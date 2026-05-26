#!/usr/bin/env bash
# Free ports used by stale Next dev servers (3000–3002).
set -euo pipefail

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -nP -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    echo "[fitlio-frontend] killing port ${port}: ${pids}"
    kill -9 ${pids} 2>/dev/null || true
  fi
}

pkill -f "next dev" 2>/dev/null || true
for port in 3000 3001 3002; do
  kill_port "${port}"
done
sleep 1
for port in 3000 3001 3002; do
  kill_port "${port}"
done

if lsof -nP -iTCP:3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[fitlio-frontend] ERROR: port 3000 still busy. Close Cursor preview tabs or run:" >&2
  echo "  sudo lsof -nP -iTCP:3000 -sTCP:LISTEN" >&2
  exit 1
fi

echo "[fitlio-frontend] ports 3000–3002 are free"
