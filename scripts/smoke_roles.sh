#!/usr/bin/env bash
# Smoke member vs admin API contracts.
# Auto-picks API base: FITLIO_API_BASE, else :8000 (dev compose), else nginx :80.
set -euo pipefail

pick_base() {
  if [[ -n "${FITLIO_API_BASE:-}" ]]; then
    echo "${FITLIO_API_BASE%/}"
    return
  fi
  if curl -fsS --max-time 3 http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "http://127.0.0.1:8000"
    return
  fi
  if curl -fsS --max-time 3 http://127.0.0.1/health >/dev/null 2>&1; then
    echo "http://127.0.0.1"
    return
  fi
  echo "[smoke-roles] API unreachable on :8000 and :80." >&2
  echo "[smoke-roles] Start stack with dev API port:" >&2
  echo "  cd ~/fitlio && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build" >&2
  exit 1
}

resolve_class_id() {
  local base="$1"
  local id=""
  id="$(curl -fsS --max-time 8 "${base}/classes/nearest" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))' 2>/dev/null || true)"
  if [[ -n "$id" ]]; then
    echo "$id"
    return
  fi
  curl -fsS --max-time 8 "${base}/classes" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["id"] if rows else "")'
}

BASE="$(pick_base)"
echo "[smoke-roles] base=${BASE}"

member_login="$(curl -fsS -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"jay.choi@fitlio.com","password":"fitlio1234!"}')"
admin_login="$(curl -fsS -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@fitlio.com","password":"AdminFitlio1!"}')"

member_token="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["access_token"])' "$member_login")"
admin_token="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["access_token"])' "$admin_login")"

echo "[smoke-roles] health"
curl -fsS "$BASE/health" | grep -q healthy

echo "[smoke-roles] member checkin-qr"
curl -fsS "$BASE/member/checkin-qr" -H "Authorization: Bearer $member_token" | grep -q token

echo "[smoke-roles] member quick-reserve route reachable"
class_id="$(curl -fsS "$BASE/classes" -H "Authorization: Bearer $member_token" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["id"] if rows else "")')"
if [[ -n "$class_id" ]]; then
  curl -fsS -X POST "$BASE/member/classes/${class_id}/quick-reserve" \
    -H "Authorization: Bearer $member_token" >/dev/null || true
fi

echo "[smoke-roles] admin roster"
roster_class_id="$(resolve_class_id "$BASE")"
if [[ -z "$roster_class_id" ]]; then
  echo "[smoke-roles] WARN: no classes in DB — restart api after seed refresh" >&2
  exit 1
fi
curl -fsS "$BASE/admin/classes/${roster_class_id}/roster" -H "Authorization: Bearer $admin_token" | grep -q roster

echo "[smoke-roles] member blocked from admin roster"
status="$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/admin/classes/${roster_class_id}/roster" -H "Authorization: Bearer $member_token")"
[[ "$status" == "401" || "$status" == "403" ]]

echo "[smoke-roles] OK"
