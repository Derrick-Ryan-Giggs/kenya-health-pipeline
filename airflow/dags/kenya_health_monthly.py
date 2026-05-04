# ============================================================
# Kenya Health Facility Mapping Pipeline
# airflow/dags/kenya_health_monthly.py
#
# Main orchestrator DAG — runs on the 1st of every month.
# Triggers ingestion DAGs in parallel, then runs dbt after
# all three complete successfully.
#
# Schedule: 02:00 EAT on the 1st of each month
# ============================================================

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner":            "kenya-health",
    "depends_on_past":  False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry":   False,
}

with DAG(
    dag_id="kenya_health_monthly",
    default_args=default_args,
    description="Monthly Kenya health facility pipeline — ingest + dbt",
    schedule_interval="0 2 1 * *",   # 02:00 on the 1st of each month
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["kenya-health", "monthly", "orchestrator"],
) as dag:

    start = EmptyOperator(task_id="start")

    # ── Ingestion — run in parallel ───────────────────────────
    ingest_facilities = TriggerDagRunOperator(
        task_id="trigger_ingest_facilities",
        trigger_dag_id="ingest_facilities",
        wait_for_completion=True,
        poke_interval=30,
        reset_dag_run=True,
    )

    ingest_population = TriggerDagRunOperator(
        task_id="trigger_ingest_population",
        trigger_dag_id="ingest_population",
        wait_for_completion=True,
        poke_interval=30,
        reset_dag_run=True,
    )

    ingest_geodata = TriggerDagRunOperator(
        task_id="trigger_ingest_geodata",
        trigger_dag_id="ingest_geodata",
        wait_for_completion=True,
        poke_interval=30,
        reset_dag_run=True,
    )

    # ── Gate — all ingestion must complete before dbt runs ────
    ingestion_complete = EmptyOperator(task_id="ingestion_complete")

    # ── dbt — runs after all ingestion succeeds ───────────────
    run_dbt = TriggerDagRunOperator(
        task_id="trigger_dbt_run",
        trigger_dag_id="dbt_run",
        wait_for_completion=True,
        poke_interval=30,
        reset_dag_run=True,
    )

    end = EmptyOperator(task_id="end")

    # ── Task dependencies ─────────────────────────────────────
    start >> [ingest_facilities, ingest_population, ingest_geodata]
    [ingest_facilities, ingest_population, ingest_geodata] >> ingestion_complete
    ingestion_complete >> run_dbt >> end