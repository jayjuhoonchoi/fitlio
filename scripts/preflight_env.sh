#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
DOMAIN="${2:-}"
REQUIRE_CERTBOT="${REQUIRE_CERTBOT:-0}"

pass() { echo "[PASS] $1"; }
warn() { echo "[WARN] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

echo "[preflight] base_url=${BASE_URL}"
if [[ -n "${DOMAIN}" ]]; then
  echo "[preflight] domain=${DOMAIN}"
fi

if ! command -v curl >/dev/null 2>&1; then
  fail "curl is required (install curl first)"
fi
pass "curl is installed"

if ! command -v docker >/dev/null 2>&1; then
  fail "docker is not installed (install Docker Engine/Desktop)"
fi
pass "docker is installed"

if ! docker compose version >/dev/null 2>&1; then
  fail "docker compose plugin unavailable (install Docker Compose v2)"
fi
pass "docker compose plugin is available"

if ! docker info >/dev/null 2>&1; then
  fail "docker daemon is not reachable (start Docker service/Desktop)"
fi
pass "docker daemon is reachable"

if [[ "${REQUIRE_CERTBOT}" == "1" || -n "${DOMAIN}" ]]; then
  if ! command -v certbot >/dev/null 2>&1; then
    fail "certbot is not installed (Ubuntu: sudo apt-get install -y certbot)"
  fi
  pass "certbot is installed"

  if [[ -n "${DOMAIN}" ]]; then
    if ! command -v dig >/dev/null 2>&1; then
      fail "dig is required for DNS checks (install dnsutils/bind tools)"
    fi
    current_ip="$(curl -4fsS https://ifconfig.me || true)"
    dns_ip="$(dig +short "${DOMAIN}" A @8.8.8.8 | awk 'NF {ip=$1} END {print ip}')"
    if [[ -z "${current_ip}" ]]; then
      warn "could not resolve current public IP (ifconfig.me unreachable)"
    else
      pass "public IP resolved (${current_ip})"
    fi
    if [[ -z "${dns_ip}" ]]; then
      fail "domain A record missing for ${DOMAIN}"
    fi
    pass "domain A record resolved (${dns_ip})"
    if [[ -n "${current_ip}" && "${dns_ip}" != "${current_ip}" ]]; then
      fail "DNS mismatch: ${DOMAIN} -> ${dns_ip}, expected ${current_ip}"
    fi
    pass "domain A record matches current public IP"
  fi
fi

health_payload="$(curl -fsS --max-time 5 "${BASE_URL}/health" || true)"
if [[ "${health_payload}" != *"healthy"* ]]; then
  fail "health endpoint is unreachable/unhealthy (${BASE_URL}/health)"
fi
pass "health endpoint is reachable"

echo "[preflight] done"
