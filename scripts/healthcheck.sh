#!/bin/bash
# Fitlio external health check script
# WARNING: Run from outside EC2 only. Hairpin NAT makes internal checks unreliable.

URL="http://fitlio-jay.duckdns.org:8080/health"
EXPECTED=200

STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL")

if [ "$STATUS" -eq "$EXPECTED" ]; then
  echo "✅ $(date) — $URL — $STATUS OK"
else
  echo "❌ $(date) — $URL — $STATUS FAIL"
  exit 1
fi