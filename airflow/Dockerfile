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

FROM apache/airflow:2.9.2

# Switch to root only to install system deps if needed
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user for pip installs
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt