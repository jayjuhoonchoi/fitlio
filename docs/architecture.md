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
- [x] datetime.utcnow() deprecated in Python 3.14 → fixed in app code (DB schema still naive)
- [ ] POSTGRES_PASSWORD hardcoded in docker-compose.yml → move to .env