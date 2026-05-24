# Fitlio Operations Runbook

## DB Backup

### Automatic
- Schedule: daily at 16:00 UTC (02:00 AEST)
- Script: `scripts/backup_db.sh`
- Destination: `s3://fitlio-db-backup-jay/daily/`
- Log: `/var/log/fitlio-backup.log`

### Manual backup
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@52.64.121.214
cd ~/fitlio
bash scripts/backup_db.sh
```

### Verify backups exist
```bash
aws s3 ls s3://fitlio-db-backup-jay/daily/
```

### Restore from backup
```bash
# Download backup
aws s3 cp s3://fitlio-db-backup-jay/daily/<filename>.sql.gz /tmp/

# Restore into running container
gunzip -c /tmp/<filename>.sql.gz | docker exec -i fitlio-db-1 psql -U fitlio fitlio
```

## Health Check
```bash
# From external network only (not inside EC2)
./scripts/healthcheck.sh
# Expected: 200 OK
```

## Deploy
```bash
# Automatic: push to main branch triggers GitHub Actions
# Manual:
ssh -i ~/.ssh/id_ed25519 ubuntu@52.64.121.214
cd ~/fitlio
git fetch origin main
git reset --hard origin/main
docker compose down
docker compose up -d
```

## First 5 Commands When Something Is Wrong
```bash
# 1. Check from external network
curl -v --max-time 10 https://fitlio-jay.duckdns.org/health

# 2. Check containers
docker ps

# 3. Check ports
ss -tlnp | grep -E ':(80|443)'

# 4. Check nginx logs
docker logs fitlio-nginx-1 --tail 20

# 5. Check API logs
docker logs fitlio-api-1 --tail 20
```

## SSL Certificate
- Provider: Let's Encrypt
- Expires: 2026-08-21
- Auto-renewal: enabled via certbot
- Manual renewal: `sudo certbot renew`