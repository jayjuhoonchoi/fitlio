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
  - PIN: 4-digit input + backspace + clear behavior
  - **QR: switch to QR mode; camera or pasted member token completes check-in**
  - success message includes remaining usage and days-left
  - auto-reset after success

## 55-60 min
- Update release note draft with:
  - fixed items
  - known risks
  - rollback command

## HTTPS deterministic recovery (EC2)
1. `./scripts/preflight_env.sh http://127.0.0.1:8000 fitlio-jay.duckdns.org`
2. **Port 80이 k8s 등으로 막혀 있으면:** `export DUCKDNS_TOKEN='…'` (DuckDNS v3 토큰) 후 같은 스크립트 → **DNS-01**
3. `./scripts/fix_https.sh fitlio-jay.duckdns.org jayjuhoonchoi@gmail.com ~/fitlio`
4. **`docker-compose.k8s-alt-ports.yml` 사용 중이면:** `export FITLIO_HTTPS_VERIFY_PORT=8443` 로 2~3번 실행 후 확인
5. 외부(맥/LTE): `curl -fsS -I https://fitlio-jay.duckdns.org/health` (또는 `:8443`)
6. (선택, 한 번만) `sudo FITLIO_DIR=$HOME/fitlio ./scripts/install_letsencrypt_deploy_hook.sh` — `certbot renew` 후 nginx 자동 reload
