from fastapi.testclient import TestClient
from unittest.mock import patch

import pytest
from datetime import datetime
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

with patch("app.database.engine") as mock_engine, \
     patch("app.models.Base.metadata.create_all"), \
     patch("app.seed.seed_database"), \
     patch("app.main.maybe_queue_membership_expiry_reminders"):
    from app.main import app
    from app.database import get_db
    from app.deps import require_admin
    from app import models
    from app.reminders import queue_membership_expiry_reminders
    from app.notification_dispatch import process_pending_notifications

client = TestClient(app)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _override_admin():
    return {"id": 1, "role": "admin"}


def _override_db(db):
    def _inner():
        try:
            yield db
        finally:
            pass

    return _inner

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root():
    response = client.get("/")
    assert response.status_code == 200


def test_member_login_page():
    response = client.get("/login/member")
    assert response.status_code == 200
    assert "Fitlio" in response.text


def test_admin_login_page():
    response = client.get("/admin-login")
    assert response.status_code == 200
    assert "Admin" in response.text


def test_admin_occupancy_trend_requires_auth():
    response = client.get("/admin/reports/occupancy-trend?months=6")
    assert response.status_code == 401


def test_admin_occupancy_trend_invalid_months(db_session):
    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get("/admin/reports/occupancy-trend?months=0")
    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Months must be between 1 and 24"


def test_admin_occupancy_trend_response_shape(db_session):
    member = models.Member(
        email="shape.member@fitlio.com",
        hashed_password="x",
        full_name="Shape Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()

    cls = models.FitnessClass(
        name="HIIT 45",
        instructor="Coach Kim",
        schedule=datetime.utcnow(),
        capacity=20,
        current_count=0,
    )
    db_session.add(cls)
    db_session.flush()
    db_session.add(
        models.Booking(member_id=member.id, class_id=cls.id, status="confirmed")
    )
    db_session.commit()

    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get("/admin/reports/occupancy-trend?months=1")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["months"] == 1
    assert isinstance(payload["points"], list)
    assert len(payload["points"]) == 1
    point = payload["points"][0]
    for key in (
        "label",
        "classes_count",
        "capacity_total",
        "booked_total",
        "fill_rate",
    ):
        assert key in point


def test_admin_member_risk_response_shape(db_session):
    member = models.Member(
        email="risk.member@fitlio.com",
        hashed_password="x",
        full_name="Risk Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()

    cls = models.FitnessClass(
        name="Pilates",
        instructor="Coach Lee",
        schedule=datetime.utcnow(),
        capacity=10,
        current_count=1,
    )
    db_session.add(cls)
    db_session.flush()
    db_session.add(models.Attendance(member_id=member.id, class_id=cls.id, status="present"))
    db_session.commit()

    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get("/admin/reports/member-risk?days=30")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    row = rows[0]
    for key in (
        "member_id",
        "full_name",
        "booked_count",
        "attendance_count",
        "attendance_rate",
        "at_risk",
    ):
        assert key in row


def test_messages_send_and_thread_flow(db_session):
    admin = models.Member(
        email="admin-msg@fitlio.com",
        hashed_password="x",
        full_name="Admin Msg",
        role="admin",
    )
    member = models.Member(
        email="member-msg@fitlio.com",
        hashed_password="x",
        full_name="Member Msg",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    from app.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    send = client.post(
        "/messages",
        json={"recipient_id": admin.id, "content": "hello admin"},
    )
    assert send.status_code == 201

    app.dependency_overrides[get_current_user] = lambda: {"id": admin.id, "role": "admin"}
    thread = client.get(f"/messages/thread/{member.id}")
    assert thread.status_code == 200
    rows = thread.json()
    assert len(rows) == 1
    assert rows[0]["content"] == "hello admin"

    members = client.get("/messages/admin/members")
    assert members.status_code == 200
    assert any(r["id"] == member.id for r in members.json())

    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    contact = client.get("/messages/admin-contact")
    assert contact.status_code == 200
    assert contact.json()["id"] == admin.id
    app.dependency_overrides.clear()


def test_queue_membership_expiry_reminders_creates_day_3_and_day_1(db_session):
    member = models.Member(
        email="reminder.member@fitlio.com",
        hashed_password="x",
        full_name="Reminder Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()

    now = datetime.utcnow()
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="monthly",
            status="active",
            start_date=now - timedelta(days=27),
            end_date=now + timedelta(days=3),
        )
    )
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="yearly",
            status="active",
            start_date=now - timedelta(days=364),
            end_date=now + timedelta(days=1),
        )
    )
    db_session.commit()

    result = queue_membership_expiry_reminders(db_session, reference_time=now)
    assert result["created"] == 2
    rows = db_session.query(models.NotificationRequest).all()
    assert len(rows) == 2
    assert any(r.topic == "membership_expiry_d3" for r in rows)
    assert any(r.topic == "membership_expiry_d1" for r in rows)
    assert all("Dear Reminder Member" in r.message for r in rows)


def test_run_membership_reminders_admin_endpoint(db_session):
    admin = models.Member(
        email="admin.reminder@fitlio.com",
        hashed_password="x",
        full_name="Reminder Admin",
        role="admin",
    )
    member = models.Member(
        email="member.reminder@fitlio.com",
        hashed_password="x",
        full_name="Reminder User",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="monthly",
            status="active",
            start_date=datetime.utcnow() - timedelta(days=27),
            end_date=datetime.utcnow() + timedelta(days=3),
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.post("/admin/notifications/membership-reminders/run")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["created"] >= 1


def test_process_pending_notifications_marks_sent(db_session):
    member = models.Member(
        email="dispatch.member@fitlio.com",
        hashed_password="x",
        full_name="Dispatch Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.NotificationRequest(
            member_id=member.id,
            topic="membership_expiry_d1",
            message="test dispatch",
            channel="email",
            status="pending",
        )
    )
    db_session.commit()

    result = process_pending_notifications(db_session, limit=20)
    assert result["processed"] == 1
    assert result["sent"] == 1
    row = db_session.query(models.NotificationRequest).first()
    assert row.status == "sent"
    assert row.sent_at is not None


def test_run_notification_dispatch_admin_endpoint(db_session):
    admin = models.Member(
        email="admin.dispatch@fitlio.com",
        hashed_password="x",
        full_name="Admin Dispatch",
        role="admin",
    )
    member = models.Member(
        email="member.dispatch@fitlio.com",
        hashed_password="x",
        full_name="Member Dispatch",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.NotificationRequest(
            member_id=member.id,
            topic="membership_expiry_d3",
            message="dispatch me",
            channel="email",
            status="pending",
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.post("/admin/notifications/dispatch/run")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "processed"
    assert payload["processed"] >= 1


def test_process_pending_notifications_retries_then_fails(db_session):
    member = models.Member(
        email="",
        hashed_password="x",
        full_name="No Contact Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    row = models.NotificationRequest(
        member_id=member.id,
        topic="membership_expiry_d1",
        message="cannot deliver",
        channel="sms",
        status="pending",
        retry_count=0,
        max_retries=2,
    )
    db_session.add(row)
    db_session.commit()

    first = process_pending_notifications(db_session, limit=10)
    assert first["queued_retry"] == 1
    db_session.refresh(row)
    assert row.status == "pending"
    assert row.retry_count == 1
    row.next_attempt_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    second = process_pending_notifications(db_session, limit=10)
    assert second["failed"] == 1
    db_session.refresh(row)
    assert row.status == "failed"
    assert row.retry_count == 2
    assert "phone number missing" in (row.last_error or "")


def test_retry_notification_endpoint_moves_failed_to_pending(db_session):
    admin = models.Member(
        email="admin.retry@fitlio.com",
        hashed_password="x",
        full_name="Retry Admin",
        role="admin",
    )
    member = models.Member(
        email="member.retry@fitlio.com",
        hashed_password="x",
        full_name="Retry Member",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    note = models.NotificationRequest(
        member_id=member.id,
        topic="membership_expiry_d3",
        message="retry test",
        status="failed",
        last_error="temporary error",
        retry_count=2,
    )
    db_session.add(note)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.post(f"/admin/notifications/{note.id}/retry")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    db_session.refresh(note)
    assert note.status == "pending"
    assert note.last_error is None


def test_process_pending_notifications_inapp_channel_sends(db_session):
    member = models.Member(
        email="inapp.member@fitlio.com",
        hashed_password="x",
        full_name="Inapp Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    note = models.NotificationRequest(
        member_id=member.id,
        topic="inapp_notice",
        message="inapp hello",
        channel="inapp",
        status="pending",
    )
    db_session.add(note)
    db_session.commit()

    result = process_pending_notifications(db_session, limit=10)
    assert result["sent"] == 1
    db_session.refresh(note)
    assert note.status == "sent"