FROM apache/airflow:2.9.2-python3.10
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && update-ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.2/constraints-3.10.txt" \
    -r /requirements.txt \
    certifi
