#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kitchen-vk-bot}"
cd "$APP_DIR"

git pull
docker compose up -d --build
docker compose exec app alembic upgrade head
docker compose ps
curl -fsS http://127.0.0.1:8000/health
echo
