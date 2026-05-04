# ============================================================
# Kenya Health Facility Mapping Pipeline
# superset/Dockerfile
#
# Extends the official Superset lean image with:
#   - sqlalchemy-trino  (Trino SQLAlchemy dialect for Superset)
#   - trino             (Trino Python client)
#   - psycopg2-binary   (PostgreSQL driver for Superset metadata DB)
# ============================================================

FROM apache/superset:5.0.0

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER superset
RUN pip install --no-cache-dir \
    sqlalchemy-trino==0.5.0 \
    trino==0.327.0 \
    psycopg2-binary==2.9.9