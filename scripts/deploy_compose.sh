#!/usr/bin/env bash
# EC2 docker compose (8080/8443): build api + web, restart stack.
#
# Usage:
#   cd ~/fitlio && bash scripts/deploy_compose.sh
#   FITLIO_USE_K8S_ALT_PORTS=1 bash scripts/deploy_compose.sh   # 8080/8443 (default on this host)
#   BUILD_IMAGES=0 bash scripts/deploy_compose.sh                 # skip rebuild
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=/dev/null
source "${ROOT}/scripts/_fitlio_compose.sh"

# This EC2 serves HTTPS on 8443 (k3s/compose alt overlay).
if [[ "${FITLIO_USE_K8S_ALT_PORTS:-}" == "1" ]] \
  || [[ -f "${ROOT}/.fitlio-k8s-alt-ports" ]] \
  || ss -tln 2>/dev/null | grep -q ':8443 '; then
  export FITLIO_USE_K8S_ALT_PORTS=1
  fitlio_compose_sync_marker "$(pwd)" 1
fi

fitlio_compose_set_args "$(pwd)"

echo "[fitlio-compose] files: ${FITLIO_COMPOSE_ARGS[*]}"

compose_build() {
  # Avoid BuildKit attestation export error: "image already exists"
  local build_args=(--pull=false)
  if docker compose build --help 2>/dev/null | grep -q provenance; then
    build_args+=(--provenance=false --sbom=false)
  fi
  docker compose "${FITLIO_COMPOSE_ARGS[@]}" build "${build_args[@]}" api web
}

if [[ "${BUILD_IMAGES:-1}" == "1" ]]; then
  echo "[fitlio-compose] removing stale local tags (prevents buildx export conflict)"
  docker image rm -f fitlio-web:latest fitlio-api:latest 2>/dev/null || true

  echo "[fitlio-compose] building api + web"
  if ! compose_build; then
    echo "[fitlio-compose] retry build without attestations (legacy docker)"
    export BUILDX_NO_DEFAULT_ATTESTATIONS=1
    docker image rm -f fitlio-web:latest fitlio-api:latest 2>/dev/null || true
    compose_build
  fi
fi

echo "[fitlio-compose] up -d"
docker compose "${FITLIO_COMPOSE_ARGS[@]}" up -d

echo "[fitlio-compose] ps"
docker compose "${FITLIO_COMPOSE_ARGS[@]}" ps

VERIFY_PORT="${FITLIO_HTTPS_VERIFY_PORT:-443}"
if [[ "${FITLIO_COMPOSE_USE_ALT:-0}" -eq 1 ]]; then
  VERIFY_PORT="8443"
fi

echo "[fitlio-compose] loopback health (port ${VERIFY_PORT})"
if curl -fsS -m 10 "https://127.0.0.1:${VERIFY_PORT}/health" -k -H "Host: fitlio-jay.duckdns.org" >/dev/null 2>&1; then
  echo "[fitlio-compose] health OK"
else
  echo "[fitlio-compose] warn: loopback health failed — check: docker compose logs nginx web api --tail 30"
fi

echo "[fitlio-compose] proxy header (expect: web)"
curl -sI -m 10 "https://127.0.0.1:${VERIFY_PORT}/login" -k -H "Host: fitlio-jay.duckdns.org" 2>/dev/null | grep -i x-fitlio-proxy || true

echo "[fitlio-compose] public URL: https://fitlio-jay.duckdns.org:${VERIFY_PORT}/"
echo "[fitlio-compose] done"
