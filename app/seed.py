from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import models
from app.database import SessionLocal
import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def print_report(members: list, classes: list, memberships: list, db: Session):
    expiring_7 = db.query(models.Membership).filter(
        models.Membership.end_date <= datetime.now() + timedelta(days=7),
        models.Membership.end_date >= datetime.now(),
        models.Membership.status == "active"
    ).count()

    expiring_3 = db.query(models.Membership).filter(
        models.Membership.end_date <= datetime.now() + timedelta(days=3),
        models.Membership.end_date >= datetime.now(),
        models.Membership.status == "active"
    ).count()

    expiring_1 = db.query(models.Membership).filter(
        models.Membership.end_date <= datetime.now() + timedelta(days=1),
        models.Membership.end_date >= datetime.now(),
        models.Membership.status == "active"
    ).count()

    print("")
    print("╔════════════════════════════════════════════╗")
    print("║       🏋️  Fitlio Database Seeded            ║")
    print("╠════════════════════════════════════════════╣")
    print(f"║  👥 Members         │ {len(members)} created              ║")
    print(f"║  🥋 Classes         │ {len(classes)} created              ║")
    print(f"║  💳 Memberships     │ {len(memberships)} created              ║")
    print("╠════════════════════════════════════════════╣")
    print(f"║  ⚠️  Expiring in 7 days  │ {expiring_7} member(s)         ║")
    print(f"║  🔴 Expiring in 3 days  │ {expiring_3} member(s)         ║")
    print(f"║  🚨 Expiring tomorrow   │ {expiring_1} member(s)         ║")
    print("╚════════════════════════════════════════════╝")
    print("")


def seed_members(db: Session) -> list:
    members_data = [
        {"email": "jay.choi@fitlio.com", "full_name": "Jay Choi", "phone": "+82-10-1234-5678"},
        {"email": "minjun.kim@fitlio.com", "full_name": "Minjun Kim", "phone": "+82-10-2345-6789"},
        {"email": "soyeon.park@fitlio.com", "full_name": "Soyeon Park", "phone": "+82-10-3456-7890"},
        {"email": "hyunwoo.lee@fitlio.com", "full_name": "Hyunwoo Lee", "phone": "+82-10-4567-8901"},
        {"email": "jiyeon.choi@fitlio.com", "full_name": "Jiyeon Choi", "phone": "+82-10-5678-9012"},
    ]
    members = []
    for data in members_data:
        existing = db.query(models.Member).filter_by(email=data["email"]).first()
        if not existing:
            member = models.Member(
                email=data["email"],
                hashed_password=hash_password("fitlio1234!"),
                full_name=data["full_name"],
                phone=data["phone"],
                is_active=True,
                created_at=datetime.now() - timedelta(days=90)
            )
            db.add(member)
            members.append(member)
    db.commit()
    for m in members:
        db.refresh(m)
    return members


def seed_classes(db: Session) -> list:
    classes_data = [
        {"name": "BJJ Fundamentals", "schedule": datetime.now() + timedelta(days=1, hours=10), "capacity": 20},
        {"name": "Wrestling", "schedule": datetime.now() + timedelta(days=2, hours=10), "capacity": 15},
        {"name": "Advanced Grappling", "schedule": datetime.now() + timedelta(days=3, hours=10), "capacity": 10},
        {"name": "Open Mat", "schedule": datetime.now() + timedelta(days=4, hours=11), "capacity": 30},
        {"name": "Kids BJJ", "schedule": datetime.now() + timedelta(days=5, hours=16), "capacity": 12},
    ]
    classes = []
    for data in classes_data:
        existing = db.query(models.FitnessClass).filter_by(name=data["name"]).first()
        if not existing:
            fitness_class = models.FitnessClass(
                name=data["name"],
                instructor="Jay Choi",
                schedule=data["schedule"],
                capacity=data["capacity"]
            )
            db.add(fitness_class)
            classes.append(fitness_class)
    db.commit()
    return classes


def seed_memberships(db: Session, members: list) -> list:
    plans = [
        {"plan": "unlimited", "days_offset": 7},
        {"plan": "3x_week", "days_offset": 3},
        {"plan": "2x_week", "days_offset": 1},
        {"plan": "unlimited", "days_offset": 30},
        {"plan": "3x_week", "days_offset": 60},
    ]
    memberships = []
    for member, plan_data in zip(members, plans):
        existing = db.query(models.Membership).filter_by(member_id=member.id).first()
        if not existing:
            membership = models.Membership(
                member_id=member.id,
                plan=plan_data["plan"],
                status="active",
                start_date=datetime.now() - timedelta(days=90),
                end_date=datetime.now() + timedelta(days=plan_data["days_offset"])
            )
            db.add(membership)
            memberships.append(membership)
    db.commit()
    return memberships


def seed_database():
    db: Session = SessionLocal()
    try:
        print("🔍 Checking database seed status...")

        member_count = db.query(models.Member).count()
        if member_count >= 5:
            print(f"✅ Database already seeded ({member_count} members). Skipping.")
            return

        print("🌱 Seeding database...")

        members = seed_members(db)
        classes = seed_classes(db)
        memberships = seed_memberships(db, members)

        print_report(members, classes, memberships, db)

    except IntegrityError as e:
        print(f"❌ IntegrityError during seeding: {e}")
        db.rollback()
    except Exception as e:
        print(f"❌ Unexpected error during seeding: {e}")
        db.rollback()
    finally:
        db.close()