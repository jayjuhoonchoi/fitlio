import json
import os
import urllib.request
from datetime import datetime, timedelta
import psycopg2


def get_db_connection():
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )


def fetch_expiring_members(cursor, days: int):
    target_date = (datetime.now() + timedelta(days=days)).date()
    cursor.execute("""
        SELECT u.full_name, u.phone, m.end_date
        FROM memberships m
        JOIN members u ON m.member_id = u.id
        WHERE m.end_date::date = %s
        AND m.status = 'active'
    """, (target_date,))
    return cursor.fetchall()


def build_slack_blocks(members_7: list, members_3: list, members_1: list) -> dict:
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🏋️ Fitlio 회원권 만료 알림",
                "emoji": True
            }
        },
        {"type": "divider"}
    ]

    sections = [
        ("7일 후 만료", "⚠️", members_7),
        ("3일 후 만료", "🔴", members_3),
        ("내일 만료", "🚨", members_1),
    ]

    has_any = False

    for label, emoji, members in sections:
        if not members:
            continue
        has_any = True
        member_lines = "\n".join(
            f"• {name} ({phone}) — {end_date.strftime('%Y-%m-%d')}"
            for name, phone, end_date in members
        )
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{label}*\n{member_lines}"
            }
        })
        blocks.append({"type": "divider"})

    if not has_any:
        return None

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Fitlio Lambda · {now} KST"
            }
        ]
    })

    return {"blocks": blocks}


def send_slack(payload: dict):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        os.environ['SLACK_WEBHOOK_URL'],
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    urllib.request.urlopen(req)


def lambda_handler(event, context):
    conn = get_db_connection()
    cursor = conn.cursor()

    members_7 = fetch_expiring_members(cursor, 7)
    members_3 = fetch_expiring_members(cursor, 3)
    members_1 = fetch_expiring_members(cursor, 1)

    cursor.close()
    conn.close()

    payload = build_slack_blocks(members_7, members_3, members_1)

    if not payload:
        return {'statusCode': 200, 'body': 'No expiring memberships today'}

    send_slack(payload)

    total = len(members_7) + len(members_3) + len(members_1)
    return {
        'statusCode': 200,
        'body': f'{total} members notified'
    }