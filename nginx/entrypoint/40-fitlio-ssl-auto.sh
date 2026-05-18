#!/bin/sh
set -eu

DOMAIN="${FITLIO_DOMAIN:-fitlio-jay.duckdns.org}"
export FITLIO_DOMAIN="$DOMAIN"
export FITLIO_PORT_IN_REDIRECT="${FITLIO_PORT_IN_REDIRECT:-}"
CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

# Templates use ${FITLIO_DOMAIN}, ${FITLIO_PORT_IN_REDIRECT}; nginx image only envsubst's *.template.
# ${FITLIO_PORT_IN_REDIRECT}: e.g. ":8443" when host maps TLS to 8443; empty when public HTTPS is :443.
# Limit envsubst vars so nginx vars like $host / $request_uri stay intact.
SUBST='$FITLIO_DOMAIN $FITLIO_PORT_IN_REDIRECT'
if [ -f "$CERT" ] && [ -f "$KEY" ]; then
  echo "[fitlio-nginx] SSL cert found for ${DOMAIN}; enabling HTTPS config"
  envsubst "$SUBST" < /etc/nginx/templates/default.https.conf > /etc/nginx/conf.d/default.conf
else
  echo "[fitlio-nginx] SSL cert missing for ${DOMAIN}; using HTTP-only fallback config"
  envsubst "$SUBST" < /etc/nginx/templates/default.http.conf > /etc/nginx/conf.d/default.conf
fi
