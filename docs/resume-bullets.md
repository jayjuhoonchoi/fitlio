# Resume Bullets — Fitlio (Draft)

## Backend
- Built and maintained a FastAPI SaaS platform (Fitlio) serving sports facility management across multiple centers
- Designed RESTful API with 18 PostgreSQL tables covering memberships, bookings, payments, and attendance
- Implemented JWT authentication with role-based access control (member/admin)

## Infrastructure & DevOps
- Deployed and operated production service on AWS EC2 (ap-southeast-2) with Docker Compose, Nginx reverse proxy, and DuckDNS
- Diagnosed and resolved production outages including AWS Security Group misconfigurations and Docker port conflicts
- Built CI/CD pipeline using GitHub Actions: automated pytest → SSH deploy → health check on every push
- Rotated compromised SSH credentials and migrated hardcoded secrets to environment variables

## Observability & Reliability
- Implemented external health check scripts and documented network debug playbooks (timeout vs refused diagnosis)
- Resolved Kubernetes/Docker port conflict on single node causing silent traffic drops (diagnosed via tcpdump)
- Maintained 80+ pytest test suite with 69% code coverage

## Problem Solving
- Diagnosed production timeout caused by missing SG inbound rule using systematic 3-step approach: app → port → AWS
- Fixed nginx ${FITLIO_DOMAIN} envsubst misconfiguration causing reverse proxy failures