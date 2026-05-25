#!/usr/bin/env bash
# Local dev: wait for Docker, start API stack, run Next on :3000.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${FITLIO_NODE_BIN:-$HOME/.local/node-v22.14.0/bin}"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="$NODE_BIN:$PATH"
fi

if ! docker info >/dev/null 2>&1; then
  echo "[fitlio-dev] Starting Docker Desktop…"
  open -a Docker 2>/dev/null || open -a "Docker Desktop" 2>/dev/null || true
  for _ in $(seq 1 60); do
    if docker info >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo "[fitlio-dev] Docker still unavailable after wait."
  echo "[fitlio-dev] Start Docker Desktop manually, then in another terminal: cd ~/fitlio && docker compose up -d"
  echo "[fitlio-dev] Continuing with Next only (demo/mock data until API is up)…"
else
echo "[fitlio-dev] docker compose up (API on :8000 via docker-compose.dev.yml)…"
cd "$ROOT"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
fi

echo "[fitlio-dev] Next dev on http://localhost:3000"
cd "$ROOT/frontend-next"
exec npm run dev
