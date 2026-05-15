# Fitlio Today QA Checklist

Owner: product engineering
Date: Friday sprint block

## 1. Login and session
- Member login success and redirect to member app
- Admin login success and redirect to admin app
- Invalid credentials show clear error

## 2. Membership and payment
- Member purchase starts in `pending` with checkout URL
- Webhook `completed` flips payment to `completed` and membership to `active`
- Webhook duplicate payload is ignored (idempotent)
- Webhook `failed/cancelled` cancels only `pending` memberships

## 3. Community moderation
- Member can report a community post
- Admin sees report in moderation queue
- Admin hide action removes content from member feed
- Admin can set report status to `resolved` or `rejected`

## 4. Tablet check-in
- Center branding applies (logo, accent, background, welcome text)
- 4-digit keypad input works with clear/reset
- **QR mode**: camera scan (or paste token) completes the same visit as PIN when code is valid
- Success message and remaining usage show after check-in
- Error state shown for invalid check-in and submit lock recovers

## 5. Member check-in QR (phone)
- Logged-in member loads **Front desk QR** card; canvas renders
- Refresh issues a new token; expired QR shows tablet error with retry hint
- `GET /member/checkin-qr` returns 401 without Bearer token

## 6. Admin class roster & one-tap attendance
- Classes tab: **Roster** loads confirmed bookings for a class
- **Mark present** respects booking, monthly cap, and duplicate same-day rules
- `GET /admin/classes/{id}/roster` is admin-gated

## 7. Core smoke endpoints
- Run deterministic command order:
  1. `./scripts/preflight_env.sh http://127.0.0.1:8000`
  2. `./scripts/smoke_core.sh`
- `GET /health` returns healthy payload
- `GET /member/home` returns membership summary (auth)
- `GET /member/community/posts` returns visible posts only (auth)
- `GET /centers/tablet/{slug}` returns tablet config
- `POST /member/classes/{id}/quick-reserve` route reachable (auth/guarded)
- `GET /admin/reports/weekly-performance` route reachable (admin-gated)
- `GET /centers/discover` route reachable (auth-gated)
- `POST /centers/tablet/check-in` returns contract-safe failure for invalid center
- `GET /member/checkin-qr` returns 401 without auth
- `POST /centers/tablet/check-in-qr` returns 401 for invalid token (non-JWT placeholder)
- `GET /admin/classes/1/roster` returns 401/403 without admin
- `GET /admin/reports/premium-overview` returns 401/403 without admin

## How you can confirm what changed (after `git pull`)
See **`docs/verify-changes.md`** for copy-paste commands: short git diff vs yesterday, full tests, smoke script, and UI URLs to hit.

## Failure remediation quick guide
- Preflight Docker failure: start Docker daemon/Desktop, then rerun preflight.
- Preflight health failure: `docker compose up -d --build` then `curl -fsS http://127.0.0.1:8000/health`.
- Smoke auth-gate mismatch (not 401/403): verify auth middleware and router include order.
- Tablet contract mismatch: inspect `app/centers.py` `tablet_check_in` error paths and headers.

## Exit criteria
- P0/P1 open issues: 0
- All high-risk flows verified at least once end-to-end
- Commits are split by function and branch is releasable
