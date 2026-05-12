# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/knbs_client.py
#
# Downloads KNBS Kenya population estimates from HDX.
# Source: Kenya Population Per County from Census Report 2019
# https://data.humdata.org/dataset/kenya-population-per-county-from-census-report-2019
#
# CSV columns (as published by KNBS on HDX):
#   County, Male, Female, Intersex, Total, Households
#
# Env vars required:
#   KNBS_POPULATION_URL — HDX direct CSV download URL
# ============================================================

import os
import io
import logging
from datetime import datetime

import requests
import urllib3
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60
MAX_RETRIES     = 3
CENSUS_YEAR     = 2019


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


def fetch_population() -> list[dict]:
    """
    Download KNBS Census 2019 county population data from HDX
    and return as list of normalised dicts.

    Returns:
        list of population records ready for MinIO upload
    """
    url     = os.environ["KNBS_POPULATION_URL"]
    session = _get_session()

    logger.info("Fetching KNBS population CSV from %s", url)
    response = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
    response.raise_for_status()

    df = pd.read_csv(io.BytesIO(response.content))

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_")
                  for c in df.columns]

    logger.info("Downloaded %d rows. Columns: %s", len(df), list(df.columns))

    ingested_at = datetime.utcnow().isoformat()
    records     = []

    for _, row in df.iterrows():
        # KNBS CSV uses 'county' as the county name column
        county_name = str(
            row.get("county") or
            row.get("county_name") or
            row.get("name") or
            ""
        ).strip()

        if not county_name or county_name.lower() in ("nan", "total", "kenya"):
            continue

        # Population — 'total' column in KNBS CSV
        population = (
            row.get("total") or
            row.get("population") or
            row.get("total_population") or
            0
        )

        try:
            population = int(str(population).replace(",", ""))
        except (ValueError, TypeError):
            population = 0

        if population == 0:
            continue

        # Sub-county is not in this CSV — county-level only
        records.append({
            "county_code":  str(row.get("county_code") or row.get("code") or ""),
            "county_name":  county_name.title(),
            "sub_county":   "",
            "population":   population,
            "male":         _safe_int(row.get("male")),
            "female":       _safe_int(row.get("female")),
            "households":   _safe_int(row.get("households") or row.get("number_of_households")),
            "census_year":  CENSUS_YEAR,
            "ingested_at":  ingested_at,
        })

    logger.info("Normalised %d population records", len(records))

    if not records:
        raise ValueError(
            "No population records parsed from KNBS CSV. "
            "Check column names or URL."
        )

    return records


def _safe_int(value) -> int:
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return 0