import os
import threading
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Member, Membership, NotificationRequest

_lock = threading.Lock()
_last_run_at: datetime | None = None
_MIN_RUN_INTERVAL_SECONDS = 900


def _build_professional_message(
    member_name: str, plan: str, end_date: datetime, days_left: int
) -> str:
    human_plan = (plan or "membership").replace("_", " ").title()
    date_text = end_date.strftime("%Y-%m-%d")
    if days_left == 3:
        return (
            f"Dear {member_name}, this is a friendly reminder that your {human_plan} "
            f"membership will expire on {date_text} (in 3 days). To ensure uninterrupted "
            f"access to classes and bookings, please renew before the expiry date. "
            "If you need assistance, our team is happy to help."
        )
    return (
        f"Dear {member_name}, your {human_plan} membership is scheduled to expire on "
        f"{date_text} (in 1 day). Please renew today to avoid interruption to your "
        "bookings and check-in access. Thank you for training with Fitlio."
    )


def queue_membership_expiry_reminders(
    db: Session, reference_time: datetime | None = None
) -> dict:
    now = reference_time or datetime.utcnow()
    today = now.date()
    day_start = datetime(today.year, today.month, today.day)
    day_end = day_start + timedelta(days=1)
    memberships = (
        db.query(Membership, Member)
        .join(Member, Member.id == Membership.member_id)
        .filter(
            Membership.status == "active",
            Membership.end_date >= now,
            Membership.end_date <= now + timedelta(days=4),
        )
        .all()
    )
    created = 0
    skipped = 0
    for membership, member in memberships:
        days_left = (membership.end_date.date() - today).days
        if days_left not in (3, 1):
            continue
        topic = f"membership_expiry_d{days_left}"
        existing = (
            db.query(NotificationRequest)
            .filter(
                NotificationRequest.member_id == member.id,
                NotificationRequest.topic == topic,
                NotificationRequest.created_at >= day_start,
                NotificationRequest.created_at < day_end,
            )
            .first()
        )
        if existing:
            skipped += 1
            continue
        db.add(
            NotificationRequest(
                member_id=member.id,
                topic=topic,
                message=_build_professional_message(
                    member.full_name,
                    membership.plan,
                    membership.end_date,
                    days_left,
                ),
                status="pending",
            )
        )
        created += 1
    if created:
        db.commit()
    return {"created": created, "skipped": skipped}


def maybe_queue_membership_expiry_reminders() -> dict:
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
        result = queue_membership_expiry_reminders(db, reference_time=now)
        return {"status": "ok", **result}
    except Exception:
        return {"status": "error"}
    finally:
        db.close()
