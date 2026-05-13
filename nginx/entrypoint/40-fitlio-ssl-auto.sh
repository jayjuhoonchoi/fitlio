#!/bin/sh
set -eu

DOMAIN="${FITLIO_DOMAIN:-fitlio-jay.duckdns.org}"
CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

if [ -f "$CERT" ] && [ -f "$KEY" ]; then
  echo "[fitlio-nginx] SSL cert found for ${DOMAIN}; enabling HTTPS config"
  cp /etc/nginx/templates/default.https.conf /etc/nginx/conf.d/default.conf
else
  echo "[fitlio-nginx] SSL cert missing for ${DOMAIN}; using HTTP-only fallback config"
  cp /etc/nginx/templates/default.http.conf /etc/nginx/conf.d/default.conf
fi
