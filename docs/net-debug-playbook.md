# 네트워크 장애 진단 플레이북

## 원칙
1. EC2 안에서 자기 공인 IP로 curl 금지 (헤어핀 — timeout/refused 오진 가능)
2. 반드시 외부 클라이언트(맥/LTE)로 검증
3. tcpdump는 외부 curl과 반드시 동시에 실행

## 분기표

| 외부 curl 결과 | tcpdump eth0 | 원인 | 다음 액션 |
|---|---|---|---|
| timeout | 0 packets | SG/NACL/EIP/DuckDNS 문제 | AWS 콘솔 SG 인바운드 전체 확인 |
| timeout | SYN 들어옴, 응답 없음 | k8s CNI 가로채거나 iptables DROP | systemctl status k3s |
| refused | SYN+RST | 포트 미LISTEN 또는 publish 불일치 | docker ps + ss -tlnp |
| 200 OK | — | 정상 또는 자가복구 | 장애 정의 재확인 |

## 진단 순서 (고정)

1. 외부(맥/LTE)에서 `curl -v --max-time 10 https://<도메인>/health` (프로덕션 기본 443) 또는 `http://...` / `:8443` 등 실제 공개 URL
2. EC2: `docker ps` + `ss -tlnp | grep <포트>`
3. AWS 콘솔 → 인스턴스 → Security 탭 → **인스턴스에 붙은 SG 전체** 인바운드 확인
4. EC2: `sudo timeout 20 tcpdump -n -i eth0 tcp port <포트>` (동시에 외부 curl)
5. 0 packets → SG/NACL/EIP/DuckDNS 재확인
6. packets 있음 → `systemctl status k3s` / iptables 확인

## 자주 하는 실수
- SG 한 개만 수정하고 인스턴스에 다른 sg 붙어있는지 안 보기
- compose ports 바꾼 뒤 SG 안 바꾸기
- EC2 재부팅 후 k3s 자동시작으로 CNI 충돌 (enabled 여부 확인 필요)
- 맥에서 systemctl/iptables 실행 (맥에는 없음)

## tcpdump 명령 (복붙용)
**프로덕션 기본(80/443):**
```bash
# 터미널 A (EC2)
sudo timeout 20 tcpdump -n -i eth0 'tcp port 80 or tcp port 443'

# 터미널 B (맥) — 동시에
curl -v --max-time 15 https://fitlio-jay.duckdns.org/health
```
**k8s-alt-ports(8080/8443) 오버레이를 쓰는 경우:**
```bash
sudo timeout 20 tcpdump -n -i eth0 'tcp port 8080 or tcp port 8443'
curl -v --max-time 15 https://fitlio-jay.duckdns.org:8443/health
```

## 실제 사례
- [Incident 001](./incident-001-sg-8080.md): SG 8080 누락 → 외부 timeout → SG 추가 → 200 복구 (2026-05-17)