#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/restore_postgres.sh backups/file.sql"
  exit 1
fi

APP_DIR="${APP_DIR:-/opt/kitchen-vk-bot}"
cd "$APP_DIR"

set -a
source .env
set +a

docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB" < "$1"
echo "Restore finished: $1"
