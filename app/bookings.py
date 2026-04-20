from pydantic import BaseModel
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FitnessClass, Booking

router = APIRouter()
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
def book_class(class_id: int, member_id: int, db: Session = Depends(get_db)):
    fitness_class = db.query(FitnessClass).filter(FitnessClass.id == class_id).first()
    if not fitness_class:
        raise HTTPException(status_code=404, detail="Class not found")
    if fitness_class.current_count >= fitness_class.capacity:
        raise HTTPException(status_code=400, detail="Class is fully booked")
    existing = db.query(Booking).filter(
        Booking.member_id == member_id,
        Booking.class_id == class_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already booked")
    booking = Booking(member_id=member_id, class_id=class_id)
    fitness_class.current_count += 1
    db.add(booking)
    db.commit()
    return {"message": "Class booked successfully", "booking_id": booking.id}

@router.delete("/classes/{class_id}/cancel")
def cancel_booking(class_id: int, member_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(
        Booking.member_id == member_id,
        Booking.class_id == class_id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    fitness_class = db.query(FitnessClass).filter(FitnessClass.id == class_id).first()
    fitness_class.current_count -= 1
    booking.status = "cancelled"
    db.commit()
    return {"message": "Booking cancelled successfully"}

@router.post("/classes", status_code=201)
def create_class(req: ClassCreate, db: Session = Depends(get_db)):
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