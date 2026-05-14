from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date
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
    birth_date = Column(Date, nullable=True)
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
    center_id = Column(Integer, nullable=True, index=True)
    level_required = Column(String(32), nullable=False, default="starter")
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
    center_id = Column(Integer, nullable=True)
    source = Column(String(32), nullable=False, default="online")  # online | onsite_manual
    payment_method = Column(String(32), nullable=False, default="card")
    memo = Column(String(512), nullable=True)
    recorded_by_member_id = Column(Integer, nullable=True)
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
    avatar_url = Column(String(512), nullable=True)
    bio = Column(String(1000), nullable=True)
    specialties = Column(String(500), nullable=True)
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


class Center(Base):
    __tablename__ = "centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    tablet_welcome_text = Column(String(256), nullable=False, default="Welcome to Fitlio.")
    tablet_theme = Column(String(64), nullable=False, default="premium-green")
    tablet_logo_url = Column(String(512), nullable=True)
    created_by_member_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CenterMembership(Base):
    __tablename__ = "center_memberships"

    id = Column(Integer, primary_key=True, index=True)
    center_id = Column(Integer, nullable=False, index=True)
    member_id = Column(Integer, nullable=False, index=True)
    role = Column(String(32), nullable=False, default="member")  # admin | staff | member
    status = Column(
        String(32), nullable=False, default="pending"
    )  # active | pending | invited | rejected
    invited_by_member_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, nullable=False, index=True)
    recipient_id = Column(Integer, nullable=False, index=True)
    content = Column(String(2000), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, nullable=False, index=True)
    channel = Column(String(16), nullable=False)
    status = Column(String(32), nullable=False)  # sent | failed
    provider_message_id = Column(String(128), nullable=True)
    error_message = Column(String(512), nullable=True)
    attempted_at = Column(DateTime, default=datetime.utcnow, index=True)


class InstructorReaction(Base):
    __tablename__ = "instructor_reactions"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(Integer, nullable=False, index=True)
    member_id = Column(Integer, nullable=False, index=True)
    type = Column(String(16), nullable=False, default="like")  # like | comment
    content = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=True, index=True)
    center_id = Column(Integer, nullable=True, index=True)
    content = Column(String(2000), nullable=False)
    is_anonymous = Column(Boolean, nullable=False, default=True)
    status = Column(String(32), nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    author_member_id = Column(Integer, nullable=False, index=True)
    center_id = Column(Integer, nullable=True, index=True)
    content = Column(String(2000), nullable=True)
    media_url = Column(String(1024), nullable=True)
    media_type = Column(String(16), nullable=False, default="image")  # image | video
    created_at = Column(DateTime, default=datetime.utcnow)


class CommunityReaction(Base):
    __tablename__ = "community_reactions"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    member_id = Column(Integer, nullable=False, index=True)
    type = Column(String(16), nullable=False, default="like")  # like | comment
    content = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)