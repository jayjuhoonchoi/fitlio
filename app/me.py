from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app import models

router = APIRouter(prefix="/api/me", tags=["me"])


def _calculate_age(birth_date):
    if not birth_date:
        return None
    today = datetime.utcnow().date()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


@router.get("/summary")
def my_summary(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    mid = user["id"]
    member = db.query(models.Member).filter(models.Member.id == mid).first()
    membership = (
        db.query(models.Membership)
        .filter(
            models.Membership.member_id == mid,
            models.Membership.status == "active",
        )
        .order_by(models.Membership.end_date.desc())
        .first()
    )

    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    visits_this_month = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.member_id == mid,
            models.Attendance.checked_in_at >= month_start,
        )
        .count()
    )

    days_left = None
    if membership and membership.end_date:
        days_left = max(0, (membership.end_date - now).days)

    limit = membership.monthly_limit if membership else None
    remaining = None
    if membership and limit is not None:
        remaining = max(0, limit - visits_this_month)

    bookings = (
        db.query(models.Booking)
        .filter(models.Booking.member_id == mid, models.Booking.status != "cancelled")
        .count()
    )

    return {
        "member": {
            "id": member.id if member else mid,
            "full_name": member.full_name if member else "",
            "email": member.email if member else "",
            "birth_date": getattr(member, "birth_date", None) if member else None,
            "age": _calculate_age(getattr(member, "birth_date", None)) if member else None,
            "level": getattr(member, "member_level", "starter") if member else "starter",
            "role": user.get("role", "member"),
        },
        "membership": (
            {
                "id": membership.id,
                "plan": membership.plan,
                "status": membership.status,
                "end_date": membership.end_date,
                "monthly_limit": membership.monthly_limit,
                "days_left": days_left,
                "visits_this_month": visits_this_month,
                "visits_remaining_in_plan": remaining,
            }
            if membership
            else None
        ),
        "active_bookings_count": bookings,
    }
