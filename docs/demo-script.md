# 15-Minute Live Demo Script — Fitlio

## Setup (before demo, 2 minutes)
```bash
# Terminal 1 — health check ready
cd ~/fitlio

# Terminal 2 — EC2 SSH ready
ssh -i ~/.ssh/id_ed25519 ubuntu@52.64.121.214

# Browser tabs ready:
# 1. https://fitlio-jay.duckdns.org
# 2. https://github.com/jayjuhoonchoi/fitlio/actions
# 3. http://localhost:3001 (Grafana — SSH tunnel open)
```

---

## Minute 0–2: Product Overview
"Fitlio is a SaaS platform I built and operate for sports facility management.
It's running in production on AWS EC2 in Sydney — ap-southeast-2.
Let me show you the live service first."

→ Open https://fitlio-jay.duckdns.org
→ Show HTTPS padlock → "Let's Encrypt certificate, auto-renews every 90 days"
→ Show /health endpoint → {"status":"healthy","service":"fitlio"}

---

## Minute 2–5: Architecture Walkthrough
"Let me walk you through the architecture."


"External ports: only 22, 80, 443. Everything else is Docker internal network.
DB, Grafana, Prometheus — not reachable from outside."

→ Show docker ps on EC2
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## Minute 5–8: CI/CD Pipeline
"Every push to main triggers automated deployment."

→ Open GitHub Actions
→ Show recent green deployments
→ Walk through deploy.yml:
  - test job: pytest 80 tests
  - deploy job: SSH → git pull → docker compose up
  - "Deploy only runs if tests pass"

→ Show a real commit: "docs: add interview Q&A"
→ "This commit triggered a deploy. Test passed in 19 seconds, deploy in 45 seconds."

---

## Minute 8–11: Real Incident Demo
"Let me show you a real incident I diagnosed."

→ Open docs/incident-001-sg-8080.md
"External timeout. Containers healthy. Found missing SG inbound rule.
3-step diagnosis: app → port → AWS."

→ Show net-debug-playbook.md
"This is the playbook I wrote after the incident.
timeout vs refused — different root causes, different fix."

→ Show tcpdump command:
```bash
sudo timeout 20 tcpdump -n -i eth0 tcp port 443
```
"0 packets = AWS layer. Packets present = OS/container layer."

---

## Minute 11–13: Monitoring & Alerting
"Production needs observability."

→ Open Grafana (http://localhost:3001)
→ Show Alert rules → "Fitlio API Down"
→ "If API is down for 2 minutes, I get an email. This fires even when I'm in Australia."

→ Show S3 backup:
```bash
aws s3 ls s3://fitlio-db-backup-jay/daily/
```
"Daily automated DB backup. Cron runs at 2AM Sydney time."

---

## Minute 13–15: What I'd Do Differently
"If I were to do this again:"
1. Staging environment from day one
2. Terraform state in S3 with locking
3. Secrets in AWS SSM Parameter Store
4. Docker image versioning for faster rollback

"These are on my roadmap."

---

## Emergency Responses (if something breaks during demo)

**If health check fails:**
```bash
docker ps
docker logs fitlio-nginx-1 --tail 10
docker compose up -d
```

**If Actions shows red:**
"Let me read the log — first red line tells us everything."

**If asked something you don't know:**
"I haven't implemented that yet, but here's how I'd approach it..."