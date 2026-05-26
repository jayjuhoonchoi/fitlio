#!/usr/bin/env bash
# Clean Next dev: stop stale servers, clear broken .next cache, start on :3000.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${FITLIO_NODE_BIN:-$HOME/.local/node-v22.14.0/bin}"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="$NODE_BIN:$PATH"
fi

bash "$ROOT/scripts/kill_frontend_ports.sh"

cd "$ROOT/frontend-next"
echo "[fitlio-frontend] clearing .next cache…"
rm -rf .next

echo "[fitlio-frontend] starting http://localhost:3000 (leave this terminal open)"
exec npx next dev -p 3000
