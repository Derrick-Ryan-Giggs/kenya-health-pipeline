# ============================================================
# Kenya Health Facility Mapping Pipeline
# airflow/dags/ingest_facilities.py
#
# Fetches MOH KMHFL facility list and uploads to MinIO raw bucket.
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
    """Verify MinIO is reachable before attempting ingestion."""
    from ingestion.minio_loader import check_bucket_exists

    if not check_bucket_exists():
        raise RuntimeError(
            "MinIO raw bucket is not reachable. "
            "Ensure MinIO is running and tofu apply has been executed."
        )
    logger.info("MinIO health check passed")


def ingest_facilities(**context):
    """Fetch KMHFL facilities and upload to MinIO."""
    from ingestion.kmhfl_client import fetch_facilities, to_records
    from ingestion.minio_loader import upload_json

    logger.info("Fetching facilities from MOH KMHFL API...")
    raw     = fetch_facilities()
    records = to_records(raw)

    logger.info("Uploading %d facility records to MinIO...", len(records))
    s3_uri = upload_json(records, dataset="facilities")

    # Push URI to XCom so downstream tasks can reference it
    context["ti"].xcom_push(key="s3_uri",       value=s3_uri)
    context["ti"].xcom_push(key="record_count",  value=len(records))

    logger.info("Facilities ingestion complete → %s", s3_uri)


with DAG(
    dag_id="ingest_facilities",
    default_args=default_args,
    description="Ingest MOH KMHFL facility list → MinIO raw bucket",
    schedule_interval=None,         # triggered by orchestrator only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["kenya-health", "ingestion", "kmhfl"],
) as dag:

    t_check_minio = PythonOperator(
        task_id="check_minio",
        python_callable=check_minio,
    )

    t_ingest = PythonOperator(
        task_id="ingest_facilities",
        python_callable=ingest_facilities,
    )

    t_check_minio >> t_ingest