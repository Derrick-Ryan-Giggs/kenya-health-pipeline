# ============================================================
# Kenya Health Facility Mapping Pipeline
# airflow/dags/dbt_run.py
#
# Runs dbt Core inside the Airflow worker via BashOperator.
# Order: deps → run → test → snapshot
#
# dbt connects to Trino using profiles.yml which reads
# connection details from environment variables.
#
# Triggered by kenya_health_monthly DAG — not scheduled directly.
# ============================================================

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

logger = logging.getLogger(__name__)

DBT_DIR      = "/opt/airflow/dbt"
DBT_PROFILES = "/opt/airflow/dbt"   # profiles.yml lives in dbt/ folder

default_args = {
    "owner":            "kenya-health",
    "depends_on_past":  False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dbt_run",
    default_args=default_args,
    description="Run dbt Core models, tests, and SCD2 snapshots via Trino",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["kenya-health", "dbt", "transform"],
) as dag:

    start = EmptyOperator(task_id="start")

    # Install dbt packages (dbt_utils etc.)
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_DIR} && dbt deps --profiles-dir {DBT_PROFILES}",
    )

    # Run all staging and mart models
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir {DBT_PROFILES}",
    )

    # Run all schema tests — fails DAG if any test fails
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir {DBT_PROFILES}",
    )

    # Run SCD2 snapshot — tracks facility changes over time
    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"cd {DBT_DIR} && dbt snapshot --profiles-dir {DBT_PROFILES}",
    )

    end = EmptyOperator(task_id="end")

    # ── Task dependencies ─────────────────────────────────────
    start >> dbt_deps >> dbt_run >> dbt_test >> dbt_snapshot >> end