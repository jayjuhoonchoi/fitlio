# HTTPS Setup — Let's Encrypt (2026-05-23)

## Result
- https://fitlio-jay.duckdns.org:8443/health → 200 OK
- Certificate: Let's Encrypt, expires 2026-08-21, auto-renewal enabled

## Method
- DNS-01 challenge via certbot-dns-duckdns plugin
- No port 80 required (used DuckDNS token to create TXT record)

## Steps
1. Install certbot-dns-duckdns plugin
2. Create /etc/letsencrypt/duckdns.ini with DuckDNS token
3. Run certbot certonly --authenticator dns-duckdns
4. Restart docker compose → nginx auto-detected cert and switched to HTTPS config

## Key Files
- /etc/letsencrypt/live/fitlio-jay.duckdns.org/fullchain.pem
- /etc/letsencrypt/live/fitlio-jay.duckdns.org/privkey.pem
- nginx/entrypoint/40-fitlio-ssl-auto.sh (cert detection logic)

## Notes
- nginx publishes 8443→443, so external access is :8443
- Port 443 inbound already existed in fitlio-sg
- Next step: redirect http:8080 → https:8443