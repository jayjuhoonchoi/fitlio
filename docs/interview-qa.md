# Interview Q&A — Fitlio DevOps Experience

## Infrastructure & Deployment

**Q1. Tell me about a production incident you've handled.**
Fitlio API was unreachable externally. Diagnosed using 3-step approach:
1. Checked containers (`docker ps`) → healthy
2. Checked ports (`ss -tlnp`) → 8080 listening
3. Checked AWS Security Group → port 8080 inbound rule was missing
Added the rule → resolved in under 30 minutes.
Key lesson: app layer was fine, problem was at AWS network layer.

**Q2. How do you deploy your application?**
Push to main → GitHub Actions triggers:
1. pytest runs (80 tests)
2. If tests pass → SSH into EC2
3. `git reset --hard origin/main` + `docker compose up -d --build`
4. External health check confirms 200 OK
Zero-downtime is not guaranteed at this scale, but deployment is fully automated and auditable.

**Q3. How do you handle secrets management?**
- Sensitive values (SECRET_KEY, DB password, SMTP password) stored in `.env` on EC2 only
- Never committed to GitHub
- GitHub Actions secrets for SSH key and EC2 host
- Next step: migrate to AWS Secrets Manager or SSM Parameter Store

**Q4. How is your infrastructure defined?**
Terraform manages: VPC, subnets, IGW, route tables, Security Group, EC2 instance, Elastic IP, IAM roles, Lambda, CloudWatch events.
Terraform state stored locally (next step: S3 backend with state locking).

**Q5. How do you monitor your application?**
- Prometheus scrapes metrics every 15s (API, node-exporter)
- Grafana visualizes metrics, defines alert rules
- Alert: `up{job="fitlio-api"} < 1` for 2 minutes → email notification
- External health check script runs from outside EC2 (avoids hairpin NAT)

---

## Networking & Security

**Q6. How did you handle port security?**
Initially all ports were exposed. Refactored to:
- External: 22 (SSH), 80 (HTTP redirect), 443 (HTTPS) only
- Internal: all other services (DB, Grafana, Prometheus) communicate via Docker internal network only
- Principle of least privilege applied to both SG and docker-compose port bindings

**Q7. What's the difference between connection timeout and connection refused?**
- Timeout: packet never reaches the host or response path fails. Usually SG/NACL/routing issue. Check with tcpdump.
- Refused: packet reaches host but nothing is listening on that port. Check with `ss -tlnp`.
- Diagnosis: `tcpdump -i eth0 tcp port <N>` while curling from external. 0 packets = AWS layer. Packets present = OS/container layer.

**Q8. How did you set up HTTPS?**
- Let's Encrypt via certbot with DNS-01 challenge (DuckDNS token)
- DNS-01 chosen because port 80 was blocked by k3s CNI at the time
- nginx detects certificate on startup via entrypoint script, switches to HTTPS config automatically
- Auto-renewal configured via certbot cron

**Q9. Tell me about a networking problem you solved.**
k3s CNI was intercepting port 443 traffic and routing to pod CIDR (10.43.x) instead of Docker nginx. Diagnosed via tcpdump: saw packets arriving at eth0 then forwarded to 10.43.7.163:443. Resolved by completely removing k3s from the node.

**Q10. How do you verify a deployment succeeded?**
External health check from outside EC2:
```bash
curl https://fitlio-jay.duckdns.org/health
# Expected: {"status":"healthy","service":"fitlio"}
```
Never test from inside EC2 using public IP — hairpin NAT causes false results.

---

## Docker & Application

**Q11. Why Docker Compose instead of Kubernetes?**
For a single-node deployment serving one product, Docker Compose provides sufficient orchestration with lower operational overhead. Kubernetes adds value for multi-node, multi-team environments with complex scaling needs. I've learned from experience that running both on the same node causes port conflicts via CNI.

**Q12. How do you structure your Docker networking?**
Single bridge network (`fitlio_default`). Only nginx binds to host ports (80/443). All other services communicate via Docker DNS (e.g., `api:8000`, `db:5432`). This isolates internal services from external access.

**Q13. How do you handle database migrations?**
Alembic for schema migrations. `ensure_columns()` runs on startup for additive changes. Production rule: never destructive migration without backup first.

**Q14. How do you back up your database?**
Daily automated backup via cron:
```bash
docker exec fitlio-db-1 pg_dump -U fitlio fitlio | gzip > backup.sql.gz
aws s3 cp backup.sql.gz s3://fitlio-db-backup-jay/daily/
```
Runs at 16:00 UTC (02:00 AEST) daily. EC2 has IAM role with S3 write permission.

**Q15. How do you handle application configuration?**
Environment variables via `.env` file on EC2. Docker Compose passes them to containers. Defaults defined in compose file for non-sensitive values. Sensitive values (passwords, keys) only in `.env`, never in code or repository.

---

## CI/CD & Quality

**Q16. How do you prevent bad code from reaching production?**
GitHub Actions runs pytest (80 tests, 69% coverage) before deploy job. Deploy job only runs if tests pass (`needs: test`). Failed deployments are visible in Actions log with exact error line.

**Q17. How would you roll back a bad deployment?**
```bash
git revert <commit>
git push  # triggers Actions → redeploys previous version
# Or manually on EC2:
git reset --hard <previous-commit>
docker compose up -d --build
```

**Q18. What would you improve about your CI/CD pipeline?**
1. Add staging environment — currently deploy directly to production
2. Docker image versioning — currently rebuilds on every deploy
3. Terraform state in S3 with locking — currently local state file
4. Secrets in AWS SSM — currently `.env` file on EC2

---

## Situational

**Q19. How do you handle being on-call from a different timezone?**
Grafana alert fires email when API is down for 2+ minutes. Runbook documents first 5 commands for any incident. Pre-departure checklist ensures all monitoring is verified before going offline.

**Q20. What's the biggest thing you'd do differently?**
Set up a staging environment from day one. Deploying directly to production means every mistake is a production incident. With staging, I could test infrastructure changes safely before applying to production.