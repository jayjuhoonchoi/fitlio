from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Attendance, Member, FitnessClass, Membership
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter()

class CheckInRequest(BaseModel):
    class_id: int
    phone_last4: str

def get_this_month_usage(db, member_id):
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    return db.query(Attendance).filter(
        Attendance.member_id == member_id,
        Attendance.checked_in_at >= month_start
    ).count()

def get_nearest_class(db):
    now = datetime.utcnow()
    return db.query(FitnessClass).filter(
        FitnessClass.schedule >= now
    ).order_by(FitnessClass.schedule.asc()).first()

@router.get("/classes/nearest")
def nearest_class(db: Session = Depends(get_db)):
    fitness_class = get_nearest_class(db)
    if not fitness_class:
        raise HTTPException(status_code=404, detail="No upcoming classes")
    return {
        "id": fitness_class.id,
        "name": fitness_class.name,
        "instructor": fitness_class.instructor,
        "schedule": fitness_class.schedule,
        "capacity": fitness_class.capacity,
        "current_count": fitness_class.current_count
    }

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
        Attendance.checked_in_at >= datetime(today.year, today.month, today.day)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already checked in today")

    # 멤버십 확인
    membership = db.query(Membership).filter(
        Membership.member_id == member.id,
        Membership.status == "active"
    ).first()

    # 이용권 횟수 체크
    if membership and membership.monthly_limit:
        used = get_this_month_usage(db, member.id)
        if used >= membership.monthly_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Monthly limit reached ({used}/{membership.monthly_limit})"
            )

    # 출석 기록 저장
    attendance = Attendance(
        member_id=member.id,
        class_id=request.class_id,
        status="present"
    )
    db.add(attendance)
    db.commit()

    # 이용권 현황 계산
    membership_info = None
    if membership:
        used = get_this_month_usage(db, member.id)
        if membership.monthly_limit:
            membership_info = {
                "plan": membership.plan,
                "used": used,
                "limit": membership.monthly_limit,
                "remaining": membership.monthly_limit - used
            }
        else:
            membership_info = {
                "plan": "unlimited",
                "used": used,
                "limit": None,
                "remaining": None
            }

    return {
        "message": f"✅ {member.full_name} checked in successfully!",
        "member_name": member.full_name,
        "class_name": fitness_class.name,
        "checked_in_at": attendance.checked_in_at,
        "membership": membership_info
    }

@router.get("/attendances")
def get_attendances(db: Session = Depends(get_db)):
    attendances = db.query(Attendance).all()
    return attendances