# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/knbs_client.py
#
# Downloads KNBS Kenya population estimates.
# KNBS publishes county and sub-county population data
# as downloadable CSV/Excel files from their website.
#
# Env vars required:
#   KNBS_POPULATION_URL — direct URL to the population CSV/Excel
# ============================================================

import os
import io
import logging
from datetime import datetime

import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60   # population file can be large
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


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names — strip whitespace, lowercase,
    replace spaces with underscores.
    """
    df.columns = [
        col.strip().lower().replace(" ", "_").replace("-", "_")
        for col in df.columns
    ]
    return df


def fetch_population() -> list[dict]:
    """
    Download KNBS population estimates and return as list of dicts.

    Expected CSV columns (flexible — normalizes whatever KNBS provides):
        County, Sub County, Population, Year

    Returns:
        list of flat population records ready for MinIO upload
    """
    url     = os.environ["KNBS_POPULATION_URL"]
    session = _get_session()

    logger.info("Fetching KNBS population data from %s", url)

    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")

    # Handle both CSV and Excel responses
    if "excel" in content_type or url.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(response.content))
    else:
        df = pd.read_csv(io.BytesIO(response.content))

    df = _normalize_columns(df)

    logger.info("Downloaded population file — %d rows, columns: %s", len(df), list(df.columns))

    ingested_at = datetime.utcnow().isoformat()
    records     = []

    for _, row in df.iterrows():
        # Flexible column mapping — handles variations in KNBS file structure
        county_code  = str(row.get("county_code") or row.get("code") or "")
        county_name  = str(row.get("county") or row.get("county_name") or "")
        sub_county   = str(row.get("sub_county") or row.get("sub_county_name") or "")
        population   = row.get("population") or row.get("total_population") or 0
        census_year  = int(row.get("year") or row.get("census_year") or 2019)

        # Skip completely empty rows
        if not county_name or not population:
            continue

        records.append({
            "county_code":   county_code,
            "county_name":   county_name.strip().title(),
            "sub_county":    sub_county.strip().title(),
            "population":    int(population),
            "census_year":   census_year,
            "ingested_at":   ingested_at,
        })

    logger.info("Normalized %d population records", len(records))
    return records