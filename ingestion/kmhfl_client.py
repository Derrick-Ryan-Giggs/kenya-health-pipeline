# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/kmhfl_client.py
#
# Fetches Kenya health facility data from the MOH KMHFL API.
# API docs: https://kmhfl.health.go.ke/api/
#
# Env vars required:
#   KMHFL_BASE_URL  — e.g. https://kmhfl.health.go.ke/api
#   KMHFL_TOKEN     — API token (leave empty if not required)
# ============================================================

import os
import logging
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
PAGE_SIZE     = 100
REQUEST_TIMEOUT = 30   # seconds per request
MAX_RETRIES     = 3


def _get_session() -> requests.Session:
    """
    Build a requests session with retry logic and auth header.
    """
    session = requests.Session()

    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)

    token = os.environ.get("KMHFL_TOKEN", "").strip()
    if token:
        session.headers.update({"Authorization": f"Token {token}"})

    return session


def fetch_facilities() -> list[dict]:
    """
    Fetch all operational facilities from the KMHFL API.
    Handles pagination automatically.

    Returns:
        list of raw facility dicts from the API
    """
    base_url = os.environ["KMHFL_BASE_URL"].rstrip("/")
    session  = _get_session()
    endpoint = f"{base_url}/facilities/facilities/"

    facilities = []
    page       = 1

    logger.info("Starting KMHFL facility fetch from %s", endpoint)

    while True:
        params = {
            "page":      page,
            "page_size": PAGE_SIZE,
            "fields":    (
                "code,name,keph_level_name,facility_type_name,"
                "county,sub_county,ward_name,"
                "lat,long,operation_status_name,"
                "service_names"
            ),
        }

        response = session.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        batch = data.get("results", [])
        facilities.extend(batch)

        logger.info(
            "Fetched page %d — %d facilities so far (total expected: %s)",
            page,
            len(facilities),
            data.get("count", "unknown"),
        )

        if not data.get("next"):
            break

        page += 1

    logger.info("KMHFL fetch complete — %d total facilities", len(facilities))
    return facilities


def to_records(raw: list[dict]) -> list[dict]:
    """
    Normalize raw KMHFL API response into clean flat records.
    Maps service names to boolean flags for maternity, ART, TB, emergency.

    Args:
        raw: list of raw facility dicts from fetch_facilities()

    Returns:
        list of clean flat dicts ready for MinIO upload
    """
    ingested_at = datetime.utcnow().isoformat()
    records     = []

    for facility in raw:
        # Extract service names as a lowercase set for easy flag checking
        service_names = {
            s.lower()
            for s in (facility.get("service_names") or [])
        }

        records.append({
            "facility_code":    str(facility.get("code", "") or ""),
            "facility_name":    str(facility.get("name", "") or ""),
            "facility_type":    str(
                facility.get("keph_level_name")
                or facility.get("facility_type_name")
                or ""
            ),
            "county_name":      str(facility.get("county", "") or ""),
            "sub_county_name":  str(facility.get("sub_county", "") or ""),
            "ward_name":        str(facility.get("ward_name", "") or ""),
            "latitude":         float(facility.get("lat") or 0.0),
            "longitude":        float(facility.get("long") or 0.0),
            "operation_status": str(facility.get("operation_status_name", "") or ""),
            # Service availability flags
            "has_maternity":    any("matern" in s for s in service_names),
            "has_art":          any("art" in s or "antiretroviral" in s for s in service_names),
            "has_tb":           any("tb" in s or "tuberculosis" in s for s in service_names),
            "has_emergency":    any("emergency" in s for s in service_names),
            "has_outpatient":   any("outpatient" in s for s in service_names),
            "ingested_at":      ingested_at,
        })

    logger.info("Normalized %d facility records", len(records))
    return records