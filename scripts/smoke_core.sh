#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"

echo "[smoke] base=${BASE_URL}"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

health="$(curl -fsS "${BASE_URL}/health" || true)"
[[ "${health}" == *"healthy"* ]] && pass "health endpoint" || fail "health endpoint"

# Unauthenticated access checks (should deny, not crash)
code_member_home="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/member/home" || true)"
[[ "${code_member_home}" == "401" || "${code_member_home}" == "403" ]] && pass "member/home auth gate" || fail "member/home auth gate"

code_posts="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/member/community/posts" || true)"
[[ "${code_posts}" == "401" || "${code_posts}" == "403" ]] && pass "community posts auth gate" || fail "community posts auth gate"

code_tablet="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/centers/tablet/non-existent-center" || true)"
[[ "${code_tablet}" == "404" ]] && pass "tablet config not-found behavior" || fail "tablet config not-found behavior"

echo "[smoke] done"
