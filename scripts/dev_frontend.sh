#!/usr/bin/env bash
# Clean Next dev: stop stale servers, clear broken .next cache, start on :3000.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${FITLIO_NODE_BIN:-$HOME/.local/node-v22.14.0/bin}"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="$NODE_BIN:$PATH"
fi

echo "[fitlio-frontend] stopping stale next dev processes…"
pkill -f "next dev" 2>/dev/null || true
for port in 3000 3001 3002; do
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    kill -9 $pids 2>/dev/null || true
  fi
done
sleep 1

cd "$ROOT/frontend-next"
echo "[fitlio-frontend] clearing .next cache…"
rm -rf .next

echo "[fitlio-frontend] starting http://localhost:3000"
if lsof -ti tcp:3000 >/dev/null 2>&1; then
  echo "[fitlio-frontend] ERROR: port 3000 still in use. Run in your terminal:" >&2
  echo "  kill -9 \$(lsof -ti tcp:3000 tcp:3001 tcp:3002)" >&2
  exit 1
fi
exec npm run dev -- -p 3000
