#!/bin/bash
# Fitlio DB backup script
# Dumps PostgreSQL from Docker container and uploads to S3
# Run from EC2: bash scripts/backup_db.sh

set -e

BUCKET="fitlio-db-backup-jay"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILENAME="fitlio-db-backup-${DATE}.sql.gz"
TMP_PATH="/tmp/${FILENAME}"

echo "[backup] Starting DB backup: ${DATE}"

# Step 1: pg_dump inside db container, compress with gzip
# pg_dump connects to PostgreSQL and exports all data as SQL
# gzip compresses it to save S3 storage
docker exec fitlio-db-1 pg_dump -U fitlio fitlio | gzip > "${TMP_PATH}"

echo "[backup] Dump complete: ${TMP_PATH}"

# Step 2: Upload to S3
# aws s3 cp copies local file to S3 bucket
aws s3 cp "${TMP_PATH}" "s3://${BUCKET}/daily/${FILENAME}"

echo "[backup] Uploaded to s3://${BUCKET}/daily/${FILENAME}"

# Step 3: Remove local temp file
rm "${TMP_PATH}"

echo "[backup] Done. Backup successful."