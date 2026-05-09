# Loki 로깅 전략

## 문제
t4g.small (2GB RAM)에서 Loki 직접 운영 시 메모리 부족

## 해결
Grafana Cloud 무료티어 사용
- 무료: 50GB 로그/월
- EC2 메모리 부담 없음
- Promtail → Grafana Cloud로 로그 전송

## 구현 계획
1. Grafana Cloud 가입
2. Promtail config에 cloud endpoint 추가
3. kubectl apply로 적용
