#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required"
  exit 1
fi

routes=(
  "/"
  "/app/member"
  "/app/admin"
  "/app/tablet/demo-center"
  "/center/demo-center"
  "/assets/luxury_tokens.css"
)

echo "Benchmark base: ${BASE_URL}"
printf "%-36s %10s %10s %10s %10s\n" "Route" "dns" "connect" "ttfb" "total"
for route in "${routes[@]}"; do
  metrics="$(curl -sS -o /dev/null \
    -w "%{time_namelookup} %{time_connect} %{time_starttransfer} %{time_total}" \
    "${BASE_URL}${route}")"
  dns="$(echo "${metrics}" | awk '{print $1}')"
  connect="$(echo "${metrics}" | awk '{print $2}')"
  ttfb="$(echo "${metrics}" | awk '{print $3}')"
  total="$(echo "${metrics}" | awk '{print $4}')"
  printf "%-36s %10s %10s %10s %10s\n" "${route}" "${dns}" "${connect}" "${ttfb}" "${total}"
done

echo
echo "Tip: run twice and compare second-run TTFB/total for cache effects."
