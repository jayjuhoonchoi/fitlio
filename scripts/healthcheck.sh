#!/usr/bin/env bash
# Fitlio external health check — run from laptop/cron, NOT from inside the same EC2 (hairpin).
# FITLIO_HEALTH_URL overrides default (HTTPS prod).
set -euo pipefail

URL="${FITLIO_HEALTH_URL:-http://fitlio-jay.duckdns.org:8080/health}"
EXPECTED="${FITLIO_HEALTH_EXPECT:-200}"

STATUS="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 15 "$URL" || echo 000)"

if [[ "$STATUS" == "$EXPECTED" ]]; then
  echo "✅ $(date -u +%Y-%m-%dT%H:%M:%SZ) — $URL — $STATUS OK"
else
  echo "❌ $(date -u +%Y-%m-%dT%H:%M:%SZ) — $URL — got $STATUS expected $EXPECTED"
  exit 1
fi
