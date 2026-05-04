# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/hdx_client.py
#
# Fetches Kenya county boundary GeoJSON from HDX
# (Humanitarian Data Exchange).
# HDX API docs: https://data.humdata.org/api/3/action/
#
# Env vars required:
#   HDX_BASE_URL          — https://data.humdata.org/api/3
#   HDX_KENYA_DATASET_ID  — e.g. kenya-county-geojson
# ============================================================

import os
import json
import logging
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def _get_geojson_url(session: requests.Session, base_url: str, dataset_id: str) -> str:
    """
    Query the HDX CKAN API to find the GeoJSON resource URL
    for the given dataset ID.
    """
    endpoint = f"{base_url}/action/package_show"
    response = session.get(
        endpoint,
        params={"id": dataset_id},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    result    = response.json().get("result", {})
    resources = result.get("resources", [])

    if not resources:
        raise ValueError(f"No resources found for HDX dataset '{dataset_id}'")

    # Find the GeoJSON resource — try format field first, then URL extension
    geojson_resource = next(
        (
            r for r in resources
            if r.get("format", "").upper() == "GEOJSON"
            or r.get("url", "").lower().endswith(".geojson")
        ),
        None,
    )

    if not geojson_resource:
        available = [r.get("format") for r in resources]
        raise ValueError(
            f"No GeoJSON resource in dataset '{dataset_id}'. "
            f"Available formats: {available}"
        )

    url = geojson_resource["url"]
    logger.info("Found GeoJSON resource: %s", url)
    return url


def fetch_geojson() -> list[dict]:
    """
    Fetch Kenya county GeoJSON boundaries from HDX.
    Flattens each GeoJSON feature into a flat dict record,
    storing the geometry as a JSON string.

    Returns:
        list of flat county boundary records ready for MinIO upload
    """
    base_url   = os.environ["HDX_BASE_URL"].rstrip("/")
    dataset_id = os.environ["HDX_KENYA_DATASET_ID"]
    session    = _get_session()

    logger.info("Fetching HDX dataset metadata for '%s'", dataset_id)
    geojson_url = _get_geojson_url(session, base_url, dataset_id)

    logger.info("Downloading GeoJSON from %s", geojson_url)
    response = session.get(geojson_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    geojson     = response.json()
    features    = geojson.get("features", [])
    ingested_at = datetime.utcnow().isoformat()

    if not features:
        raise ValueError("GeoJSON file contains no features")

    records = []

    for feature in features:
        props    = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        # KNBS GeoJSON property names vary between HDX datasets —
        # try multiple known key names for county code and name
        county_code = str(
            props.get("OBJECTID")
            or props.get("County_Cod")
            or props.get("county_code")
            or props.get("CODE")
            or ""
        )
        county_name = str(
            props.get("County")
            or props.get("NAME_1")
            or props.get("county_name")
            or props.get("Name")
            or ""
        )
        area_sqkm = float(
            props.get("Shape_Area")
            or props.get("area_sqkm")
            or props.get("AREA")
            or 0.0
        )

        if not county_name:
            logger.warning("Skipping feature with no county name: %s", props)
            continue

        records.append({
            "county_code":  county_code,
            "county_name":  county_name.strip().title(),
            "geometry":     json.dumps(geometry),   # stored as JSON string
            "area_sqkm":    area_sqkm,
            "ingested_at":  ingested_at,
        })

    logger.info("Fetched %d county boundary records from HDX", len(records))
    return records