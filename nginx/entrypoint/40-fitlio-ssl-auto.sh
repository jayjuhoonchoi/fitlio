#!/bin/sh
set -eu

DOMAIN="${FITLIO_DOMAIN:-fitlio-jay.duckdns.org}"
export FITLIO_DOMAIN="$DOMAIN"
CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

# Templates use ${FITLIO_DOMAIN}; nginx image only envsubst's *.template, so expand here.
# Limit substitution to FITLIO_DOMAIN so nginx vars like $host / $request_uri stay intact.
if [ -f "$CERT" ] && [ -f "$KEY" ]; then
  echo "[fitlio-nginx] SSL cert found for ${DOMAIN}; enabling HTTPS config"
  envsubst '$FITLIO_DOMAIN' < /etc/nginx/templates/default.https.conf > /etc/nginx/conf.d/default.conf
else
  echo "[fitlio-nginx] SSL cert missing for ${DOMAIN}; using HTTP-only fallback config"
  envsubst '$FITLIO_DOMAIN' < /etc/nginx/templates/default.http.conf > /etc/nginx/conf.d/default.conf
fi
