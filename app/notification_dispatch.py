import os
import threading
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Member, NotificationDeliveryAttempt, NotificationRequest
from app.notification_channels import (
    DispatchResult,
    deliver_email,
    deliver_inapp,
    deliver_sms,
)

_lock = threading.Lock()
_last_run_at: datetime | None = None
_MIN_RUN_INTERVAL_SECONDS = 300


def _backoff_delay_minutes(retry_count: int) -> int:
    if retry_count <= 0:
        return 5
    if retry_count == 1:
        return 15
    if retry_count == 2:
        return 60
    return 180


def _dispatch_row(row: NotificationRequest, member: Member | None) -> DispatchResult:
    channel = getattr(row, "channel", "email")
    if channel == "inapp":
        return deliver_inapp(recipient_id=row.member_id, message=row.message)
    if channel == "sms":
        phone = member.phone if member else None
        return deliver_sms(to_phone=phone, message=row.message)
    email = member.email if member else None
    return deliver_email(to_email=email, message=row.message)


def process_pending_notifications(db: Session, limit: int = 100) -> dict:
    now = datetime.utcnow()
    rows = (
        db.query(NotificationRequest)
        .filter(
            NotificationRequest.status == "pending",
            or_(
                NotificationRequest.next_attempt_at.is_(None),
                NotificationRequest.next_attempt_at <= now,
            ),
        )
        .order_by(NotificationRequest.created_at.asc(), NotificationRequest.id.asc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    sent = 0
    failed = 0
    queued_retry = 0
    for row in rows:
        member = None
        if row.member_id is not None:
            member = db.query(Member).filter(Member.id == row.member_id).first()
        result = _dispatch_row(row, member)
        db.add(
            NotificationDeliveryAttempt(
                notification_id=row.id,
                channel=getattr(row, "channel", "email"),
                status="sent" if result.delivered else "failed",
                provider_message_id=result.provider_message_id,
                error_message=result.error,
            )
        )
        if result.delivered:
            row.status = "sent"
            row.sent_at = now
            row.last_error = None
            sent += 1
        else:
            next_retry_count = (row.retry_count or 0) + 1
            row.retry_count = next_retry_count
            row.last_error = result.error or f"Dispatch failed channel={row.channel}"
            if next_retry_count >= (row.max_retries or 3):
                row.status = "failed"
                failed += 1
            else:
                row.next_attempt_at = now + timedelta(
                    minutes=_backoff_delay_minutes(next_retry_count)
                )
                queued_retry += 1
    if sent or failed or queued_retry:
        db.commit()
    return {
        "processed": len(rows),
        "sent": sent,
        "failed": failed,
        "queued_retry": queued_retry,
    }


def maybe_process_pending_notifications() -> dict:
    global _last_run_at
    if os.getenv("PYTEST_CURRENT_TEST"):
        return {"status": "skipped", "reason": "test_env"}
    now = datetime.utcnow()
    with _lock:
        if _last_run_at and (now - _last_run_at).total_seconds() < _MIN_RUN_INTERVAL_SECONDS:
            return {"status": "skipped", "reason": "interval"}
        _last_run_at = now
    db = SessionLocal()
    try:
        result = process_pending_notifications(db)
        return {"status": "ok", **result}
    except Exception:
        return {"status": "error"}
    finally:
        db.close()
