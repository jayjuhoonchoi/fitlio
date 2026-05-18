#!/usr/bin/env bash
# Run ON EC2. Loopback checks only — do not curl public DNS from this host (hairpin).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${FITLIO_DIR:-$ROOT}"

# shellcheck source=/dev/null
source "${ROOT}/scripts/_fitlio_compose.sh"
fitlio_compose_set_args "$(pwd)"

echo "[fitlio-probe] marker: $([ -f .fitlio-k8s-alt-ports ] && echo yes || echo no)"
echo "[fitlio-probe] compose: ${FITLIO_COMPOSE_ARGS[*]}"
docker ps -a --filter name=nginx --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
echo "[fitlio-probe] listeners:"
sudo ss -tlnp 2>/dev/null | grep -E ':(80|443|8080|8443)\b' || true

if [[ "${FITLIO_COMPOSE_USE_ALT}" -eq 1 ]]; then
  echo -n "[fitlio-probe] http://127.0.0.1:8080/health → "
  curl -sS -o /dev/null -w "%{http_code}\n" --max-time 8 http://127.0.0.1:8080/health || echo "fail"
  echo -n "[fitlio-probe] https://127.0.0.1:8443/health → "
  curl -sk -o /dev/null -w "%{http_code}\n" --max-time 8 https://127.0.0.1:8443/health || echo "fail"
else
  echo -n "[fitlio-probe] http://127.0.0.1/health → "
  curl -sS -o /dev/null -w "%{http_code}\n" --max-time 8 http://127.0.0.1/health || echo "fail"
  echo -n "[fitlio-probe] https://127.0.0.1/health → "
  curl -sk -o /dev/null -w "%{http_code}\n" --max-time 8 https://127.0.0.1/health || echo "fail"
fi
