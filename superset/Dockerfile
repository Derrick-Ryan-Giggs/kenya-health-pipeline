FROM apache/superset:5.0.0

USER root

RUN UV_CACHE_DIR=/tmp/uv-cache uv pip install \
    --python /app/.venv/bin/python3 \
    --no-cache \
    psycopg2-binary==2.9.9 \
    sqlalchemy-trino==0.5.0 \
    trino==0.327.0

USER superset
