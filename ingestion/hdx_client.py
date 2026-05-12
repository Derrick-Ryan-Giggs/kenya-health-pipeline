# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/hdx_client.py
#
# Fetches Kenya county boundary GeoJSON from HDX JSON Repository.
# Source: https://data.humdata.org/dataset/json-repository
#
# Property keys in this GeoJSON:
#   COUNTY_NAM  — county name
#   COUNTY_COD  — county code
#   CONST_CODE  — constituency code
#   Shape_Area  — area in degrees²
#   OBJECTID    — feature ID
#
# Env vars required:
#   HDX_GEOJSON_URL — direct download URL for kenya.geojson
# ============================================================

import os
import json
import logging
from datetime import datetime

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60
MAX_RETRIES     = 3


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


def fetch_geojson() -> list[dict]:
    """
    Download Kenya county GeoJSON from HDX and return flat records.

    The GeoJSON has one feature per constituency (290 features),
    not per county (47). We aggregate by county name, keeping
    the union geometry of the first matching feature and summing area.

    Returns:
        list of county boundary records ready for MinIO upload
    """
    url     = os.environ["HDX_GEOJSON_URL"]
    session = _get_session()

    logger.info("Downloading Kenya GeoJSON from %s", url)
    response = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
    response.raise_for_status()

    geojson     = response.json()
    features    = geojson.get("features", [])
    ingested_at = datetime.utcnow().isoformat()

    if not features:
        raise ValueError("GeoJSON file returned no features")

    logger.info("Downloaded %d raw features (constituencies)", len(features))

    # Aggregate constituencies → counties
    # Keep first geometry per county, sum area
    county_map: dict = {}

    for feature in features:
        props    = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        county_name = str(props.get("COUNTY_NAM") or "").strip().title()
        county_code = str(props.get("COUNTY_COD") or "").strip()
        area_sqkm   = float(props.get("Shape_Area") or 0.0)

        if not county_name or county_name.lower() == "none":
            continue

        if county_name not in county_map:
            county_map[county_name] = {
                "county_code": county_code,
                "county_name": county_name,
                "geometry":    json.dumps(geometry),  # first constituency geometry
                "area_sqkm":   area_sqkm,
                "ingested_at": ingested_at,
            }
        else:
            # Accumulate area across constituencies
            county_map[county_name]["area_sqkm"] += area_sqkm

    records = list(county_map.values())

    logger.info(
        "Aggregated %d constituency features into %d county records",
        len(features), len(records),
    )

    if not records:
        raise ValueError(
            "No county records extracted from GeoJSON. "
            "Check COUNTY_NAM property key."
        )

    return records