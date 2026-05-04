#!/usr/bin/env bash
# ============================================================
# Kenya Health Facility Mapping Pipeline
# scripts/run_pipeline.sh
#
# Manually triggers the full monthly pipeline.
# Useful for testing outside the schedule.
#
# Usage: make pipeline-run
#        or: bash scripts/run_pipeline.sh
# ============================================================

set -e
source .env

echo ""
echo "Triggering kenya_health_monthly DAG..."
echo ""

docker compose exec airflow-webserver \
    airflow dags trigger kenya_health_monthly

echo ""
echo "Pipeline triggered successfully."
echo "Monitor progress at: http://localhost:${AIRFLOW_PORT:-8080}"
echo "DAG: kenya_health_monthly"
echo ""