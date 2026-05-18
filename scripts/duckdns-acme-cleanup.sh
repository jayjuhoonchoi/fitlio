#!/usr/bin/env sh
# Called by certbot --manual-cleanup-hook: clear DuckDNS TXT for ACME.
set -eu
TOKEN="${DUCKDNS_TOKEN:?export DUCKDNS_TOKEN}"
DOMAIN="${CERTBOT_DOMAIN:?}"
SUB="${DOMAIN%.duckdns.org}"
if [ "$SUB" = "$DOMAIN" ]; then
  echo "[duckdns-acme] expected *.duckdns.org, got: $DOMAIN" >&2
  exit 1
fi
curl -fsS "https://www.duckdns.org/update?domains=${SUB}&token=${TOKEN}&txt="
