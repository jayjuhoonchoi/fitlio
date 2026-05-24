# Pre-Departure Checklist — Australia Working Holiday

## 출국 전 반드시 확인할 것

### 1. Infrastructure
- [ ] `https://fitlio-jay.duckdns.org/health` → 200 OK
- [ ] GitHub Actions 최근 배포 초록색
- [ ] EC2 EIP 고정 여부 확인 (재시작 시 IP 변경 주의)
- [ ] DuckDNS → 52.64.121.214 정합성 확인
- [ ] SSL 인증서 만료일 확인 (`sudo certbot certificates`)
- [ ] cron 백업 작동 확인 (`aws s3 ls s3://fitlio-db-backup-jay/daily/`)

### 2. GitHub Secrets
- [ ] EC2_HOST: 52.64.121.214
- [ ] EC2_USER: ubuntu
- [ ] EC2_SSH_KEY: 유효한 프라이빗 키
- [ ] SLACK_WEBHOOK_URL: 유효 여부 확인

### 3. EC2 상태
- [ ] k3s disabled 확인 (`systemctl is-enabled k3s`)
- [ ] docker compose 전체 컨테이너 healthy
- [ ] 디스크 사용량 확인 (`df -h`)
- [ ] 메모리 사용량 확인 (`free -h`)

### 4. 보안
- [ ] SG 인바운드: 22, 80, 443만 열려있는지 확인
- [ ] .env 파일 EC2에만 존재, GitHub에 없는지 확인
- [ ] SSH 키 백업 (로컬 안전한 곳에)

### 5. 모니터링
- [ ] Grafana 알림 규칙 "Fitlio API Down" Normal 상태
- [ ] 이메일 알림 테스트 완료

---

## 호주에서 장애 났을 때 — 20분 체크리스트

### Step 1 — 외부에서 확인 (2분)
```bash
curl -v --max-time 10 https://fitlio-jay.duckdns.org/health
./scripts/healthcheck.sh
```

### Step 2 — 컨테이너 상태 (3분)
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@52.64.121.214
docker ps
docker logs fitlio-nginx-1 --tail 20
docker logs fitlio-api-1 --tail 20
```

### Step 3 — 분기
| 증상 | 원인 | 조치 |
|---|---|---|
| timeout | SG 또는 EC2 다운 | AWS 콘솔 확인 |
| refused | 컨테이너 다운 | docker compose up -d |
| 500 error | 앱 에러 | docker logs fitlio-api-1 |
| SSL 에러 | 인증서 만료 | sudo certbot renew |

### Step 4 — 빠른 복구 (5분)
```bash
cd ~/fitlio
git fetch origin main
git reset --hard origin/main
docker compose down && docker compose up -d
```

### Step 5 — 헬스체크 확인
```bash
# 맥/LTE에서 실행 (EC2 내부 금지)
curl https://fitlio-jay.duckdns.org/health
```

---

## 비상 연락 / 비용 관리
- AWS 콘솔 월 예산 알람 설정 필요
- EC2 t2.small 월 예상 비용: ~$20 USD
- S3 백업 비용: 미미 (<$1 USD)
- Let's Encrypt: 무료, 90일마다 자동 갱신

---

## SSH 접속 명령 (복붙용)
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@52.64.121.214
```

## Grafana 접속 (복붙용)
```bash
ssh -i ~/.ssh/id_ed25519 -L 3001:172.18.0.5:3000 ubuntu@52.64.121.214 -N &
# 브라우저: http://localhost:3001
```