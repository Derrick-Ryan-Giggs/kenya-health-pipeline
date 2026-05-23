# ============================================================
# Kenya Health Pipeline — Makefile
# ============================================================
include .env
export

.PHONY: help up down restart logs ps \
        pull build \
        tofu-init tofu-plan tofu-apply tofu-destroy \
        dbt-run dbt-test dbt-snapshot dbt-docs \
        superset-init \
        pipeline-run \
        clean

help:
	@echo ""
	@echo "  Kenya Health Facility Mapping Pipeline"
	@echo ""
	@echo "  make up              Start all services"
	@echo "  make down            Stop all services"
	@echo "  make restart         Down then up"
	@echo "  make logs            Tail all logs"
	@echo "  make ps              Show running containers"
	@echo ""
	@echo "  make pull            Pull all Docker images"
	@echo "  make build           Build custom Airflow + Superset images"
	@echo ""
	@echo "  make tofu-init       Initialise OpenTofu"
	@echo "  make tofu-plan       Preview infra changes"
	@echo "  make tofu-apply      Provision MinIO buckets + Trino catalog"
	@echo "  make tofu-destroy    Tear down provisioned infra"
	@echo ""
	@echo "  make dbt-run         Run all dbt models"
	@echo "  make dbt-test        Run dbt tests"
	@echo "  make dbt-snapshot    Run SCD2 snapshots"
	@echo "  make dbt-docs        Generate + serve dbt docs"
	@echo ""
	@echo "  make superset-init   Bootstrap Superset admin + DB"
	@echo "  make pipeline-run    Trigger monthly DAG manually"
	@echo "  make clean           Remove volumes + built images"
	@echo ""

# ── Docker ───────────────────────────────────────────────────

pull:
	docker pull trinodb/trino:480
	docker pull minio/minio:RELEASE.2025-09-07T16-13-09Z
	docker pull minio/mc:RELEASE.2025-08-13T08-35-41Z
	docker pull apache/superset:5.0.0
	docker pull apache/airflow:2.9.2
	docker pull postgres:13
	docker pull postgres:18
	docker pull redis:7.2

build:
	docker compose build airflow-webserver superset

up:
	docker compose up -d
	@echo "Airflow   → http://localhost:8080"
	@echo "MinIO     → http://localhost:9001"
	@echo "Trino     → http://localhost:8081"
	@echo "Superset  → http://localhost:8088"

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f

ps:
	docker compose ps

# ── OpenTofu ─────────────────────────────────────────────────

tofu-init:
	cd infra && tofu init

tofu-plan:
	cd infra && tofu plan

tofu-apply:
	cd infra && tofu apply -auto-approve

tofu-destroy:
	cd infra && tofu destroy -auto-approve

# ── dbt ──────────────────────────────────────────────────────

dbt-run:
	docker compose exec airflow-worker bash -c "cd /opt/airflow/dbt && /home/airflow/.local/bin/dbt run --profiles-dir . --project-dir ."

dbt-test:
	docker compose exec airflow-worker bash -c "cd /opt/airflow/dbt && /home/airflow/.local/bin/dbt test --profiles-dir . --project-dir ."

dbt-snapshot:
	docker compose exec airflow-worker bash -c "cd /opt/airflow/dbt && /home/airflow/.local/bin/dbt snapshot --profiles-dir . --project-dir ."

dbt-docs:
	docker compose exec airflow-worker bash -c "cd /opt/airflow/dbt && /home/airflow/.local/bin/dbt docs generate --profiles-dir . --project-dir . && dbt docs serve --port 8082"

# ── Superset ─────────────────────────────────────────────────

superset-init:
	bash scripts/init_superset.sh

# ── Pipeline ─────────────────────────────────────────────────

pipeline-run:
	docker compose exec airflow-webserver airflow dags trigger kenya_health_monthly

# ── Clean ────────────────────────────────────────────────────

clean:
	docker compose down -v --remove-orphans
	docker image rm kenya-health-airflow kenya-health-superset 2>/dev/null || true
