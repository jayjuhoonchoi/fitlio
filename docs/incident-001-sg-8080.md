# # Incident 001 — SG 8080 누락으로 외부 접속 불가

## 날짜

2026-05-17

## 증상

외부(맥)에서 curl 시 Connection timed out. EC2 내부 docker ps, ss -tlnp는 정상.

## 원인

compose가 8080→80으로 publish하고 있었으나, fitlio-sg 인바운드 규칙에 8080이 없었다. SYN 패킷이 ENI에서 drop됨.

## 진단 순서

1. 외부 curl → timeout 확인

2. EC2 내부 docker ps + ss -tlnp → 앱 정상 확인

3. AWS 콘솔 fitlio-sg 인바운드 목록 → 8080 누락 확인

## 해결

fitlio-sg에 8080, 8443 인바운드 규칙 추가. 외부 curl → 200 OK 복구.

## 재발 방지

compose ports 변경 시 SG 인바운드도 같이 확인한다.

인스턴스에 붙은 SG 전체를 본다, 한 개만 보지 않는다.

## 배운 것

- timeout이면 SG/NACL/EIP부터 본다. refused면 포트 미LISTEN.

- EC2 내부에서 자기 공인 IP curl은 헤어핀으로 신뢰 금지.

- k3s inactive여도 enabled면 재부팅 시 자동 시작된다.

