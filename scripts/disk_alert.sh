#!/bin/bash
# Disk usage alert — sends email if usage exceeds threshold
# Run from EC2 via cron

THRESHOLD=80
USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
HOSTNAME=$(hostname)

if [ "$USAGE" -ge "$THRESHOLD" ]; then
  echo "WARNING: Disk usage is ${USAGE}% on ${HOSTNAME}" | \
  mail -s "Fitlio EC2 Disk Alert: ${USAGE}% used" jayjuhoonchoi@gmail.com
fi

echo "$(date) — Disk usage: ${USAGE}%" >> /var/log/fitlio-disk-check.log
