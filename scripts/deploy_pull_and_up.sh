#!/usr/bin/env bash
# EC2 / CI: docker compose down + up using the same file set as fix_https
# (respects ~/fitlio/.fitlio-k8s-alt-ports or FITLIO_USE_K8S_ALT_PORTS=1).
#
# Git fetch/reset is done by the caller (e.g. GitHub Actions) unless RUN_GIT_SYNC=1.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${FITLIO_DIR:-$ROOT}"

if [[ "${RUN_GIT_SYNC:-0}" == "1" ]]; then
  git fetch origin main
  git reset --hard origin/main
fi

# shellcheck source=/dev/null
source "${ROOT}/scripts/_fitlio_compose.sh"
fitlio_compose_set_args "$(pwd)"
# Persist overlay choice for later deploys / CI (gitignored marker on disk).
if [[ "${FITLIO_COMPOSE_USE_ALT:-0}" -eq 1 ]]; then
  fitlio_compose_sync_marker "$(pwd)" 1
else
  fitlio_compose_sync_marker "$(pwd)" 0
fi

echo "[fitlio-deploy] compose: ${FITLIO_COMPOSE_ARGS[*]}"
docker compose "${FITLIO_COMPOSE_ARGS[@]}" down
docker compose "${FITLIO_COMPOSE_ARGS[@]}" up -d --build
