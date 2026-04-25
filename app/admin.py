from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import get_db
from app.models import Member, FitnessClass, Attendance
from datetime import datetime

router = APIRouter(prefix="/admin")

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # 전체 회원 수
    total_members = db.query(Member).count()

    # 오늘 출석 수
    today = datetime.utcnow().date()
    today_start = datetime(today.year, today.month, today.day)
    today_attendance = db.query(Attendance).filter(
        Attendance.checked_in_at >= today_start
    ).count()

    # 전체 수업 수
    total_classes = db.query(FitnessClass).count()

    return {
        "total_members": total_members,
        "today_attendance": today_attendance,
        "total_classes": total_classes,
    }

@router.get("/attendances/recent")
def get_recent_attendances(db: Session = Depends(get_db)):
    # 최근 20개 체크인 기록
    attendances = db.query(Attendance).order_by(
        Attendance.checked_in_at.desc()
    ).limit(20).all()

    result = []
    for a in attendances:
        member = db.query(Member).filter(Member.id == a.member_id).first()
        fitness_class = db.query(FitnessClass).filter(FitnessClass.id == a.class_id).first()
        result.append({
            "member_name": member.full_name if member else "Unknown",
            "class_name": fitness_class.name if fitness_class else "Unknown",
            "checked_in_at": a.checked_in_at,
            "status": a.status
        })
    return result

@router.get("/members")
def get_members(db: Session = Depends(get_db)):
    members = db.query(Member).all()
    return [{"id": m.id, "full_name": m.full_name, "email": m.email, "phone": m.phone, "is_active": m.is_active, "created_at": m.created_at} for m in members]