from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Attendance, Member, FitnessClass
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class CheckInRequest(BaseModel):
    class_id: int
    phone_last4: str

@router.post("/check-in")
def check_in(request: CheckInRequest, db: Session = Depends(get_db)):
    # 전화번호 뒷자리 4개로 회원 찾기
    member = db.query(Member).filter(
        Member.phone.endswith(request.phone_last4),
        Member.is_active == True
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # 수업 존재 확인
    fitness_class = db.query(FitnessClass).filter(
        FitnessClass.id == request.class_id
    ).first()

    if not fitness_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # 오늘 이미 체크인했는지 확인
    today = datetime.utcnow().date()
    existing = db.query(Attendance).filter(
        Attendance.member_id == member.id,
        Attendance.class_id == request.class_id,
    ).filter(
        Attendance.checked_in_at >= datetime(today.year, today.month, today.day)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already checked in today")

    # 출석 기록 저장
    attendance = Attendance(
        member_id=member.id,
        class_id=request.class_id,
        status="present"
    )
    db.add(attendance)
    db.commit()

    return {
        "message": f"✅ {member.full_name} checked in successfully!",
        "member_name": member.full_name,
        "class_name": fitness_class.name,
        "checked_in_at": attendance.checked_in_at
    }

@router.get("/attendances")
def get_attendances(db: Session = Depends(get_db)):
    attendances = db.query(Attendance).all()
    return attendances