# Resume Bullets — Fitlio (Draft)

## Backend
- Built and maintained a FastAPI SaaS platform (Fitlio) for sports facility management with 101 API endpoints and 18 PostgreSQL tables
- Designed data models covering memberships, bookings, payments, attendance, and community features
- Implemented JWT authentication (HS256) with role-based access control (member/admin) and short-lived QR tokens (45min) for tablet check-in

## Infrastructure & DevOps
- Deployed production service on AWS EC2 t2.small (ap-southeast-2) with Docker Compose, Nginx reverse proxy, Let's Encrypt TLS, and DuckDNS
- Diagnosed and resolved production outages including AWS Security Group misconfigurations causing silent packet drops
- Built CI/CD pipeline using GitHub Actions: automated pytest → SSH deploy → external health check on every push to main
- Migrated hardcoded secrets (SECRET_KEY, POSTGRES_PASSWORD) to environment variables; rotated compromised SSH credentials

## Observability & Reliability
- Maintained 80+ pytest test suite with 69% code coverage across 2,500+ lines of application code
- Documented network debug playbooks distinguishing timeout vs refused errors using tcpdump + SG analysis
- Resolved Kubernetes CNI / Docker Compose port conflict on single node causing external traffic drops

## Problem Solving (Real Incidents)
- [Incident 001] Production timeout: diagnosed missing SG 8080 inbound rule via 3-step approach (app → port → AWS) — resolved in under 30 minutes
- [Incident 002] CI/CD failure: identified trailing whitespace in GitHub Secret EC2_USER as root cause after ruling out key format issues
- [Incident 003] Deployment failure: caught YAML indentation error (depends_on nested inside environment) from Actions log