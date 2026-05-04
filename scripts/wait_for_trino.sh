#!/usr/bin/env bash
# ============================================================
# Kenya Health Facility Mapping Pipeline
# scripts/wait_for_trino.sh
#
# Waits until Trino coordinator is fully started and ready
# to accept queries. Call this before running dbt manually.
#
# Usage: bash scripts/wait_for_trino.sh
# ============================================================

set -e
source .env

TRINO_URL="http://localhost:${TRINO_EXPOSED_PORT:-8081}/v1/info"
MAX_WAIT=120   # seconds
INTERVAL=5
ELAPSED=0

echo "Waiting for Trino at ${TRINO_URL}..."

until curl -sf "$TRINO_URL" | grep -q '"starting":false'; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo "Trino did not become ready within ${MAX_WAIT}s. Check logs:"
        echo "  docker compose logs trino"
        exit 1
    fi
    echo "  Trino not ready yet — retrying in ${INTERVAL}s... (${ELAPSED}s elapsed)"
    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo "Trino is ready."