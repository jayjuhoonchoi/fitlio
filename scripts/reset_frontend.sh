#!/usr/bin/env bash
# Fix white screen / MODULE_NOT_FOUND / port 3000 conflicts.
# Usage: bash ~/fitlio/scripts/reset_frontend.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${FITLIO_NODE_BIN:-$HOME/.local/node-v22.14.0/bin}"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="$NODE_BIN:$PATH"
fi

free_ports() {
  pkill -f "next dev" 2>/dev/null || true
  for port in 3000 3001 3002; do
    local pids
    pids="$(lsof -nP -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "${pids}" ]]; then
      echo "[reset-frontend] killing port ${port}: ${pids}"
      kill -9 ${pids} 2>/dev/null || true
    fi
  done
}

echo "[reset-frontend] 1/4 stop next + free ports 3000-3002"
free_ports
sleep 2
free_ports
sleep 1

if lsof -nP -iTCP:3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[reset-frontend] ERROR: port 3000 still in use. Run this, then retry:" >&2
  lsof -nP -iTCP:3000 -sTCP:LISTEN >&2 || true
  echo "  kill -9 \$(lsof -tiTCP:3000 -sTCP:LISTEN)" >&2
  exit 1
fi

echo "[reset-frontend] 2/4 wipe .next cache"
cd "$ROOT/frontend-next"
rm -rf .next

echo "[reset-frontend] 3/4 verify node_modules (skip if already ok)"
if [[ ! -d node_modules/next ]]; then
  npm install
fi

echo "[reset-frontend] 4/4 start http://localhost:3000 — keep this terminal open"
exec npx next dev -p 3000
