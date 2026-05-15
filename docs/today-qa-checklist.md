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
- `GET /health` returns healthy payload
- `GET /member/home` returns membership summary (auth)
- `GET /member/community/posts` returns visible posts only (auth)
- `GET /centers/tablet/{slug}` returns tablet config

## Exit criteria
- P0/P1 open issues: 0
- All high-risk flows verified at least once end-to-end
- Commits are split by function and branch is releasable
