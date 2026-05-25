# Resume Bullets — Fitlio (Updated 2026-05-25)

## Backend
- Built and maintained a FastAPI SaaS platform (Fitlio) for sports facility management with 101 API endpoints and 18 PostgreSQL tables
- Designed data models covering memberships, bookings, payments, attendance, and community features
- Implemented JWT authentication (HS256) with role-based access control (member/admin) and short-lived QR tokens (45min) for tablet check-in

## Infrastructure & DevOps
- Deployed and operated production service on AWS EC2 t2.small (ap-southeast-2, Sydney) with Docker Compose, Nginx, Let's Encrypt TLS, and DuckDNS
- Managed infrastructure as code using Terraform: VPC, subnets, SG, EC2, Elastic IP, IAM roles, Lambda, CloudWatch Events
- Built CI/CD pipeline using GitHub Actions: automated pytest → SSH deploy → external health check on every push to main
- Enforced least-privilege security: only ports 22/80/443 exposed externally; DB, Grafana, Prometheus isolated in Docker internal network
- Automated daily PostgreSQL backup to S3 via cron + pg_dump; EC2 IAM role grants write-only S3 access
- Migrated hardcoded secrets (SECRET_KEY, POSTGRES_PASSWORD, SMTP password) to environment variables

## Observability & Reliability
- Configured Prometheus + Grafana monitoring stack with email alerting: fires when API down > 2 minutes
- Maintained 80+ pytest test suite with 69% code coverage across 2,500+ lines of application code
- Documented network debug playbooks distinguishing timeout vs refused errors using tcpdump + SG analysis
- Resolved Kubernetes CNI / Docker Compose port conflict on single node: diagnosed via tcpdump showing packets forwarded to 10.43.x Pod CIDR instead of nginx

## Problem Solving (Real Incidents)
- [Incident 001] Production timeout: diagnosed missing SG 8080 inbound rule via 3-step approach (app → port → AWS) — resolved in under 30 minutes
- [Incident 002] CI/CD failure: identified trailing whitespace in GitHub Secret EC2_USER as root cause after ruling out SSH key format issues
- [Incident 003] Deployment failure: caught YAML indentation error (depends_on nested inside environment) from Actions log
- [Incident 004] HTTPS timeout: diagnosed k3s CNI intercepting port 443 via tcpdump, resolved by removing k3s from production node