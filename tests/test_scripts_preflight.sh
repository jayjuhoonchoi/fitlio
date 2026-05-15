#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PRECHECK_SCRIPT="${REPO_ROOT}/scripts/preflight_env.sh"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

if [[ ! -f "${PRECHECK_SCRIPT}" ]]; then
  fail "preflight script file missing"
fi

SCRIPT_TEXT="$(<"${PRECHECK_SCRIPT}")"

if [[ "${SCRIPT_TEXT}" != *"set -euo pipefail"* ]]; then
  fail "strict shell mode missing"
fi
pass "strict shell mode present"

if [[ "${SCRIPT_TEXT}" != *"docker compose version"* ]]; then
  fail "docker compose precheck missing"
fi
pass "docker compose precheck present"

if [[ "${SCRIPT_TEXT}" != *"docker info"* ]]; then
  fail "docker daemon precheck missing"
fi
pass "docker daemon precheck present"

if [[ "${SCRIPT_TEXT}" != *"BASE_URL"* ]]; then
  fail "base URL support missing"
fi
pass "base URL support present"

if [[ "${SCRIPT_TEXT}" != *"health endpoint"* ]]; then
  fail "health reachability check missing"
fi
pass "health reachability check present"

if [[ "${SCRIPT_TEXT}" != *"certbot"* ]]; then
  fail "certbot conditional checks missing"
fi
pass "certbot conditional checks present"

echo "[test-scripts] done"
