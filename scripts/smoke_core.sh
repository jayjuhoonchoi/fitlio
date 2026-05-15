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

# Critical route smoke for recently introduced features
code_quick_reserve="$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/member/classes/1/quick-reserve" || true)"
[[ "${code_quick_reserve}" == "401" || "${code_quick_reserve}" == "403" || "${code_quick_reserve}" == "404" || "${code_quick_reserve}" == "409" ]] && pass "quick-reserve route is reachable" || fail "quick-reserve route is reachable"

code_weekly_report="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/reports/weekly-performance" || true)"
[[ "${code_weekly_report}" == "401" || "${code_weekly_report}" == "403" ]] && pass "weekly-performance auth gate" || fail "weekly-performance auth gate"

code_discover="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/centers/discover?query=core" || true)"
[[ "${code_discover}" == "401" || "${code_discover}" == "403" ]] && pass "center discover auth gate" || fail "center discover auth gate"

code_tablet_contract="$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"center_slug":"non-existent-center","phone_last4":"0000"}' "${BASE_URL}/centers/tablet/check-in" || true)"
[[ "${code_tablet_contract}" == "404" ]] && pass "tablet contract endpoint failure contract" || fail "tablet contract endpoint failure contract"

code_member_qr="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/member/checkin-qr" || true)"
[[ "${code_member_qr}" == "401" || "${code_member_qr}" == "403" ]] && pass "member checkin-qr auth gate" || fail "member checkin-qr auth gate"

code_tablet_qr="$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"center_slug":"smoke-center","token":"01234567890123456789012345"}' "${BASE_URL}/centers/tablet/check-in-qr" || true)"
[[ "${code_tablet_qr}" == "401" ]] && pass "tablet check-in-qr rejects invalid token" || fail "tablet check-in-qr rejects invalid token"

code_roster="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/classes/1/roster" || true)"
[[ "${code_roster}" == "401" || "${code_roster}" == "403" ]] && pass "admin class roster auth gate" || fail "admin class roster auth gate"

code_premium="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/reports/premium-overview?months=6" || true)"
[[ "${code_premium}" == "401" || "${code_premium}" == "403" ]] && pass "premium-overview auth gate" || fail "premium-overview auth gate"

echo "[smoke] done"
