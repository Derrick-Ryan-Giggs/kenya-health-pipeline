# ============================================================
# Kenya Health Facility Mapping Pipeline
# airflow/Dockerfile
#
# Extends the official Airflow image with:
#   - dbt Core + dbt-trino adapter
#   - boto3 (MinIO S3 client)
#   - requests, pandas (ingestion scripts)
#   - trino Python client (Trino queries)
# ============================================================
FROM apache/airflow:2.9.2-python3.10

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.2/constraints-3.10.txt" \
    -r /requirements.txt