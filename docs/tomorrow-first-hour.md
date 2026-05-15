# Tomorrow First Hour Plan

Objective: start with confidence and release readiness.

## 0-10 min
- Pull latest `main`
- Run in strict order:
  1. `python3 -m compileall app tests`
  2. `./scripts/preflight_env.sh http://127.0.0.1:8000`
  3. `./scripts/smoke_core.sh`
- If preflight fails:
  - Docker missing/unreachable: start Docker or `sudo systemctl start docker`
  - Health unreachable: run `docker compose up -d --build` and re-check `curl -fsS http://127.0.0.1:8000/health`
  - Certbot missing (HTTPS flow): `sudo apt-get update && sudo apt-get install -y certbot`
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

## HTTPS deterministic recovery (EC2)
1. `./scripts/preflight_env.sh http://127.0.0.1:8000 fitlio-jay.duckdns.org`
2. `./scripts/fix_https.sh fitlio-jay.duckdns.org jayjuhoonchoi@gmail.com ~/fitlio`
3. `curl -fsS -I https://fitlio-jay.duckdns.org/health`
