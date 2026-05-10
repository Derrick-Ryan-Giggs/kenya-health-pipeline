FROM apache/superset:5.0.0

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Target the venv explicitly so uv installs there, not system Python
RUN uv pip install --python /app/.venv/bin/python \
    psycopg2-binary==2.9.9 \
    sqlalchemy-trino==0.5.0 \
    trino==0.327.0 \
    flask-session==0.8.0 \
    redis==5.0.1

COPY superset_config.py /app/pythonpath/superset_config.py

USER superset