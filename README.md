# 🏋️ Fitlio — Sports Facility Management SaaS

## 🌍 Overview
Fitlio is a production-grade SaaS platform built for a real gym in Gwanghwamun, Seoul.
Members book classes, track memberships, and check in by phone number.
Owners get a live dashboard with attendance stats and membership status.

## 🛠️ Tech Stack
🐍 Backend: FastAPI + PostgreSQL  
🐳 Container: Docker + Docker Compose  
🏗️ IaC: Terraform  
☁️ Cloud: AWS EC2 (t3.micro, ap-southeast-2)  
🌐 Web Server: Nginx + Let's Encrypt  
⚙️ CI/CD: GitHub Actions  
📊 Monitoring: Prometheus + Grafana + Node Exporter  
🔔 Notification: Slack Webhook + Block Kit  
🔒 Security: Trivy (0 vulnerabilities)  
☁️ Serverless: AWS Lambda + EventBridge  

## 🏗️ Architecture
👨‍💻 Developer pushes code → 🤖 GitHub Actions tests → 🚀 Deploys to AWS EC2  
🌐 Nginx handles HTTPS → ⚡ FastAPI serves API → 🗄️ PostgreSQL stores data  
📡 Prometheus scrapes metrics → 📊 Grafana visualizes dashboards  
💬 Slack receives deployment notifications  
⏰ EventBridge triggers Lambda daily → 🔍 Scans expiring memberships → 📲 Slack alert  

## 💪 Key Features
🔐 HTTPS with Let's Encrypt SSL  
🔄 Automated SSL renewal (certbot + pre/post hooks)  
🚀 Automated CI/CD pipeline (test → deploy → notify)  
📊 Real-time monitoring dashboard  
🏗️ Infrastructure as Code (Terraform)  
🤫 Zero hardcoded secrets (.env + GitHub Secrets)  
🛡️ Security scanning (Trivy — 0 CRITICAL, 0 HIGH)  
🏃 Membership & class booking system  
📱 Attendance check-in by phone number  
👑 Admin dashboard (stats + members + check-ins)  
🌏 International phone number support (20 countries)  
🇰🇷🇦🇺 Korean/English language switch  
🤖 Serverless membership expiry alerts (Lambda + EventBridge)  
🌱 Automated DB seeding with startup report

## 🌐 DNS (DuckDNS)
Terraform allocates an **Elastic IP** for the Fitlio EC2 instance, so the **public IPv4 stays the same across normal stop/start** (unlike ephemeral public IPs). Still keep `fitlio-jay.duckdns.org` pointed at the address from `terraform output` (first deploy, accidental DNS drift, or EIP replacement).
If the recorded IP and DuckDNS diverge, clients may see **HTTPS timeouts** even when the cluster and app are healthy.

## ⚡ Quick ops (copy/paste helpers)
From `terraform/`:

- **Print Elastic IP:** `terraform output -raw ec2_public_ip`
- **Print example SSH:** `terraform output -raw ssh_example`
- **HTTPS health (after DNS points at the EIP):** `curl -fsS -o /dev/null -w "%{http_code}\n" https://fitlio-jay.duckdns.org/health`
- **Check public DNS (bypass local cache):** `dig +short fitlio-jay.duckdns.org A @8.8.8.8`
- **Run preflight checks (local base):** `./scripts/preflight_env.sh http://127.0.0.1:8000`
- **Run preflight checks (HTTPS/DNS):** `./scripts/preflight_env.sh http://127.0.0.1:8000 fitlio-jay.duckdns.org`

## HTTPS one-shot fix

When HTTPS is flaky, use the one-shot script to enforce a stable sequence:

1. Validate DNS A record matches current public IP.
2. Bring stack up in HTTP fallback mode (service stays available).
3. Request/renew certificate through webroot challenge.
4. Restart nginx so HTTPS template is auto-selected.
5. Verify `https://<domain>/health`.

Run:

`./scripts/fix_https.sh fitlio-jay.duckdns.org jayjuhoonchoi@gmail.com ~/fitlio`

If DNS is wrong, the script exits early with the exact expected IP.

## Notification Dispatch Modes

Fitlio notifications support safe dry-run and real-run provider mode.

- `NOTIFICATION_REAL_RUN=0` (default): delivery adapters simulate success with `dryrun-*` IDs.
- `NOTIFICATION_REAL_RUN=1`: provider keys are required.
  - Email: `SENDGRID_API_KEY`
  - SMS: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

Admin notification operations:

- `POST /admin/notifications/membership-reminders/run` queue D-3 / D-1 reminders
- `POST /admin/notifications/dispatch/run` process pending notifications
- `GET /admin/notifications?status=&channel=` filter queue
- `GET /admin/notifications/summary` queue KPI snapshot

## Sprint smoke helpers

- Environment preflight:
  - `./scripts/preflight_env.sh http://127.0.0.1:8000`
  - with DNS/cert checks: `./scripts/preflight_env.sh http://127.0.0.1:8000 fitlio-jay.duckdns.org`

- Core local smoke:
  - `./scripts/smoke_core.sh`
  - or custom base URL: `./scripts/smoke_core.sh https://fitlio-jay.duckdns.org`

- Quick page benchmark:
  - `./scripts/bench_pages.sh`
  - or custom base URL: `./scripts/bench_pages.sh https://fitlio-jay.duckdns.org`
  - run twice; compare second-run `time_starttransfer` and `time_total` for cache effects

- QA checklist:
  - `docs/today-qa-checklist.md`

- Next-session kickoff:
  - `docs/tomorrow-first-hour.md`