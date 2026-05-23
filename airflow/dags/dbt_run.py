# ============================================================
# Kenya Health Facility Mapping Pipeline
# airflow/dags/dbt_run.py
# ============================================================
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

logger = logging.getLogger(__name__)

DBT_BIN      = "/home/airflow/.local/bin/dbt"
DBT_DIR      = "/opt/airflow/dbt"
DBT_PROFILES = "/opt/airflow/dbt"

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

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && {DBT_BIN} run --profiles-dir {DBT_PROFILES} --project-dir {DBT_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && {DBT_BIN} test --profiles-dir {DBT_PROFILES} --project-dir {DBT_DIR}",
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"cd {DBT_DIR} && {DBT_BIN} snapshot --profiles-dir {DBT_PROFILES} --project-dir {DBT_DIR}",
    )

    end = EmptyOperator(task_id="end")

    start >> dbt_run >> dbt_test >> dbt_snapshot >> end
