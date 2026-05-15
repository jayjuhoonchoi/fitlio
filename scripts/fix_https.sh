#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-fitlio-jay.duckdns.org}"
EMAIL="${2:-jayjuhoonchoi@gmail.com}"
PROJECT_DIR="${3:-$HOME/fitlio}"

echo "[fitlio-https] domain=${DOMAIN}"
echo "[fitlio-https] project=${PROJECT_DIR}"

cd "${PROJECT_DIR}"

if [[ ! -x "./scripts/preflight_env.sh" ]]; then
  echo "[fitlio-https] missing executable ./scripts/preflight_env.sh"
  echo "Run: chmod +x ./scripts/preflight_env.sh"
  exit 1
fi

echo "[fitlio-https] running environment preflight..."
./scripts/preflight_env.sh "http://127.0.0.1:8000" "${DOMAIN}"

CURRENT_IP="$(curl -4fsS https://ifconfig.me || true)"
DNS_IP="$(dig +short "${DOMAIN}" A @8.8.8.8 | tail -n 1 || true)"

echo "[fitlio-https] current_public_ip=${CURRENT_IP:-unknown}"
echo "[fitlio-https] dns_a_record=${DNS_IP:-missing}"

if [[ -z "${DNS_IP}" || -z "${CURRENT_IP}" || "${DNS_IP}" != "${CURRENT_IP}" ]]; then
  echo "[fitlio-https] DNS mismatch. Update ${DOMAIN} A record to ${CURRENT_IP} first."
  exit 1
fi

echo "[fitlio-https] starting stack with HTTP fallback first..."
docker compose up -d --build

echo "[fitlio-https] requesting/renewing certificate..."
sudo mkdir -p /var/www/certbot
sudo certbot certonly \
  --webroot -w /var/www/certbot \
  -d "${DOMAIN}" \
  --agree-tos -m "${EMAIL}" \
  --non-interactive \
  --keep-until-expiring

echo "[fitlio-https] reloading nginx with HTTPS template..."
docker compose restart nginx

echo "[fitlio-https] verify HTTPS"
curl -fsS -I "https://${DOMAIN}/health" | sed -n '1,10p'

echo "[fitlio-https] done"
