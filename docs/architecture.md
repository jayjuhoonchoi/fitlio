# Fitlio 아키텍처

## 인프라
- AWS EC2 ap-southeast-2 (시드니)
- 도메인: fitlio-jay.duckdns.org (DuckDNS)
- OS: Ubuntu

## 컨테이너 구성 (프로덕션 기본 `docker-compose.yml`)

| 이름 | 이미지 | 호스트 포트 | 역할 |
|---|---|---|---|
| fitlio-nginx-1 | nginx:latest | **80→80**, **443→443** | 리버스 프록시, TLS 종단 |
| fitlio-api-1 | fitlio-api | 8000→8000 | FastAPI 앱 |
| fitlio-db-1 | postgres:15 | 5432→5432 | 데이터베이스 |
| fitlio-grafana-1 | grafana/grafana | 3000→3000 | 모니터링 대시보드 |
| fitlio-prometheus-1 | prom/prometheus | 9090→9090 | 메트릭 수집 |
| fitlio-node-exporter-1 | node-exporter | 9100→9100 | 노드 메트릭 |

**호스트 80/443이 이미 점유된 경우**(예: k3s):  
`docker compose -f docker-compose.yml -f docker-compose.k8s-alt-ports.yml up -d`  
→ nginx **8080→80**, **8443→443**. 인증서는 **`DUCKDNS_TOKEN` + `scripts/fix_https.sh`(DNS-01)** 권장.

## 요청 흐름 (기본)
브라우저 → SG(**80/443** 인바운드) → EC2 ENI → nginx → api:8000 → postgres:5432

## HTTPS
- 인증서: Let’s Encrypt  
- **권장(80 막힘)**: `export DUCKDNS_TOKEN=...` 후 `./scripts/fix_https.sh` → DNS-01 (DuckDNS TXT)  
- **80 오픈 시**: 같은 스크립트, 토큰 없음 → HTTP-01 webroot  
- Nginx: 인증서 존재 시 `default.https.conf`, TLS1.2+1.3, `X-Forwarded-Proto` 전달.

## 보안 그룹 (예시; 실제 콘솔과 동기화)
프로덕션 기본: **TCP 22, 80, 443** (+ 필요 시 8000 등).  
`k8s-alt-ports` 사용 시 **8080, 8443** 추가.

## k3s / CNI (과거 이슈)
- 동일 노드에서 **노드 80을 CNI가 가로채면** Docker nginx로 트래픽이 안 들어갈 수 있음 → `tcpdump`로 `10.42.x`/`10.43.x` 경로 확인.  
- 장기: k3s 제거 또는 **Fitlio 전용 EC2** / 포트 오버레이 파일 사용.


## Route Tracing Example: POST /auth/login

```
client → nginx (location /auth/) → api:8000/auth/login
  → app/routers.py line 58: login()
  → DB query: Member.email == req.email
  → JWT token created
  → returns access_token
```


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
- app/auth.py line 5: SECRET_KEY hardcoded → move to environment variable
- datetime.utcnow() used in multiple files → deprecated in Python 3.14