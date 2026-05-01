from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String)
    is_active = Column(Boolean, default=True)
    language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

class FitnessClass(Base):
    __tablename__ = "fitness_classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    instructor = Column(String, nullable=False)
    schedule = Column(DateTime, nullable=False)
    capacity = Column(Integer, default=20)
    current_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False)
    class_id = Column(Integer, nullable=False)
    status = Column(String, default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False)
    plan = Column(String, nullable=False)  # unlimited, weekly_2, weekly_3, weekly_5
    monthly_limit = Column(Integer, nullable=True)  # None = 무제한, 8/12/20 = 제한
    status = Column(String, default="active")  # active, expired, cancelled
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False)
    membership_id = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)  # cents (e.g. 5000 = $50.00)
    currency = Column(String, default="aud")
    status = Column(String, default="pending")  # pending, completed, failed
    stripe_payment_intent_id = Column(String)  # Stripe 연동용
    created_at = Column(DateTime, default=datetime.utcnow)

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False)
    class_id = Column(Integer, nullable=False)
    checked_in_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="present")  # present, late, absent