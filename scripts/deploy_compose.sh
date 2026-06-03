#!/usr/bin/env bash
# EC2 docker compose (8080/8443): build api + web, restart stack.
#
# Usage:
#   cd ~/fitlio && bash scripts/deploy_compose.sh
#   BUILD_IMAGES=0 bash scripts/deploy_compose.sh   # skip rebuild
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=/dev/null
source "${ROOT}/scripts/_fitlio_compose.sh"
fitlio_compose_set_args "$(pwd)"
if [[ "${FITLIO_COMPOSE_USE_ALT:-0}" -eq 1 ]]; then
  fitlio_compose_sync_marker "$(pwd)" 1
fi

echo "[fitlio-compose] files: ${FITLIO_COMPOSE_ARGS[*]}"

if [[ "${BUILD_IMAGES:-1}" == "1" ]]; then
  echo "[fitlio-compose] building api + web"
  docker compose "${FITLIO_COMPOSE_ARGS[@]}" build api web
fi

echo "[fitlio-compose] up -d"
docker compose "${FITLIO_COMPOSE_ARGS[@]}" up -d

echo "[fitlio-compose] ps"
docker compose "${FITLIO_COMPOSE_ARGS[@]}" ps

VERIFY_PORT="${FITLIO_HTTPS_VERIFY_PORT:-443}"
if [[ -f "${ROOT}/.fitlio-k8s-alt-ports" ]] || [[ "${FITLIO_COMPOSE_USE_ALT:-0}" -eq 1 ]]; then
  VERIFY_PORT="8443"
fi

echo "[fitlio-compose] loopback health (port ${VERIFY_PORT})"
if curl -fsS -m 10 "https://127.0.0.1:${VERIFY_PORT}/health" -k -H "Host: fitlio-jay.duckdns.org" >/dev/null 2>&1; then
  echo "[fitlio-compose] health OK"
else
  echo "[fitlio-compose] warn: loopback health failed — check: docker compose logs nginx web api --tail 30"
fi

echo "[fitlio-compose] public URL: https://fitlio-jay.duckdns.org:${VERIFY_PORT}/"
echo "[fitlio-compose] done"
