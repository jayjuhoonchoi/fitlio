import boto3
import psycopg2
import os
import json
from datetime import datetime

def lambda_handler(event, context):
    db_host = os.environ['DB_HOST']
    db_name = os.environ['DB_NAME']
    db_user = os.environ['DB_USER']
    db_pass = os.environ['DB_PASSWORD']
    bucket  = os.environ['S3_BUCKET']

    date_str = datetime.utcnow().strftime('%Y-%m-%d_%H-%M')
    s3_key   = f"backups/fitlio_backup_{date_str}.sql"

    conn = psycopg2.connect(
        host=db_host, dbname=db_name,
        user=db_user, password=db_pass, port=5432
    )
    cursor = conn.cursor()

    # 모든 테이블 목록
    cursor.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
    """)
    tables = [row[0] for row in cursor.fetchall()]

    dump_lines = []
    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        dump_lines.append(f"-- Table: {table}")
        dump_lines.append(f"-- Columns: {cols}")
        for row in rows:
            dump_lines.append(json.dumps(list(row), default=str))
        dump_lines.append("")

    cursor.close()
    conn.close()

    content = "\n".join(dump_lines)

    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=content.encode('utf-8')
    )

    return {
        'statusCode': 200,
        'body': f"Backup saved to s3://{bucket}/{s3_key} ({len(tables)} tables)"
    }