# Fitlio 아키텍처 (2026-05-17 기준)

## 인프라
- AWS EC2 ap-southeast-2 (시드니)
- EIP: 52.64.121.214
- 도메인: fitlio-jay.duckdns.org (DuckDNS)
- OS: Ubuntu

## 컨테이너 구성
| 이름 | 이미지 | 포트 | 역할 |
|---|---|---|---|
| fitlio-nginx-1 | nginx:latest | 8080→80, 8443→443 | 리버스 프록시 |
| fitlio-api-1 | fitlio-api | 8000→8000 | FastAPI 앱 |
| fitlio-db-1 | postgres:15 | 5432→5432 | 데이터베이스 |
| fitlio-grafana-1 | grafana/grafana | 3000→3000 | 모니터링 대시보드 |
| fitlio-prometheus-1 | prom/prometheus | 9090→9090 | 메트릭 수집 |
| fitlio-node-exporter-1 | node-exporter | 9100→9100 | 노드 메트릭 |

## 요청 흐름
브라우저 → SG(8080 인바운드) → EC2 ENI → nginx:8080 → api:8000 → postgres:5432

## 보안 그룹 (fitlio-sg) 인바운드
| 포트 | 용도 | 비고 |
|---|---|---|
| 22 | SSH | |
| 80 | HTTP | 현재 미사용, nginx는 8080으로 publish |
| 443 | HTTPS | 현재 미사용, nginx는 8443으로 publish |
| 8080 | Nginx HTTP | 2026-05-17 추가 |
| 8443 | Nginx HTTPS | 2026-05-17 추가 |
| 8000 | FastAPI 직접 접근 | |
| 3000 | Grafana | |
| 9090 | Prometheus | |
| 5432 | PostgreSQL | |
| 9100 | Node Exporter | |
| 30090 | Prometheus NodePort | k3s 잔재, 정리 필요 |
| 30030 | Grafana NodePort | k3s 잔재, 정리 필요 |

## k3s 상태
- 설치됨, 현재 inactive
- 자동시작: 2026-05-17 disabled 처리
- 위험: 재활성화 시 CNI(10.42.x/10.43.x)가 포트 충돌 가능
- 의사결정 필요: A) k3s 완전 제거 B) 전용 노드 분리

## 알려진 이슈
- SG에 80/443 열려있으나 nginx는 8080/8443 사용 중 → 정리 필요
- k3s NodePort 규칙(30090/30030) SG에 남아있음 → 정리 필요
- Nginx ${FITLIO_DOMAIN} envsubst 적용 여부 미확인 → 확인 필요