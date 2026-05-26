# Fitlio 아키텍처

## 인프라
- AWS EC2 ap-southeast-2 (시드니)
- EIP: 52.64.121.214
- 도메인: fitlio-jay.duckdns.org (DuckDNS)
- OS: Ubuntu

## 컨테이너 구성 (2026-05-20 기준)

| 이름 | 이미지 | 호스트 포트 | 역할 |
|---|---|---|---|
| fitlio-nginx-1 | nginx:latest | 8080→80, 8443→443 | 리버스 프록시 |
| fitlio-api-1 | fitlio-api | 8000→8000 | FastAPI 앱 |
| fitlio-db-1 | postgres:15 | 5432→5432 | 데이터베이스 |
| fitlio-grafana-1 | grafana/grafana | 3000→3000 | 모니터링 |
| fitlio-prometheus-1 | prom/prometheus | 9090→9090 | 메트릭 수집 |
| fitlio-node-exporter-1 | node-exporter | 9100→9100 | 노드 메트릭 |

## 요청 흐름
브라우저 → SG(8080 인바운드) → EC2 ENI → nginx:8080 → api:8000 → postgres:5432

## 보안 그룹 (fitlio-sg) 인바운드

| 포트 | 용도 |
|---|---|
| 22 | SSH |
| 80 | HTTP (certbot ACME용으로 유지) |
| 8080 | Nginx HTTP |
| 8443 | Nginx HTTPS |
| 8000 | FastAPI 직접 접근 |
| 3000 | Grafana |
| 9090 | Prometheus |
| 5432 | PostgreSQL |
| 9100 | Node Exporter |

## k3s 상태
- 설치됨, inactive
- 자동시작: 2026-05-17 disabled
- 재활성화 시 CNI(10.42.x/10.43.x)가 포트 충돌 가능

## Route Tracing Example: POST /auth/login





## Database Models (18 tables)

| Model | Table | Description |
|---|---|---|
| Member | members | User accounts, login, role (member/admin) |
| FitnessClass | fitness_classes | Class schedule, capacity |
| Booking | bookings | Member-class reservation |
| Membership | memberships | Plan, expiry, auto-renew |
| Payment | payments | Payment records |
| Attendance | attendance | Check-in records |
| InstructorProfile | instructor_profiles | Instructor info |
| NotificationRequest | notification_requests | Notification queue |
| Center | centers | Facility info |
| CenterMembership | center_memberships | Center-plan mapping |
| DirectMessage | direct_messages | Messaging |
| NotificationDeliveryAttempt | notification_delivery_attempts | Delivery log |
| InstructorReaction | instructor_reactions | Reactions |
| Suggestion | suggestions | User suggestions |
| CommunityPost | community_posts | Community feed |
| CommunityReaction | community_reactions | Post reactions |
| ContentReport | content_reports | Content moderation |
| PaymentWebhookEvent | payment_webhook_events | Webhook log |

## Known Technical Debt
- [x] Terraform S3 remote backend configured (fitlio-db-backup-jay/terraform/fitlio.tfstate)
- [ ] Terraform state migration: run `terraform init` to migrate local state to S3



## 보안 그룹 (fitlio-sg) 인바운드 (2026-05-24 기준)

| 포트 | 용도 |
|---|---|
| 22 | SSH |
| 80 | HTTP (HTTPS 리다이렉트 + certbot) |
| 443 | HTTPS |

## 포트 격리 정책
- nginx만 외부 포트(80/443) 바인딩
- api, db, prometheus, grafana, node-exporter는 Docker 내부 네트워크만 사용
- 외부에서 DB, 모니터링 도구 직접 접근 불가


## Security Group (fitlio-sg) Inbound Rules (as of 2026-05-24)

| Port | Purpose |
|---|---|
| 22 | SSH access |
| 80 | HTTP (HTTPS redirect + certbot renewal) |
| 443 | HTTPS |

## Port Isolation Policy
- Only nginx binds to external ports (80/443)
- api, db, prometheus, grafana, node-exporter communicate via Docker internal network only
- Direct external access to DB and monitoring tools is blocked
- Principle of least privilege: expose only what is necessary

## Terraform Resources Managed
- VPC, subnets, IGW, route tables
- Security Group (22/80/443 only)
- EC2 t2.small + Elastic IP
- IAM role + S3 policy
- Lambda + CloudWatch Events (daily membership alerts + DB backup)
- Remote state: s3://fitlio-db-backup-jay/terraform/fitlio.tfstate

## Staging Environment

| | Production | Staging |
|---|---|---|
| URL | https://fitlio-jay.duckdns.org | https://fitlio-jay.duckdns.org:8443 |
| Branch | main | develop |
| DB | fitlio | fitlio_staging |
| Directory | ~/fitlio | ~/fitlio-staging |
| Deploy | Auto via GitHub Actions | Auto via GitHub Actions |