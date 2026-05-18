#!/usr/bin/env sh
# Called by certbot --manual-auth-hook (DNS-01 via DuckDNS TXT).
# Env from certbot: CERTBOT_DOMAIN, CERTBOT_VALIDATION
# Requires: DUCKDNS_TOKEN
set -eu
TOKEN="${DUCKDNS_TOKEN:?export DUCKDNS_TOKEN (DuckDNS v3 token)}"
DOMAIN="${CERTBOT_DOMAIN:?}"
VAL="${CERTBOT_VALIDATION:?}"
SUB="${DOMAIN%.duckdns.org}"
if [ "$SUB" = "$DOMAIN" ]; then
  echo "[duckdns-acme] expected *.duckdns.org, got: $DOMAIN" >&2
  exit 1
fi
curl -fsS "https://www.duckdns.org/update?domains=${SUB}&token=${TOKEN}&txt=${VAL}"
# TXT propagation (DuckDNS + resolvers)
sleep "${DUCKDNS_TXT_PROPAGATION_SECONDS:-75}"
