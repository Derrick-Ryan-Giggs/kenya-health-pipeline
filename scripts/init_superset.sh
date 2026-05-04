#!/usr/bin/env bash
# ============================================================
# Kenya Health Facility Mapping Pipeline
# scripts/init_superset.sh
#
# Bootstraps Superset after first docker compose up.
# Run once — subsequent runs are safe (idempotent).
#
# Usage: make superset-init
#        or: bash scripts/init_superset.sh
# ============================================================

set -e
source .env

echo ""
echo "Initialising Superset..."
echo ""

# Step 1 — run DB migrations
echo "[1/4] Running Superset DB migrations..."
docker compose exec superset superset db upgrade

# Step 2 — create admin user
echo "[2/4] Creating admin user '${SUPERSET_ADMIN_USER}'..."
docker compose exec superset superset fab create-admin \
    --username  "${SUPERSET_ADMIN_USER}" \
    --firstname "Kenya" \
    --lastname  "Health" \
    --email     "${SUPERSET_ADMIN_EMAIL}" \
    --password  "${SUPERSET_ADMIN_PASSWORD}" || true
# || true so it doesn't fail if user already exists on re-run

# Step 3 — init roles and permissions
echo "[3/4] Initialising roles and permissions..."
docker compose exec superset superset init

# Step 4 — print connection string for Trino
echo "[4/4] Done. Add this database connection in Superset UI:"
echo ""
echo "  Display name : Kenya Health — Trino"
echo "  SQLAlchemy URI:"
echo "  trino://${TRINO_USER}@${TRINO_HOST}:${TRINO_PORT}/${TRINO_CATALOG}/${TRINO_SCHEMA}"
echo ""
echo "Superset is ready → http://localhost:${SUPERSET_PORT:-8088}"
echo "Login: ${SUPERSET_ADMIN_USER} / ${SUPERSET_ADMIN_PASSWORD}"
echo ""