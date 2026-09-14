#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting FinPilot backend container..."

: "${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY is required}"

if [ "${SKIP_DJANGO_STARTUP:-false}" = "true" ]; then
    echo "[entrypoint] SKIP_DJANGO_STARTUP=true — skipping migrate and collectstatic"
else
    : "${POSTGRES_HOST:?POSTGRES_HOST is required}"

    echo "[entrypoint] Running database migrations..."
    python manage.py migrate --noinput

    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "[entrypoint] Handing off to: $*"

exec "$@"