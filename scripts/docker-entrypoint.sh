#!/usr/bin/env bash
# Docker entrypoint: prepare the DB + storage layout, then exec CMD.
set -euo pipefail

cd /app

if [[ -z "${SFRA_DATABASE_URL:-}" ]]; then
    echo "[entrypoint] SFRA_DATABASE_URL not set — defaulting to file SQLite at /app/data/app.db"
    export SFRA_DATABASE_URL="sqlite:////app/data/app.db"
fi

if [[ -z "${SFRA_JWT_SECRET:-}" ]]; then
    if [[ "${ALLOW_DEV_JWT_SECRET:-0}" != "1" ]]; then
        echo "[entrypoint] ERROR: SFRA_JWT_SECRET is unset."
        echo "             Generate one with: openssl rand -hex 32"
        echo "             For dev only, set ALLOW_DEV_JWT_SECRET=1 to bypass."
        exit 1
    fi
    echo "[entrypoint] WARNING: ALLOW_DEV_JWT_SECRET=1 — using hardcoded dev secret. Do NOT use in production."
fi

mkdir -p /app/data/storage /app/data/audit

if [[ "${SFRA_RUN_MIGRATIONS:-1}" == "1" ]]; then
    echo "[entrypoint] Running Alembic upgrade head…"
    alembic upgrade head
fi

if [[ "${SFRA_SEED_CATALOGUE:-1}" == "1" ]]; then
    echo "[entrypoint] Seeding combination catalogue…"
    python3 scripts/seed_combinations.py
fi

echo "[entrypoint] Starting service: $*"
exec "$@"
