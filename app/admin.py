from calendar import monthrange
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models import (
    Attendance,
    Booking,
    FitnessClass,
    InstructorProfile,
    Member,
    Membership,
    NotificationDeliveryAttempt,
    NotificationRequest,
    Payment,
)
from app.reminders import queue_membership_expiry_reminders
from app.notification_dispatch import process_pending_notifications

router = APIRouter(prefix="/admin")


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    total_members = db.query(Member).count()
    today = datetime.utcnow().date()
    today_start = datetime(today.year, today.month, today.day)
    today_attendance = (
        db.query(Attendance)
        .filter(Attendance.checked_in_at >= today_start)
        .count()
    )
    total_classes = db.query(FitnessClass).count()
    active_memberships = (
        db.query(Membership)
        .filter(Membership.status == "active", Membership.end_date >= datetime.utcnow())
        .count()
    )
    pending_notifications = (
        db.query(NotificationRequest).filter(NotificationRequest.status == "pending").count()
    )
    upcoming_7d_classes = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.schedule >= datetime.utcnow(),
            FitnessClass.schedule <= datetime.utcnow() + timedelta(days=7),
        )
        .count()
    )
    return {
        "total_members": total_members,
        "today_attendance": today_attendance,
        "total_classes": total_classes,
        "active_memberships": active_memberships,
        "pending_notifications": pending_notifications,
        "upcoming_7d_classes": upcoming_7d_classes,
    }


@router.get("/sales")
def sales_summary(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    now = datetime.utcnow()
    y = year or now.year
    m = month or now.month
    if m < 1 or m > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    last = monthrange(y, m)[1]
    start = datetime(y, m, 1)
    end = datetime(y, m, last, 23, 59, 59)
    q = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.status == "completed",
            Payment.created_at >= start,
            Payment.created_at <= end,
        )
        .scalar()
    )
    count = (
        db.query(Payment)
        .filter(
            Payment.status == "completed",
            Payment.created_at >= start,
            Payment.created_at <= end,
        )
        .count()
    )
    return {
        "year": y,
        "month": m,
        "completed_payment_count": count,
        "total_amount_cents": int(q or 0),
        "total_amount": (int(q or 0)) / 100.0,
    }


@router.get("/sales/trend")
def sales_trend(
    months: int = 6,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 24:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 24")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        start = datetime(y, m, 1)
        end = datetime(y, m, last, 23, 59, 59)
        total = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.status == "completed",
                Payment.created_at >= start,
                Payment.created_at <= end,
            )
            .scalar()
        )
        count = (
            db.query(Payment)
            .filter(
                Payment.status == "completed",
                Payment.created_at >= start,
                Payment.created_at <= end,
            )
            .count()
        )
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "payment_count": count,
                "total_amount_cents": int(total or 0),
                "total_amount": int(total or 0) / 100.0,
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/member-growth")
def member_growth_report(
    months: int = 12,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 36:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 36")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        start = datetime(y, m, 1)
        end = datetime(y, m, last, 23, 59, 59)
        new_members = (
            db.query(Member)
            .filter(Member.created_at >= start, Member.created_at <= end)
            .count()
        )
        total_members = db.query(Member).filter(Member.created_at <= end).count()
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "new_members": new_members,
                "total_members": total_members,
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/retention")
def retention_report(
    months: int = 12,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 36:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 36")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        end = datetime(y, m, last, 23, 59, 59)
        member_base = db.query(Member).filter(Member.created_at <= end).count()
        active_members = (
            db.query(func.count(func.distinct(Membership.member_id)))
            .filter(
                Membership.status == "active",
                Membership.start_date <= end,
                Membership.end_date >= end,
            )
            .scalar()
        ) or 0
        rate = (active_members / member_base * 100.0) if member_base else 0.0
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "member_base": member_base,
                "active_members": active_members,
                "retention_rate": round(rate, 2),
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/occupancy-trend")
def occupancy_trend_report(
    months: int = 6,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 24:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 24")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        start = datetime(y, m, 1)
        end = datetime(y, m, last, 23, 59, 59)
        classes = (
            db.query(FitnessClass)
            .filter(FitnessClass.schedule >= start, FitnessClass.schedule <= end)
            .all()
        )
        capacity_total = sum(c.capacity for c in classes)
        class_ids = [c.id for c in classes]
        booked_total = 0
        if class_ids:
            booked_total = (
                db.query(Booking)
                .filter(
                    Booking.class_id.in_(class_ids),
                    Booking.status == "confirmed",
                )
                .count()
            )
        fill_rate = (booked_total / capacity_total * 100.0) if capacity_total else 0.0
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "classes_count": len(classes),
                "capacity_total": capacity_total,
                "booked_total": booked_total,
                "fill_rate": round(fill_rate, 2),
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/member-risk")
def member_risk_report(
    days: int = 60,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if days < 14 or days > 180:
        raise HTTPException(status_code=400, detail="Days must be between 14 and 180")
    since = datetime.utcnow() - timedelta(days=days)
    classes_count = (
        db.query(FitnessClass)
        .filter(FitnessClass.schedule >= since, FitnessClass.schedule <= datetime.utcnow())
        .count()
    )
    denominator = max(classes_count, 1)
    members = db.query(Member).all()
    attendance_rows = (
        db.query(Attendance.member_id, func.count(Attendance.id))
        .filter(Attendance.checked_in_at >= since)
        .group_by(Attendance.member_id)
        .all()
    )
    attendance_by_member = {member_id: count for member_id, count in attendance_rows}
    booking_rows = (
        db.query(Booking.member_id, func.count(Booking.id))
        .join(FitnessClass, FitnessClass.id == Booking.class_id)
        .filter(
            Booking.status == "confirmed",
            FitnessClass.schedule >= since,
            FitnessClass.schedule <= datetime.utcnow(),
        )
        .group_by(Booking.member_id)
        .all()
    )
    booked_by_member = {member_id: count for member_id, count in booking_rows}
    rows = []
    for m in members:
        attendance_count = attendance_by_member.get(m.id, 0)
        booked_count = booked_by_member.get(m.id, 0)
        member_denominator = max(booked_count, denominator)
        attendance_rate = round((attendance_count / member_denominator) * 100.0, 2)
        rows.append(
            {
                "member_id": m.id,
                "member_no": getattr(m, "member_no", None),
                "full_name": m.full_name,
                "booked_count": booked_count,
                "attendance_count": attendance_count,
                "attendance_rate": attendance_rate,
                "at_risk": attendance_rate <= 50.0,
            }
        )
    rows.sort(key=lambda r: r["attendance_rate"])
    return rows


@router.get("/reports/class-utilization")
def class_utilization_report(
    days: int = 30,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if days < 1 or days > 180:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 180")
    start = datetime.utcnow() - timedelta(days=days)
    classes = (
        db.query(FitnessClass)
        .filter(FitnessClass.schedule >= start)
        .order_by(FitnessClass.schedule.desc())
        .all()
    )
    rows = []
    total_fill = 0.0
    for c in classes:
        booked = (
            db.query(Booking)
            .filter(Booking.class_id == c.id, Booking.status != "cancelled")
            .count()
        )
        fill = (booked / c.capacity * 100.0) if c.capacity else 0.0
        total_fill += fill
        rows.append(
            {
                "class_id": c.id,
                "name": c.name,
                "instructor": c.instructor,
                "schedule": c.schedule,
                "capacity": c.capacity,
                "booked_count": booked,
                "fill_rate": round(fill, 2),
            }
        )
    avg_fill = round(total_fill / len(rows), 2) if rows else 0.0
    return {
        "days": days,
        "average_fill_rate": avg_fill,
        "classes_count": len(rows),
        "rows": rows,
    }


@router.post("/notifications/membership-reminders/run")
def run_membership_reminders(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = queue_membership_expiry_reminders(db)
    return {"status": "queued", **result}


@router.post("/notifications/dispatch/run")
def run_notification_dispatch(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = process_pending_notifications(db)
    return {"status": "processed", **result}


@router.get("/attendances/recent")
def get_recent_attendances(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    attendances = (
        db.query(Attendance).order_by(Attendance.checked_in_at.desc()).limit(20).all()
    )
    result = []
    for a in attendances:
        member = db.query(Member).filter(Member.id == a.member_id).first()
        fitness_class = (
            db.query(FitnessClass).filter(FitnessClass.id == a.class_id).first()
        )
        result.append(
            {
                "member_name": member.full_name if member else "Unknown",
                "class_name": fitness_class.name if fitness_class else "Unknown",
                "checked_in_at": a.checked_in_at,
                "status": a.status,
            }
        )
    return result


@router.get("/members")
def get_members(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    members = db.query(Member).all()
    return [
        {
            "id": m.id,
            "full_name": m.full_name,
            "email": m.email,
            "phone": m.phone,
            "member_no": getattr(m, "member_no", None),
            "member_level": getattr(m, "member_level", "starter"),
            "is_active": m.is_active,
            "role": getattr(m, "role", "member"),
            "created_at": m.created_at,
        }
        for m in members
    ]


@router.get("/payments")
def list_payments(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    rows = (
        db.query(Payment).order_by(Payment.created_at.desc()).limit(min(limit, 500)).all()
    )
    return [
        {
            "id": p.id,
            "member_id": p.member_id,
            "membership_id": p.membership_id,
            "amount": p.amount / 100.0,
            "currency": p.currency,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in rows
    ]


@router.get("/classes")
def list_classes_admin(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    classes = db.query(FitnessClass).order_by(FitnessClass.schedule.asc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "instructor": c.instructor,
            "schedule": c.schedule,
            "capacity": c.capacity,
            "current_count": c.current_count,
        }
        for c in classes
    ]


class InstructorCreate(BaseModel):
    display_name: str = Field(..., min_length=1)
    hourly_rate_cents: int = Field(50_000, ge=0)
    pay_per_class_cents: int = Field(80_000, ge=0)
    email: str | None = None
    notes: str | None = None


class InstructorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1)
    hourly_rate_cents: int | None = Field(default=None, ge=0)
    pay_per_class_cents: int | None = Field(default=None, ge=0)
    email: str | None = None
    notes: str | None = None


class ClassCreateAdmin(BaseModel):
    name: str = Field(..., min_length=1)
    instructor: str = Field(..., min_length=1)
    schedule: datetime
    capacity: int = Field(default=20, ge=1, le=500)


class ClassUpdateAdmin(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    instructor: str | None = Field(default=None, min_length=1)
    schedule: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=500)


@router.get("/instructors")
def list_instructors(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    rows = db.query(InstructorProfile).order_by(InstructorProfile.display_name).all()
    return [
        {
            "id": r.id,
            "display_name": r.display_name,
            "hourly_rate_cents": r.hourly_rate_cents,
            "pay_per_class_cents": r.pay_per_class_cents,
            "email": r.email,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/instructors", status_code=201)
def create_instructor(
    body: InstructorCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    exists = (
        db.query(InstructorProfile)
        .filter(InstructorProfile.display_name == body.display_name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Instructor name already exists")
    row = InstructorProfile(
        display_name=body.display_name.strip(),
        hourly_rate_cents=body.hourly_rate_cents,
        pay_per_class_cents=body.pay_per_class_cents,
        email=body.email,
        notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "display_name": row.display_name}


@router.put("/instructors/{instructor_id}")
def update_instructor(
    instructor_id: int,
    body: InstructorUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instructor not found")
    if body.display_name is not None:
        old_name = row.display_name
        dup = (
            db.query(InstructorProfile)
            .filter(
                InstructorProfile.display_name == body.display_name.strip(),
                InstructorProfile.id != instructor_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Instructor name already exists")
        row.display_name = body.display_name.strip()
        (
            db.query(FitnessClass)
            .filter(FitnessClass.instructor == old_name)
            .update({"instructor": row.display_name}, synchronize_session=False)
        )
    if body.hourly_rate_cents is not None:
        row.hourly_rate_cents = body.hourly_rate_cents
    if body.pay_per_class_cents is not None:
        row.pay_per_class_cents = body.pay_per_class_cents
    if body.email is not None:
        row.email = body.email
    if body.notes is not None:
        row.notes = body.notes
    db.commit()
    db.refresh(row)
    return {"id": row.id, "display_name": row.display_name}


@router.delete("/instructors/{instructor_id}")
def delete_instructor(
    instructor_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instructor not found")
    has_upcoming = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.instructor == row.display_name,
            FitnessClass.schedule >= datetime.utcnow(),
        )
        .first()
    )
    if has_upcoming:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete instructor with upcoming classes",
        )
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.post("/classes", status_code=201)
def create_class_admin(
    body: ClassCreateAdmin,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if body.schedule <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Class schedule must be in the future")
    has_instructor_profiles = db.query(InstructorProfile).count() > 0
    if has_instructor_profiles:
        profile = (
            db.query(InstructorProfile)
            .filter(InstructorProfile.display_name == body.instructor.strip())
            .first()
        )
        if not profile:
            raise HTTPException(
                status_code=400,
                detail="Instructor must exist in instructor profiles",
            )
    row = FitnessClass(
        name=body.name.strip(),
        instructor=body.instructor.strip(),
        schedule=body.schedule,
        capacity=body.capacity,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.put("/classes/{class_id}")
def update_class_admin(
    class_id: int,
    body: ClassUpdateAdmin,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(FitnessClass).filter(FitnessClass.id == class_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.instructor is not None:
        row.instructor = body.instructor.strip()
    if body.schedule is not None:
        if body.schedule <= datetime.utcnow():
            raise HTTPException(
                status_code=400, detail="Class schedule must be in the future"
            )
        row.schedule = body.schedule
    if body.instructor is not None:
        has_instructor_profiles = db.query(InstructorProfile).count() > 0
        if has_instructor_profiles:
            profile = (
                db.query(InstructorProfile)
                .filter(InstructorProfile.display_name == body.instructor.strip())
                .first()
            )
            if not profile:
                raise HTTPException(
                    status_code=400,
                    detail="Instructor must exist in instructor profiles",
                )
    if body.capacity is not None:
        if body.capacity < row.current_count:
            raise HTTPException(
                status_code=400,
                detail="Capacity cannot be lower than current bookings",
            )
        row.capacity = body.capacity
        row.current_count = min(row.current_count, row.capacity)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "updated": True}


@router.delete("/classes/{class_id}")
def delete_class_admin(
    class_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(FitnessClass).filter(FitnessClass.id == class_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    db.query(Booking).filter(Booking.class_id == class_id).delete()
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/instructors/{instructor_id}/payroll")
def instructor_payroll(
    instructor_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    prof = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Instructor not found")
    last = monthrange(year, month)[1]
    start = datetime(year, month, 1)
    end = datetime(year, month, last, 23, 59, 59)
    cnt = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.instructor == prof.display_name,
            FitnessClass.schedule >= start,
            FitnessClass.schedule <= end,
        )
        .count()
    )
    gross = cnt * prof.pay_per_class_cents
    hours_equivalent = cnt * 1.5
    hourly_based = int(hours_equivalent * prof.hourly_rate_cents)
    recommended = max(gross, hourly_based)
    return {
        "instructor_id": prof.id,
        "display_name": prof.display_name,
        "year": year,
        "month": month,
        "classes_scheduled": cnt,
        "pay_per_class_cents": prof.pay_per_class_cents,
        "hourly_rate_cents": prof.hourly_rate_cents,
        "flat_total_cents": gross,
        "hourly_based_total_cents": hourly_based,
        "recommended_monthly_pay_cents": recommended,
        "recommended_monthly_pay": recommended / 100.0,
    }


class NotificationCreate(BaseModel):
    member_id: int | None = None
    topic: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    channel: str = Field(default="email", pattern="^(email|sms|inapp)$")


class NotificationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|sent|failed)$")


class MemberAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    member_no: str | None = None
    member_level: str | None = Field(default=None, pattern="^(starter|core|elite|vip)$")
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern="^(member|admin)$")


@router.get("/notifications")
def list_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    rows = (
        db.query(NotificationRequest)
        .order_by(NotificationRequest.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": r.id,
            "member_id": r.member_id,
            "topic": r.topic,
            "message": r.message,
            "channel": getattr(r, "channel", "email"),
            "status": r.status,
            "retry_count": getattr(r, "retry_count", 0),
            "max_retries": getattr(r, "max_retries", 3),
            "next_attempt_at": getattr(r, "next_attempt_at", None),
            "last_error": getattr(r, "last_error", None),
            "sent_at": getattr(r, "sent_at", None),
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/notifications", status_code=201)
def create_notification(
    body: NotificationCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = NotificationRequest(
        member_id=body.member_id,
        topic=body.topic.strip(),
        message=body.message.strip(),
        channel=body.channel,
        status="pending",
        retry_count=0,
        max_retries=3,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.patch("/notifications/{notification_id}/status")
def update_notification_status(
    notification_id: int,
    body: NotificationStatusUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = (
        db.query(NotificationRequest)
        .filter(NotificationRequest.id == notification_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.status = body.status
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.post("/notifications/{notification_id}/retry")
def retry_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = (
        db.query(NotificationRequest)
        .filter(NotificationRequest.id == notification_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.status = "pending"
    row.next_attempt_at = None
    row.last_error = None
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.get("/notifications/{notification_id}/attempts")
def notification_attempts(
    notification_id: int,
    limit: int = 30,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    rows = (
        db.query(NotificationDeliveryAttempt)
        .filter(NotificationDeliveryAttempt.notification_id == notification_id)
        .order_by(NotificationDeliveryAttempt.attempted_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )
    return [
        {
            "id": r.id,
            "notification_id": r.notification_id,
            "channel": r.channel,
            "status": r.status,
            "provider_message_id": r.provider_message_id,
            "error_message": r.error_message,
            "attempted_at": r.attempted_at,
        }
        for r in rows
    ]


@router.put("/members/{member_id}")
def update_member_admin(
    member_id: int,
    body: MemberAdminUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(Member).filter(Member.id == member_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    if body.full_name is not None:
        row.full_name = body.full_name.strip()
    if body.phone is not None:
        row.phone = body.phone.strip()
    if body.member_level is not None:
        row.member_level = body.member_level
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.role is not None:
        row.role = body.role
    if body.member_no is not None:
        normalized = body.member_no.strip()
        if normalized:
            dup = (
                db.query(Member)
                .filter(Member.member_no == normalized, Member.id != member_id)
                .first()
            )
            if dup:
                raise HTTPException(status_code=400, detail="Member number already exists")
            row.member_no = normalized
        else:
            row.member_no = None
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "full_name": row.full_name,
        "phone": row.phone,
        "member_no": row.member_no,
        "member_level": getattr(row, "member_level", "starter"),
        "is_active": row.is_active,
        "role": row.role,
    }
