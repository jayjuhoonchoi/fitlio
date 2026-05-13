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
    NotificationRequest,
    Payment,
)

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


class NotificationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|sent|failed)$")


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
            "status": r.status,
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
        status="pending",
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
