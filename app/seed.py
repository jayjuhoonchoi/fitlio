from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models
from app.database import SessionLocal


def seed_database():
    db: Session = SessionLocal()
    try:
        # 이미 데이터 있으면 스킵
        if db.query(models.Member).first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding database...")

        # 테스트 회원 3명
        members = [
            models.Member(
                email="jay@fitlio.com",
                hashed_password="hashed_test",
                full_name="Jay Choi",
                phone="+821012345678",
                is_active=True
            ),
            models.Member(
                email="alice@fitlio.com",
                hashed_password="hashed_test",
                full_name="Alice Kim",
                phone="+821087654321",
                is_active=True
            ),
            models.Member(
                email="bob@fitlio.com",
                hashed_password="hashed_test",
                full_name="Bob Lee",
                phone="+821099998888",
                is_active=True
            ),
        ]
        db.add_all(members)
        db.commit()
        for m in members:
            db.refresh(m)

        # 수업 5개
        classes = [
            models.FitnessClass(
                name="BJJ Fundamentals",
                instructor="Jay Choi",
                day_of_week="Monday",
                start_time="10:00",
                end_time="11:30",
                capacity=20
            ),
            models.FitnessClass(
                name="Wrestling",
                instructor="Jay Choi",
                day_of_week="Wednesday",
                start_time="10:00",
                end_time="11:30",
                capacity=15
            ),
            models.FitnessClass(
                name="Advanced Grappling",
                instructor="Jay Choi",
                day_of_week="Friday",
                start_time="10:00",
                end_time="11:30",
                capacity=10
            ),
            models.FitnessClass(
                name="Open Mat",
                instructor="Jay Choi",
                day_of_week="Saturday",
                start_time="11:00",
                end_time="13:00",
                capacity=30
            ),
            models.FitnessClass(
                name="Kids BJJ",
                instructor="Jay Choi",
                day_of_week="Tuesday",
                start_time="16:00",
                end_time="17:00",
                capacity=12
            ),
        ]
        db.add_all(classes)
        db.commit()

        # 멤버십 (Lambda 테스트용 - 7일 후 만료)
        memberships = [
            models.Membership(
                member_id=members[0].id,
                plan="unlimited",
                status="active",
                start_date=datetime.now() - timedelta(days=83),
                end_date=datetime.now