from pydantic import BaseModel
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FitnessClass, Booking
from app.deps import get_current_user, require_admin

router = APIRouter(redirect_slashes=False)
class ClassCreate(BaseModel):
    name: str
    instructor: str
    schedule: datetime
    capacity: int = 20

@router.get("/classes")
def get_classes(db: Session = Depends(get_db)):
    classes = db.query(FitnessClass).all()
    return classes

@router.post("/classes/{class_id}/book")
def book_class(
    class_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if member_id != user["id"]:
        raise HTTPException(status_code=403, detail="Cannot book for another account")
    # Lock the class row so concurrent bookings cannot overshoot capacity (PostgreSQL).
    fitness_class = (
        db.query(FitnessClass)
        .filter(FitnessClass.id == class_id)
        .with_for_update()
        .first()
    )
    if not fitness_class:
        raise HTTPException(status_code=404, detail="Class not found")
    if fitness_class.current_count >= fitness_class.capacity:
        raise HTTPException(status_code=400, detail="Class is fully booked")
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
        raise HTTPException(status_code=400, detail="Already booked")
    booking = Booking(member_id=member_id, class_id=class_id)
    fitness_class.current_count += 1
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return {"message": "Class booked successfully", "booking_id": booking.id}


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
    fitness_class.current_count = max(0, fitness_class.current_count - 1)
    booking.status = "cancelled"
    db.commit()
    return {"message": "Booking cancelled successfully"}

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