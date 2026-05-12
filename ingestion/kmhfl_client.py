# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/kmhfl_client.py
#
# PRIMARY SOURCE: MOH KMHFL XLSX via HDX
#   Full facility fields: code, name, KEPH level, facility type,
#   owner, county, sub-county, ward, operation status, service names.
#   Source: https://data.humdata.org/dataset/kenya-health-facilities-in-kenya
#
# GPS ENRICHMENT: HOT OSM Kenya Health Facilities (monthly updated)
#   Fills in lat/lon for facilities missing GPS in the XLSX by
#   fuzzy-matching on facility name + county.
#   Source: https://data.humdata.org/dataset/hotosm_ken_health_facilities
#
# Env vars required:
#   KMHFL_FACILITIES_URL      — HDX XLSX download URL (dataset UUID path)
#   KMHFL_GPS_ENRICHMENT_URL  — HOT OSM zipped GeoJSON points URL
# ============================================================

import io
import json
import logging
import os
import zipfile
from datetime import datetime

import requests
import urllib3
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 120
MAX_RETRIES     = 3

# Map KMHFL facility type strings → normalised short labels
FACILITY_TYPE_MAP = {
    "basic primary health care facility":        "Health Centre",
    "dispensaries and clinic-out patients":      "Dispensary",
    "dispensaries and clinic-out patient":       "Dispensary",
    "secondary care hospitals":                  "Hospital",
    "primary care hospitals":                    "Hospital",
    "national referral hospitals":               "National Referral",
    "county referral hospitals":                 "County Referral",
    "radiology clinic":                          "Radiology Clinic",
    "nursing home":                              "Nursing Home",
    "pharmacy":                                  "Pharmacy",
    "laboratory":                                "Laboratory",
}


def _get_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session


def _normalise_type(raw: str) -> str:
    key = str(raw).lower().strip()
    for pattern, label in FACILITY_TYPE_MAP.items():
        if pattern in key:
            return label
    return str(raw).strip().title() or "Unknown"


def _load_osm_gps(session: requests.Session) -> dict:
    """
    Download HOT OSM GeoJSON zip and build a lookup dict:
      {(normalised_name, normalised_county): (lat, lon)}
    Used to fill missing GPS in the XLSX.
    """
    url = os.environ.get("KMHFL_GPS_ENRICHMENT_URL", "")
    if not url:
        logger.warning("KMHFL_GPS_ENRICHMENT_URL not set — skipping GPS enrichment")
        return {}

    logger.info("Downloading HOT OSM GPS enrichment from %s", url)
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
        response.raise_for_status()
    except Exception as e:
        logger.warning("HOT OSM GPS download failed: %s — proceeding without GPS", e)
        return {}

    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            geojson_files = [f for f in zf.namelist() if f.endswith(".geojson")]
            if not geojson_files:
                logger.warning("No GeoJSON in HOT OSM zip — skipping GPS enrichment")
                return {}
            with zf.open(geojson_files[0]) as f:
                geojson = json.load(f)
    except Exception as e:
        logger.warning("HOT OSM zip parse error: %s — skipping GPS enrichment", e)
        return {}

    gps_lookup = {}
    for feature in geojson.get("features", []):
        props = feature.get("properties") or {}
        geom  = feature.get("geometry") or {}
        name  = str(props.get("name") or "").strip().lower()
        county = str(
            props.get("addr:city") or props.get("addr:county") or ""
        ).strip().lower()
        coords = geom.get("coordinates", [])
        if name and len(coords) >= 2:
            try:
                gps_lookup[(name, county)] = (float(coords[1]), float(coords[0]))
            except (TypeError, ValueError):
                pass

    logger.info("Loaded %d GPS points from HOT OSM for enrichment", len(gps_lookup))
    return gps_lookup


def fetch_facilities() -> list[dict]:
    """
    Download MOH KMHFL XLSX from HDX, parse all facility fields,
    and enrich with GPS coordinates from HOT OSM where available.

    Returns:
        list of normalised facility dicts ready for MinIO upload
    """
    url     = os.environ["KMHFL_FACILITIES_URL"]
    session = _get_session()

    # Load GPS lookup first (non-fatal if unavailable)
    gps_lookup = _load_osm_gps(session)

    logger.info("Downloading KMHFL facilities XLSX from %s", url)
    response = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
    response.raise_for_status()

    df = pd.read_excel(io.BytesIO(response.content))

    # Normalise column names
    df.columns = [
        c.strip().lower().replace(" ", "_").replace("-", "_")
        for c in df.columns
    ]

    logger.info("Downloaded %d facility rows. Columns: %s", len(df), list(df.columns))

    ingested_at = datetime.utcnow().isoformat()
    records     = []

    for _, row in df.iterrows():
        name = str(row.get("name") or "").strip()
        if not name or name.lower() == "nan":
            continue

        county     = str(row.get("county") or "").strip().title()
        sub_county = str(row.get("sub_county") or row.get("sub county") or "").strip().title()
        ward       = str(row.get("ward") or "").strip().title()

        # Service names — XLSX has a pipe/comma separated string or list
        raw_services = str(row.get("service_names") or row.get("services") or "")
        service_list = [s.strip().lower() for s in raw_services.replace("|", ",").split(",") if s.strip()]
        services_str = "|".join(service_list)

        # GPS — try XLSX columns first, fall back to OSM lookup
        lat = _safe_float(row.get("lat") or row.get("latitude"))
        lon = _safe_float(row.get("lon") or row.get("longitude") or row.get("long"))

        if (lat == 0.0 or lon == 0.0) and gps_lookup:
            osm_key    = (name.lower(), county.lower())
            osm_coords = gps_lookup.get(osm_key)
            if osm_coords:
                lat, lon = osm_coords

        records.append({
            "facility_code":    str(row.get("code") or "").strip(),
            "facility_name":    name.title(),
            "keph_level":       str(row.get("keph_level") or row.get("keph level") or "").strip(),
            "facility_type":    _normalise_type(row.get("facility_type") or ""),
            "owner":            str(row.get("owner") or "").strip(),
            "county_name":      county,
            "sub_county_name":  sub_county,
            "ward_name":        ward,
            "constituency":     str(row.get("constituency") or "").strip().title(),
            "latitude":         lat,
            "longitude":        lon,
            "operation_status": str(row.get("operation_status") or row.get("operation status") or "Operational").strip(),
            "open_whole_day":   _yes_bool(row.get("open_whole_day")),
            "open_weekends":    _yes_bool(row.get("open_weekends")),
            "open_public_holidays": _yes_bool(row.get("open_public_holidays")),
            "open_late_night":  _yes_bool(row.get("open_late_night")),
            # Service flags derived from service_names column
            "has_maternity":    any(x in services_str for x in ["matern", "obstet", "gynae", "midwif"]),
            "has_art":          any(x in services_str for x in ["art", "antiretro", "hiv"]),
            "has_tb":           any(x in services_str for x in ["tb ", "tuberculosis", "tb_"]),
            "has_emergency":    any(x in services_str for x in ["emergency", "casualty", "trauma"]),
            "has_outpatient":   any(x in services_str for x in ["outpatient", "opd"]),
            "service_names":    services_str,
            "approved":         _yes_bool(row.get("approved")),
            "closed":           _yes_bool(row.get("closed")),
            "source":           "MOH KMHFL via HDX",
            "ingested_at":      ingested_at,
        })

    logger.info("Normalised %d facility records", len(records))

    if not records:
        raise ValueError(
            "No facility records parsed from KMHFL XLSX. "
            "Check column names or KMHFL_FACILITIES_URL."
        )

    return records


def to_records(raw: list[dict]) -> list[dict]:
    """Pass-through — records already normalised by fetch_facilities()."""
    return raw


def _safe_float(value) -> float:
    try:
        v = float(str(value).replace(",", ""))
        return v if v != 0 else 0.0
    except (ValueError, TypeError):
        return 0.0


def _yes_bool(value) -> bool:
    return str(value).strip().lower() in ("yes", "true", "1", "y")