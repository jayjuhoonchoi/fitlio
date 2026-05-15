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
- Success message and remaining usage show after check-in
- Error state shown for invalid check-in and submit lock recovers

## 5. Core smoke endpoints
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

## Failure remediation quick guide
- Preflight Docker failure: start Docker daemon/Desktop, then rerun preflight.
- Preflight health failure: `docker compose up -d --build` then `curl -fsS http://127.0.0.1:8000/health`.
- Smoke auth-gate mismatch (not 401/403): verify auth middleware and router include order.
- Tablet contract mismatch: inspect `app/centers.py` `tablet_check_in` error paths and headers.

## Exit criteria
- P0/P1 open issues: 0
- All high-risk flows verified at least once end-to-end
- Commits are split by function and branch is releasable
