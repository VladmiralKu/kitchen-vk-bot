#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kitchen-vk-bot}"
cd "$APP_DIR"

set -a
source .env
set +a

mkdir -p backups
FILE="backups/kitchen_bot_$(date +%Y%m%d_%H%M%S).sql"

docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$FILE"
echo "Backup saved: $FILE"
