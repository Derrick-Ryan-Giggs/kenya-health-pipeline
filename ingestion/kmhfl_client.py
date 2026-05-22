# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/kmhfl_client.py
#
# PRIMARY SOURCE: Kenya Master Health Facility Registry (KMHFR)
#   Republic of Kenya, Ministry of Health
#   https://kmhfr.health.go.ke
#   API: https://api.kmhfr.health.go.ke/api/public/facilities/
#   Accessed: May 2026
#   No authentication required for public read access.
#
# Fields returned by API (verified):
#   code, name, keph_level_name, facility_type_name,
#   county_name, sub_county_name, ward_name, constituency_name,
#   owner_name, owner_type_name, lat, long, beds, cots,
#   operation_status_name, open_whole_day, open_weekends,
#   open_public_holidays, open_late_night, service_names,
#   infrastructure_names, closed, is_published
#
# Env vars required:
#   KMHFL_FACILITIES_URL — base API URL
#                          e.g. https://api.kmhfr.health.go.ke/api/public/facilities/
# ============================================================

import logging
import os
import time
from datetime import datetime

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60
MAX_RETRIES     = 5
PAGE_SIZE       = 100
HEADERS         = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept":     "application/json",
}

# Service name keywords → boolean flags for mart layer
SERVICE_FLAGS = {
    "has_maternity":  ["matern", "obstet", "gynaecol", "midwif", "antenatal",
                       "postnatal", "delivery", "birth"],
    "has_art":        ["antiretroviral", "art ", " art,", "hiv", "vct",
                       "voluntary counsel"],
    "has_tb":         ["tubercul", "tb ", "tb,", "tb-", "dots"],
    "has_emergency":  ["emergency", "casualty", "trauma", "accident"],
    "has_outpatient": ["outpatient", "opd", "out-patient"],
    "has_family_planning": ["family planning", "contracepti", "long acting",
                            "short acting", "implant", "iud"],
    "has_immunisation":    ["immunis", "immuniz", "vaccination", "epi "],
    "has_lab":             ["laborator", "lab service", "patholog"],
    "has_pharmacy":        ["pharmac", "dispensing"],
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


def _service_flags(service_names: list) -> dict:
    joined = " ".join(s.lower() for s in service_names)
    return {
        flag: any(kw in joined for kw in keywords)
        for flag, keywords in SERVICE_FLAGS.items()
    }


def _safe_float(value) -> float:
    try:
        v = float(str(value).strip())
        return v
    except (ValueError, TypeError):
        return 0.0


def _safe_int(value) -> int:
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):\
        return 0


def fetch_facilities() -> list[dict]:
    """
    Paginate through the KMHFR public API and return all facility records.
    Source: Kenya Master Health Facility Registry (KMHFR)
            Republic of Kenya, Ministry of Health
            https://kmhfr.health.go.ke
    """
    base_url    = os.environ["KMHFL_FACILITIES_URL"]
    session     = _get_session()
    ingested_at = datetime.utcnow().isoformat()
    records     = []
    page        = 1
    total_pages = None

    logger.info("Starting KMHFR API pagination from %s", base_url)

    while True:
        url = f"{base_url}?format=json&page_size={PAGE_SIZE}&page={page}"
        logger.info("Fetching page %s/%s — %s",
                    page, total_pages or "?", url)

        try:
            response = session.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                verify=True,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to fetch page %d: %s", page, e)
            raise

        data = response.json()

        if total_pages is None:
            total_pages = data.get("total_pages", 1)
            total_count = data.get("count", 0)
            logger.info(
                "KMHFR API: %d total facilities across %d pages",
                total_count, total_pages
            )

        for facility in data.get("results", []):
            service_names = facility.get("service_names") or []
            if isinstance(service_names, str):
                service_names = [service_names]

            infra_names = facility.get("infrastructure_names") or []

            lat = _safe_float(facility.get("lat"))
            lon = _safe_float(facility.get("long"))

            flags = _service_flags(service_names)

            records.append({
                # Identity
                "facility_code":        str(facility.get("code") or "").strip(),
                "facility_id":          str(facility.get("id") or "").strip(),
                "facility_name":        str(facility.get("name") or "").strip(),
                "official_name":        str(facility.get("officialname") or "").strip(),
                "registration_number":  str(facility.get("registration_number") or "").strip(),

                # Classification
                "keph_level":           str(facility.get("keph_level_name") or "").strip(),
                "facility_type":        str(facility.get("facility_type_name") or "").strip(),
                "facility_type_category": str(facility.get("facility_type_category") or "").strip(),
                "owner":                str(facility.get("owner_name") or "").strip(),
                "owner_type":           str(facility.get("owner_type_name") or "").strip(),
                "regulatory_body":      str(facility.get("regulatory_body_name") or "").strip(),

                # Location
                "county_name":          str(facility.get("county_name") or "").strip(),
                "sub_county_name":      str(facility.get("sub_county_name") or "").strip(),
                "ward_name":            str(facility.get("ward_name") or "").strip(),
                "constituency_name":    str(facility.get("constituency_name") or "").strip(),
                "latitude":             lat,
                "longitude":            lon,
                "has_gps":              lat != 0.0 and lon != 0.0,

                # Operations
                "operation_status":     str(facility.get("operation_status_name") or "").strip(),
                "admission_status":     str(facility.get("admission_status_name") or "").strip(),
                "open_whole_day":       bool(facility.get("open_whole_day")),
                "open_weekends":        bool(facility.get("open_weekends")),
                "open_public_holidays": bool(facility.get("open_public_holidays")),
                "open_late_night":      bool(facility.get("open_late_night")),

                # Capacity
                "beds":                 _safe_int(facility.get("beds")),
                "cots":                 _safe_int(facility.get("cots")),

                # Services
                "service_names":        "|".join(service_names),
                **flags,

                # Infrastructure
                "infrastructure":       "|".join(infra_names),
                "has_electricity":      any("grid" in x.lower() or "solar" in x.lower()
                                            or "electric" in x.lower()
                                            for x in infra_names),
                "has_water":            any("water" in x.lower() for x in infra_names),

                # Status
                "closed":               bool(facility.get("closed")),
                "is_published":         bool(facility.get("is_published")),

                # Metadata
                "source":               "Kenya Master Health Facility Registry (KMHFR), "
                                        "Republic of Kenya Ministry of Health, "
                                        "https://kmhfr.health.go.ke, accessed May 2026",
                "ingested_at":          ingested_at,
            })

        logger.info("Page %d done — total records so far: %d", page, len(records))

        if page >= total_pages:
            break

        page += 1
        # Be polite to the government API
        time.sleep(0.3)

    logger.info("KMHFR ingestion complete — %d total facility records", len(records))

    if not records:
        raise ValueError(
            "No facility records returned from KMHFR API. "
            "Check KMHFL_FACILITIES_URL."
        )

    return records


def to_records(raw: list[dict]) -> list[dict]:
    return raw