#!/usr/bin/env bash
# Start the dev stack: Postgres in Docker, backend + frontend locally.
# Usage: ./ops/scripts/dev.sh (from the project root)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ── Postgres ─────────────────────────────────────────────────────────────────
echo "Starting Postgres..."
docker-compose -f "$ROOT/ops/deploy/docker-compose.yml" up -d db

echo "Waiting for database to be ready..."
until docker-compose -f "$ROOT/ops/deploy/docker-compose.yml" exec -T db \
  pg_isready -U finance -q 2>/dev/null; do
  sleep 1
done
echo "Database ready."

# ── Migrations ────────────────────────────────────────────────────────────────
echo "Running migrations..."
(cd "$ROOT/src/backend" && uv run alembic upgrade head)

# ── Backend ───────────────────────────────────────────────────────────────────
echo "Starting backend (port 8000)..."
(cd "$ROOT/src/backend" && uv run uvicorn main:app --reload --port 8000) &
BACKEND_PID=$!

# ── Frontend ──────────────────────────────────────────────────────────────────
echo "Starting frontend (port 5173)..."
(cd "$ROOT/src/frontend" && npm run dev) &
FRONTEND_PID=$!

# ── Info ──────────────────────────────────────────────────────────────────────
echo ""
echo "Dev stack running:"
echo "  App:   http://localhost:5173"
echo "  API:   http://localhost:8000"
echo "  Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."

cleanup() {
  echo "Stopping..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  docker-compose -f "$ROOT/ops/deploy/docker-compose.yml" stop db
}
trap cleanup INT TERM

wait "$BACKEND_PID" "$FRONTEND_PID"
