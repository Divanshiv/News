#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Creating databases"
./scripts/create_db.sh

echo "==> Backend setup"
cd backend
uv venv
uv sync
cp -n .env.example .env || true

echo "==> Frontend setup"
cd ../frontend
npm install
cp -n .env.example .env.local || true

echo "==> Done"
echo "Run backend:  cd backend && uv run uvicorn app.main:app --reload"
echo "Run frontend: cd frontend && npm run dev"