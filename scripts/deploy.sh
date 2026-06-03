#!/usr/bin/env bash
# EC2 deploy entrypoint: k3s if installed, else docker compose.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v k3s >/dev/null 2>&1 && [[ -f /etc/rancher/k3s/k3s.yaml ]]; then
  echo "[fitlio-deploy] k3s detected → deploy_k8s.sh"
  exec bash "${ROOT}/scripts/deploy_k8s.sh" "$@"
fi

echo "[fitlio-deploy] k3s not found → deploy_compose.sh (ports 8080/8443)"
exec bash "${ROOT}/scripts/deploy_compose.sh" "$@"
