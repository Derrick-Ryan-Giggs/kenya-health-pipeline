# ============================================================
# Kenya Health Facility Mapping Pipeline
# ingestion/minio_loader.py
#
# Uploads raw ingestion records to MinIO raw bucket.
# All config comes from environment variables — nothing hardcoded.
#
# Storage layout:
#   raw-facilities/
#     facilities/year=YYYY/month=MM/day=DD/facilities.json
#     population/year=YYYY/month=MM/day=DD/population.json
#     geodata/year=YYYY/month=MM/day=DD/geodata.json
# ============================================================

import os
import json
import logging
from datetime import datetime

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _get_client():
    """
    Build a boto3 S3 client pointed at MinIO.
    Reads credentials from environment variables.
    """
    return boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _build_key(dataset: str, dt: datetime) -> str:
    """
    Build the S3 object key for a dataset partition.
    Example: facilities/year=2025/month=05/day=01/facilities.json
    """
    return (
        f"{dataset}/"
        f"year={dt.year}/"
        f"month={dt.month:02d}/"
        f"day={dt.day:02d}/"
        f"{dataset}.json"
    )


def upload_json(records: list[dict], dataset: str) -> str:
    """
    Upload a list of records to MinIO as newline-delimited JSON.

    Args:
        records: list of dicts to upload
        dataset: one of 'facilities', 'population', 'geodata'

    Returns:
        The full S3 URI of the uploaded object.

    Raises:
        ClientError: if the upload fails
    """
    if not records:
        raise ValueError(f"No records to upload for dataset '{dataset}'")

    client = _get_client()
    bucket = os.environ["MINIO_RAW_BUCKET"]
    dt     = datetime.utcnow()
    key    = _build_key(dataset, dt)

    # Newline-delimited JSON — one record per line
    # Easy to read back with pandas or Trino
    body = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)

    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "dataset":      dataset,
                "record_count": str(len(records)),
                "ingested_at":  dt.isoformat(),
            },
        )
    except ClientError as e:
        logger.error("Failed to upload %s to s3://%s/%s: %s", dataset, bucket, key, e)
        raise

    s3_uri = f"s3://{bucket}/{key}"
    logger.info("Uploaded %d records → %s", len(records), s3_uri)
    return s3_uri


def check_bucket_exists() -> bool:
    """
    Quick health check — confirms the raw bucket is reachable.
    Call this at the start of each DAG run.
    """
    client = _get_client()
    bucket = os.environ["MINIO_RAW_BUCKET"]

    try:
        client.head_bucket(Bucket=bucket)
        logger.info("MinIO bucket '%s' is reachable", bucket)
        return True
    except ClientError as e:
        logger.error("MinIO bucket '%s' not reachable: %s", bucket, e)
        return False