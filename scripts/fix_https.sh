#!/usr/bin/env bash
# Obtain/renew Let's Encrypt cert and reload Fitlio nginx.
#
# Modes (auto):
#   • If DUCKDNS_TOKEN is set: DNS-01 via DuckDNS TXT (works when public port 80 is blocked).
#   • Else: HTTP-01 webroot (needs https://duckdns-domain/.well-known/... on port 80).
#
# Usage:
#   export DUCKDNS_TOKEN='your-duckdns-v3-token'   # recommended on conflicted hosts
#   ./scripts/fix_https.sh [domain] [email] [project_dir]
#
# Alt HTTPS port (with docker-compose.k8s-alt-ports.yml):
#   export FITLIO_HTTPS_VERIFY_PORT=8443
#   → docker compose automatically adds the k8s-alt-ports overlay (8080/8443).
# Or: export FITLIO_USE_K8S_ALT_PORTS=1
#
set -euo pipefail

DOMAIN="${1:-fitlio-jay.duckdns.org}"
EMAIL="${2:-jayjuhoonchoi@gmail.com}"
PROJECT_DIR="${3:-$HOME/fitlio}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HTTPS_VERIFY_PORT="${FITLIO_HTTPS_VERIFY_PORT:-443}"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_fitlio_compose.sh"

echo "[fitlio-https] domain=${DOMAIN}"
echo "[fitlio-https] project=${PROJECT_DIR}"
echo "[fitlio-https] mode=$([ -n "${DUCKDNS_TOKEN:-}" ] && echo dns-01-duckdns || echo http-01-webroot)"

cd "${PROJECT_DIR}"

fitlio_compose_set_args "${PROJECT_DIR}"
fitlio_compose_sync_marker "${PROJECT_DIR}" "${FITLIO_COMPOSE_USE_ALT}"
if [[ "${FITLIO_COMPOSE_USE_ALT}" -eq 1 ]]; then
  echo "[fitlio-https] compose=standard+k8s-alt-ports (host 8080→80, 8443→443)"
else
  echo "[fitlio-https] compose=standard (host 80→80, 443→443)"
fi

if [[ ! -x "./scripts/preflight_env.sh" ]]; then
  echo "[fitlio-https] missing executable ./scripts/preflight_env.sh"
  exit 1
fi

chmod +x "${SCRIPT_DIR}/duckdns-acme-auth.sh" "${SCRIPT_DIR}/duckdns-acme-cleanup.sh" 2>/dev/null || true

echo "[fitlio-https] running environment preflight..."
./scripts/preflight_env.sh "http://127.0.0.1:8000" "${DOMAIN}"

CURRENT_IP="$(curl -4fsS https://ifconfig.me || true)"
DNS_IP="$(dig +short "${DOMAIN}" A @8.8.8.8 | tail -n 1 || true)"

echo "[fitlio-https] current_public_ip=${CURRENT_IP:-unknown}"
echo "[fitlio-https] dns_a_record=${DNS_IP:-missing}"

if [[ -z "${DNS_IP}" || -z "${CURRENT_IP}" || "${DNS_IP}" != "${CURRENT_IP}" ]]; then
  echo "[fitlio-https] DNS mismatch. Point ${DOMAIN} A record to ${CURRENT_IP:-the public IP of this host} first."
  exit 1
fi

echo "[fitlio-https] starting stack (nginx needed for webroot mode; harmless for DNS mode)..."
docker compose "${FITLIO_COMPOSE_ARGS[@]}" up -d --build

if [[ -n "${DUCKDNS_TOKEN:-}" ]]; then
  echo "[fitlio-https] requesting certificate via DNS-01 (DuckDNS TXT)..."
  sudo certbot certonly \
    --non-interactive \
    --agree-tos \
    -m "${EMAIL}" \
    --preferred-challenges dns \
    --manual \
    --manual-public-ip-logging-ok \
    --manual-auth-hook "${SCRIPT_DIR}/duckdns-acme-auth.sh" \
    --manual-cleanup-hook "${SCRIPT_DIR}/duckdns-acme-cleanup.sh" \
    --keep-until-expiring \
    -d "${DOMAIN}"
else
  echo "[fitlio-https] requesting certificate via HTTP-01 webroot (public :80 must reach this nginx)..."
  sudo mkdir -p /var/www/certbot
  sudo certbot certonly \
    --non-interactive \
    --agree-tos \
    -m "${EMAIL}" \
    --webroot \
    -w /var/www/certbot \
    -d "${DOMAIN}" \
    --keep-until-expiring
fi

echo "[fitlio-https] reloading nginx (picks HTTPS template when certs exist)..."
docker compose "${FITLIO_COMPOSE_ARGS[@]}" restart nginx

echo "[fitlio-https] verify HTTPS (port ${HTTPS_VERIFY_PORT})..."
if [[ "${HTTPS_VERIFY_PORT}" == "443" ]]; then
  curl -fsS -I "https://${DOMAIN}/health" | sed -n '1,12p'
else
  # Same-host checks: avoid AWS hairpin when curling public DNS from EC2.
  echo "[fitlio-https] same-host (loopback :${HTTPS_VERIFY_PORT}, -k for fresh cert)..."
  curl -skI "https://127.0.0.1:${HTTPS_VERIFY_PORT}/health" | sed -n '1,12p'
fi
echo "[fitlio-https] from your laptop (needs SG TCP ${HTTPS_VERIFY_PORT} open): curl -fsS https://${DOMAIN}:${HTTPS_VERIFY_PORT}/health"

echo "[fitlio-https] done"
echo "[fitlio-https] For certbot renew → nginx reload, run once on the server:"
echo "  sudo FITLIO_DIR=${PROJECT_DIR} ${SCRIPT_DIR}/install_letsencrypt_deploy_hook.sh"
