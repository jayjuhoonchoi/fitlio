# Request Flow — Fitlio

xternal client (Mac/LTE)
→ DNS: fitlio-jay.duckdns.org → 52.64.121.214
→ AWS Security Group: port 8080 inbound (added 2026-05-17)
→ EC2 ENI
→ nginx:8080 (container port 80)
→ location / → proxy_pass http://api:8000
→ FastAPI (uvicorn) port 8000
→ main.py middleware (line 84): X-Fitlio-App: portal-v2
→ route handler
→ response
→ nginx adds: X-Fitlio-Proxy: api (default.http.conf line 84)
→ client receives response

## Full Path: curl → response

curl http://fitlio-jay.duckdns.org:8080/health
→ nginx location / (catch-all, line 77)
→ proxy_pass http://api:8000
→ main.py line 152: health_check()
→ returns {"status":"healthy","service":"fitlio"}


## Example: GET /health


curl -X POST http://fitlio-jay.duckdns.org:8080/auth/login
→ nginx location /auth/ (line 13)
→ proxy_pass http://api:8000/auth/login
→ app/routers.py line 58: login()
→ DB query: members table (email match)
→ app/auth.py line 18: create_access_token()
→ returns JWT token (expires 24h, HS256)


## Key Files

| File | Role |
|---|---|
| nginx/default.http.conf | Routing rules, proxy headers |
| app/main.py | FastAPI app, middleware, page routes |
| app/routers.py | Auth endpoints (/auth/register, /auth/login) |
| app/auth.py | Password hashing, JWT creation |
| app/models.py | DB schema (18 tables) |

## Response Headers Explained

| Header | Value | Added by | Line |
|---|---|---|---|
| X-Fitlio-App | portal-v2 | FastAPI middleware | main.py:90 |
| X-Fitlio-Proxy | api | nginx | default.http.conf:84 |