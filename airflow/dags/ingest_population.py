# ============================================================
# Kenya Health Facility Mapping Pipeline
# airflow/dags/ingest_population.py
#
# Downloads KNBS population estimates and uploads to MinIO.
# Triggered by kenya_health_monthly DAG — not scheduled directly.
# ============================================================

import sys
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

logger = logging.getLogger(__name__)

default_args = {
    "owner":            "kenya-health",
    "depends_on_past":  False,
    "retries":          3,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}


def check_minio(**context):
    from ingestion.minio_loader import check_bucket_exists

    if not check_bucket_exists():
        raise RuntimeError("MinIO raw bucket is not reachable.")
    logger.info("MinIO health check passed")


def ingest_population(**context):
    """Download KNBS population data and upload to MinIO."""
    from ingestion.knbs_client import fetch_population
    from ingestion.minio_loader import upload_json

    logger.info("Fetching KNBS population estimates...")
    records = fetch_population()

    logger.info("Uploading %d population records to MinIO...", len(records))
    s3_uri = upload_json(records, dataset="population")

    context["ti"].xcom_push(key="s3_uri",      value=s3_uri)
    context["ti"].xcom_push(key="record_count", value=len(records))

    logger.info("Population ingestion complete → %s", s3_uri)


with DAG(
    dag_id="ingest_population",
    default_args=default_args,
    description="Ingest KNBS population estimates → MinIO raw bucket",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["kenya-health", "ingestion", "knbs"],
) as dag:

    t_check_minio = PythonOperator(
        task_id="check_minio",
        python_callable=check_minio,
    )

    t_ingest = PythonOperator(
        task_id="ingest_population",
        python_callable=ingest_population,
    )

    t_check_minio >> t_ingest