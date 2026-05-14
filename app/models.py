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
    member_no = Column(String, unique=True, index=True, nullable=True)
    member_level = Column(String(32), nullable=False, default="starter")
    is_active = Column(Boolean, default=True)
    language = Column(String, default="en")
    role = Column(String(32), nullable=False, default="member")  # member | admin
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


class InstructorProfile(Base):
    """Payroll: match display_name to FitnessClass.instructor string."""

    __tablename__ = "instructor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, unique=True, nullable=False, index=True)
    hourly_rate_cents = Column(Integer, nullable=False, default=50_000)  # KRW-style cents unit
    pay_per_class_cents = Column(Integer, nullable=False, default=80_000)  # flat per scheduled class
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NotificationRequest(Base):
    __tablename__ = "notification_requests"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=True)
    topic = Column(String(64), nullable=False)
    message = Column(String(512), nullable=False)
    channel = Column(String(16), nullable=False, default="email")  # email | sms | inapp
    status = Column(String(32), nullable=False, default="pending")  # pending | sent | failed
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    next_attempt_at = Column(DateTime, nullable=True)
    last_error = Column(String(512), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, nullable=False, index=True)
    recipient_id = Column(Integer, nullable=False, index=True)
    content = Column(String(2000), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)