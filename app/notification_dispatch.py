import os
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Member, NotificationRequest

_lock = threading.Lock()
_last_run_at: datetime | None = None
_MIN_RUN_INTERVAL_SECONDS = 300


def process_pending_notifications(db: Session, limit: int = 100) -> dict:
    rows = (
        db.query(NotificationRequest)
        .filter(NotificationRequest.status == "pending")
        .order_by(NotificationRequest.created_at.asc(), NotificationRequest.id.asc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    sent = 0
    failed = 0
    for row in rows:
        member = None
        if row.member_id is not None:
            member = db.query(Member).filter(Member.id == row.member_id).first()
        has_contact = True
        if member is not None:
            has_contact = bool(member.email or member.phone)
        if has_contact:
            row.status = "sent"
            sent += 1
        else:
            row.status = "failed"
            failed += 1
    if sent or failed:
        db.commit()
    return {"processed": len(rows), "sent": sent, "failed": failed}


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
