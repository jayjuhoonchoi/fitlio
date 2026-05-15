# Tomorrow First Hour Plan

Objective: start with confidence and release readiness.

## 0-10 min
- Pull latest `main`
- Run:
  - `python3 -m compileall app tests`
  - `./scripts/smoke_core.sh`
- If smoke fails, stop and fix before feature work

## 10-25 min
- Verify payment progression with one fixture account:
  - purchase -> pending
  - webhook completed -> active
  - duplicate webhook -> ignored

## 25-40 min
- Verify moderation flow:
  - report created by member
  - appears in admin queue
  - hide + resolve updates queue and post visibility

## 40-55 min
- Verify tablet flow:
  - themed kiosk loads
  - 4-digit input + backspace + clear behavior
  - success message includes remaining usage and days-left
  - auto-reset after success

## 55-60 min
- Update release note draft with:
  - fixed items
  - known risks
  - rollback command
