from pydantic import BaseModel
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FitnessClass, Booking, Member
from app.deps import get_current_user, require_admin

router = APIRouter(redirect_slashes=False)
class ClassCreate(BaseModel):
    name: str
    instructor: str
    schedule: datetime
    capacity: int = 20


def _attempt_reserve(db: Session, class_id: int, member_id: int):
    # Lock class row so concurrent requests cannot overshoot capacity.
    fitness_class = (
        db.query(FitnessClass)
        .filter(FitnessClass.id == class_id)
        .with_for_update()
        .first()
    )
    if not fitness_class:
        raise HTTPException(status_code=404, detail="Class not found")
    existing = (
        db.query(Booking)
        .filter(
            Booking.member_id == member_id,
            Booking.class_id == class_id,
            Booking.status != "cancelled",
        )
        .first()
    )
    if existing:
        existing_detail = (
            "You already reserved this class."
            if existing.status == "confirmed"
            else "You are already on the waitlist for this class."
        )
        raise HTTPException(status_code=409, detail=existing_detail)

    class_is_full = fitness_class.current_count >= fitness_class.capacity
    booking = Booking(
        member_id=member_id,
        class_id=class_id,
        status="waiting" if class_is_full else "confirmed",
    )
    if not class_is_full:
        fitness_class.current_count += 1
    db.add(booking)
    db.commit()
    db.refresh(booking)

    if class_is_full:
        waitlist_position = (
            db.query(Booking)
            .filter(Booking.class_id == class_id, Booking.status == "waiting")
            .count()
        )
        return {
            "booking_id": booking.id,
            "status": "waitlisted",
            "message": "Class is full. You were added to the waitlist.",
            "waitlist_position": waitlist_position,
            "waitlisted": True,
        }
    return {
        "booking_id": booking.id,
        "status": "confirmed",
        "message": "Class reserved successfully.",
        "waitlisted": False,
    }

@router.get("/classes")
def get_classes(db: Session = Depends(get_db)):
    classes = db.query(FitnessClass).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "instructor": c.instructor,
            "schedule": c.schedule,
            "capacity": c.capacity,
            "current_count": c.current_count,
            "waitlist": db.query(Booking)
            .filter(Booking.class_id == c.id, Booking.status == "waiting")
            .count(),
        }
        for c in classes
    ]

@router.post("/classes/{class_id}/book")
def book_class(
    class_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if member_id != user["id"]:
        raise HTTPException(status_code=403, detail="Cannot book for another account")
    try:
        result = _attempt_reserve(db, class_id=class_id, member_id=member_id)
    except HTTPException as exc:
        if exc.status_code == 409:
            raise HTTPException(status_code=400, detail="Already booked")
        raise
    return {
        "message": result["message"],
        "booking_id": result["booking_id"],
        "waitlisted": result["waitlisted"],
        **(
            {"waitlist_position": result["waitlist_position"]}
            if "waitlist_position" in result
            else {}
        ),
    }


@router.post("/member/classes/{class_id}/quick-reserve")
def quick_reserve_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if user.get("role") != "member":
        raise HTTPException(status_code=403, detail="Member access required")
    member = db.query(Member).filter(Member.id == user["id"]).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if not member.is_active:
        raise HTTPException(status_code=403, detail="Inactive member account")
    return _attempt_reserve(db, class_id=class_id, member_id=member.id)


@router.get("/bookings/{member_id}")
def get_member_bookings(
    member_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if member_id != user["id"]:
        raise HTTPException(status_code=403, detail="Cannot view another account")
    rows = (
        db.query(Booking, FitnessClass)
        .join(FitnessClass, FitnessClass.id == Booking.class_id)
        .filter(Booking.member_id == member_id, Booking.status != "cancelled")
        .order_by(FitnessClass.schedule.asc())
        .all()
    )
    return [
        {
            "booking_id": b.id,
            "class_id": c.id,
            "name": c.name,
            "instructor": c.instructor,
            "schedule": c.schedule,
            "status": b.status,
        }
        for b, c in rows
    ]

@router.delete("/classes/{class_id}/cancel")
def cancel_booking(
    class_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if member_id != user["id"]:
        raise HTTPException(status_code=403, detail="Cannot cancel for another account")
    fitness_class = (
        db.query(FitnessClass)
        .filter(FitnessClass.id == class_id)
        .with_for_update()
        .first()
    )
    if not fitness_class:
        raise HTTPException(status_code=404, detail="Class not found")
    booking = (
        db.query(Booking)
        .filter(
            Booking.member_id == member_id,
            Booking.class_id == class_id,
            Booking.status != "cancelled",
        )
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    cancelled_status = booking.status
    booking.status = "cancelled"
    if cancelled_status == "confirmed":
        fitness_class.current_count = max(0, fitness_class.current_count - 1)
        next_waiting = (
            db.query(Booking)
            .filter(Booking.class_id == class_id, Booking.status == "waiting")
            .order_by(Booking.created_at.asc(), Booking.id.asc())
            .first()
        )
        if next_waiting:
            next_waiting.status = "confirmed"
            fitness_class.current_count += 1
    db.commit()
    return {"message": "Booking cancelled successfully"}


@router.get("/classes/{class_id}/waitlist")
def class_waitlist(class_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Booking, Member)
        .join(Member, Member.id == Booking.member_id)
        .filter(Booking.class_id == class_id, Booking.status == "waiting")
        .order_by(Booking.created_at.asc(), Booking.id.asc())
        .all()
    )
    return [
        {
            "booking_id": b.id,
            "member_id": m.id,
            "member_name": m.full_name,
            "member_no": getattr(m, "member_no", None),
            "requested_at": b.created_at,
        }
        for b, m in rows
    ]

@router.post("/classes", status_code=201)
def create_class(
    req: ClassCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    fitness_class = FitnessClass(
        name=req.name,
        instructor=req.instructor,
        schedule=req.schedule,
        capacity=req.capacity
    )
    db.add(fitness_class)
    db.commit()
    db.refresh(fitness_class)
    return {"message": "Class created successfully", "id": fitness_class.id}