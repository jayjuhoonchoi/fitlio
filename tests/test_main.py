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


def test_luxury_tokens_css_cache_headers_and_conditional_get():
    first = client.get("/assets/luxury_tokens.css")
    assert first.status_code == 200
    assert "public, max-age=3600" in first.headers.get("Cache-Control", "")
    assert "stale-while-revalidate" in first.headers.get("Cache-Control", "")
    assert "ETag" in first.headers
    etag = first.headers["ETag"]

    second = client.get("/assets/luxury_tokens.css", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.text == ""
    assert second.headers.get("ETag") == etag


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


def test_admin_premium_overview_invalid_months(db_session):
    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get("/admin/reports/premium-overview?months=2")
    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Months must be between 3 and 24"


def test_admin_premium_overview_response_shape(db_session):
    now = datetime.utcnow()
    member = models.Member(
        email="premium.member@fitlio.com",
        hashed_password="x",
        full_name="Premium Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()

    membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        start_date=now - timedelta(days=15),
        end_date=now + timedelta(days=15),
        status="active",
    )
    db_session.add(membership)

    cls = models.FitnessClass(
        name="Premium HIIT",
        instructor="Coach Prime",
        schedule=now - timedelta(days=2),
        capacity=20,
        current_count=0,
    )
    db_session.add(cls)
    db_session.flush()

    db_session.add(models.Booking(member_id=member.id, class_id=cls.id, status="confirmed"))
    db_session.add(models.Attendance(member_id=member.id, class_id=cls.id, status="present"))
    db_session.add(
        models.Payment(
            member_id=member.id,
            membership_id=membership.id,
            amount=12000,
            status="completed",
            payment_method="card",
        )
    )
    db_session.commit()

    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get(
        "/admin/reports/premium-overview?months=6&risk_days=60&risk_threshold_pct=50"
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["months"] == 6
    assert "kpis" in payload
    assert "trends" in payload
    assert "at_risk_summary" in payload

    for key in ("mrr", "retention_proxy", "occupancy", "at_risk"):
        assert key in payload["kpis"]
    for key in ("mrr", "retention_proxy", "occupancy"):
        assert key in payload["trends"]
        assert isinstance(payload["trends"][key], list)
        assert len(payload["trends"][key]) == 6

    mrr_kpi = payload["kpis"]["mrr"]
    assert mrr_kpi["label"] == "MRR"
    for key in ("value", "value_cents", "delta_pct", "status"):
        assert key in mrr_kpi

    risk_summary = payload["at_risk_summary"]
    for key in (
        "count",
        "risk_window_days",
        "risk_threshold_pct",
        "share_of_active_members_pct",
        "top_members",
    ):
        assert key in risk_summary


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
        "risk_window_days",
        "risk_threshold_pct",
        "rationale",
    ):
        assert key in row


def test_admin_member_risk_threshold_behavior(db_session):
    low_member = models.Member(
        email="risk.threshold.low@fitlio.com",
        hashed_password="x",
        full_name="Risk Threshold Low",
        role="member",
    )
    high_member = models.Member(
        email="risk.threshold.high@fitlio.com",
        hashed_password="x",
        full_name="Risk Threshold High",
        role="member",
    )
    db_session.add(low_member)
    db_session.add(high_member)
    db_session.flush()

    scheduled_at = datetime.utcnow() - timedelta(days=1)
    classes = []
    for idx in range(4):
        klass = models.FitnessClass(
            name=f"Risk Threshold Class {idx}",
            instructor="Coach Risk",
            schedule=scheduled_at,
            capacity=20,
            current_count=0,
        )
        db_session.add(klass)
        classes.append(klass)
    db_session.flush()

    for klass in classes:
        db_session.add(
            models.Booking(member_id=low_member.id, class_id=klass.id, status="confirmed")
        )
        db_session.add(
            models.Booking(member_id=high_member.id, class_id=klass.id, status="confirmed")
        )
    db_session.flush()

    db_session.add(
        models.Attendance(member_id=low_member.id, class_id=classes[0].id, status="present")
    )
    for klass in classes[:3]:
        db_session.add(
            models.Attendance(member_id=high_member.id, class_id=klass.id, status="present")
        )
    db_session.commit()

    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get("/admin/reports/member-risk?days=30&threshold_pct=50")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    by_member = {row["member_id"]: row for row in rows}
    assert by_member[low_member.id]["attendance_rate"] == 25.0
    assert by_member[low_member.id]["at_risk"] is True
    assert by_member[high_member.id]["attendance_rate"] == 75.0
    assert by_member[high_member.id]["at_risk"] is False


def test_admin_members_include_retention_risk_shape(db_session):
    member = models.Member(
        email="risk.shape.member@fitlio.com",
        hashed_password="x",
        full_name="Risk Shape Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    klass = models.FitnessClass(
        name="Risk Shape Class",
        instructor="Coach Shape",
        schedule=datetime.utcnow() - timedelta(days=1),
        capacity=20,
        current_count=0,
    )
    db_session.add(klass)
    db_session.flush()
    db_session.add(models.Booking(member_id=member.id, class_id=klass.id, status="confirmed"))
    db_session.add(models.Attendance(member_id=member.id, class_id=klass.id, status="present"))
    db_session.commit()

    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get("/admin/members?risk_days=30&risk_threshold_pct=50")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 1
    target = next(row for row in rows if row["id"] == member.id)
    for key in ("at_risk", "attendance_rate", "risk_reason", "retention_risk"):
        assert key in target
    for key in (
        "at_risk",
        "attendance_rate",
        "attendance_count",
        "booked_count",
        "risk_window_days",
        "risk_threshold_pct",
        "rationale",
    ):
        assert key in target["retention_risk"]


def test_admin_member_risk_non_risk_member_case(db_session):
    member = models.Member(
        email="risk.non.member@fitlio.com",
        hashed_password="x",
        full_name="Risk Non Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()

    scheduled_at = datetime.utcnow() - timedelta(days=2)
    classes = []
    for idx in range(2):
        klass = models.FitnessClass(
            name=f"Risk Non Class {idx}",
            instructor="Coach Safe",
            schedule=scheduled_at,
            capacity=10,
            current_count=0,
        )
        db_session.add(klass)
        classes.append(klass)
    db_session.flush()

    for klass in classes:
        db_session.add(models.Booking(member_id=member.id, class_id=klass.id, status="confirmed"))
        db_session.add(
            models.Attendance(member_id=member.id, class_id=klass.id, status="present")
        )
    db_session.commit()

    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get("/admin/reports/member-risk?days=30&threshold_pct=50")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    row = next(item for item in rows if item["member_id"] == member.id)
    assert row["attendance_rate"] == 100.0
    assert row["at_risk"] is False


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


def test_dispatch_creates_delivery_attempt_log(db_session):
    member = models.Member(
        email="attempt.member@fitlio.com",
        hashed_password="x",
        full_name="Attempt Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    note = models.NotificationRequest(
        member_id=member.id,
        topic="attempt_topic",
        message="attempt message",
        channel="email",
        status="pending",
    )
    db_session.add(note)
    db_session.commit()

    process_pending_notifications(db_session, limit=10)
    rows = db_session.query(models.NotificationDeliveryAttempt).all()
    assert len(rows) == 1
    assert rows[0].notification_id == note.id
    assert rows[0].status == "sent"


def test_admin_notification_attempts_endpoint(db_session):
    admin = models.Member(
        email="admin.attempts@fitlio.com",
        hashed_password="x",
        full_name="Attempts Admin",
        role="admin",
    )
    member = models.Member(
        email="member.attempts@fitlio.com",
        hashed_password="x",
        full_name="Attempts Member",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    note = models.NotificationRequest(
        member_id=member.id,
        topic="attempts",
        message="attempts message",
        status="pending",
    )
    db_session.add(note)
    db_session.flush()
    db_session.add(
        models.NotificationDeliveryAttempt(
            notification_id=note.id,
            channel="email",
            status="failed",
            error_message="provider timeout",
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.get(f"/admin/notifications/{note.id}/attempts")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "failed"


def test_list_notifications_filter_by_status_and_channel(db_session):
    admin = models.Member(
        email="admin.filter@fitlio.com",
        hashed_password="x",
        full_name="Filter Admin",
        role="admin",
    )
    member = models.Member(
        email="member.filter@fitlio.com",
        hashed_password="x",
        full_name="Filter Member",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.NotificationRequest(
            member_id=member.id,
            topic="n1",
            message="pending email",
            channel="email",
            status="pending",
        )
    )
    db_session.add(
        models.NotificationRequest(
            member_id=member.id,
            topic="n2",
            message="failed sms",
            channel="sms",
            status="failed",
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.get("/admin/notifications?status=failed&channel=sms")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["channel"] == "sms"


def test_notifications_summary_counts(db_session):
    admin = models.Member(
        email="admin.summary@fitlio.com",
        hashed_password="x",
        full_name="Summary Admin",
        role="admin",
    )
    member = models.Member(
        email="member.summary@fitlio.com",
        hashed_password="x",
        full_name="Summary Member",
        role="member",
        phone="+82-10-0000-1111",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.NotificationRequest(
            member_id=member.id,
            topic="s1",
            message="p email",
            channel="email",
            status="pending",
            retry_count=1,
        )
    )
    db_session.add(
        models.NotificationRequest(
            member_id=member.id,
            topic="s2",
            message="ok sms",
            channel="sms",
            status="sent",
        )
    )
    db_session.add(
        models.NotificationRequest(
            member_id=member.id,
            topic="s3",
            message="bad inapp",
            channel="inapp",
            status="failed",
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.get("/admin/notifications/summary")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued"] >= 1
    assert payload["sent"] >= 1
    assert payload["failed"] >= 1
    assert payload["retrying"] >= 1
    assert payload["by_channel"]["email"] >= 1
    assert payload["by_channel"]["sms"] >= 1
    assert payload["by_channel"]["inapp"] >= 1


def test_member_purchase_starts_pending_and_returns_checkout(db_session):
    member = models.Member(
        email="member.purchase@fitlio.com",
        hashed_password="x",
        full_name="Purchase Member",
        role="member",
    )
    db_session.add(member)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(
        "/member/purchase",
        json={"plan": "monthly", "payment_method": "card"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["payment_status"] == "pending"
    assert payload["checkout_url"].startswith("https://pay.fitlio.local/checkout/")
    assert payload["external_ref"]
    assert "payment_metadata" in payload
    assert payload["payment_metadata"]["provider"] == "card_gateway_sim"
    assert payload["payment_metadata"]["provider_reference"] == payload["external_ref"]
    assert payload["payment_metadata"]["settlement_state"] == "awaiting_settlement"
    payment = db_session.query(models.Payment).filter(models.Payment.id == payload["payment_id"]).first()
    membership = db_session.query(models.Membership).filter(models.Membership.id == payload["membership_id"]).first()
    assert payment is not None
    assert membership is not None
    assert payment.status == "pending"
    assert membership.status == "pending"


def test_payment_webhook_duplicate_is_idempotent(db_session):
    member = models.Member(
        email="member.webhook@fitlio.com",
        hashed_password="x",
        full_name="Webhook Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        status="pending",
        end_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(membership)
    db_session.flush()
    payment = models.Payment(
        member_id=member.id,
        membership_id=membership.id,
        amount=5000,
        currency="aud",
        status="pending",
        source="online",
        payment_method="card",
        external_ref="card_20260101010101_abcdef12",
    )
    db_session.add(payment)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    body = {
        "provider": "card",
        "event_type": "payment.updated",
        "external_ref": payment.external_ref,
        "status": "completed",
        "payload": {"trace": "same"},
    }
    first = client.post("/member/payments/webhook", json=body)
    second = client.post("/member/payments/webhook", json=body)
    app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert first.json()["payment_metadata"]["settlement_state"] == "settled"
    assert second.json()["settlement_state"] == "settled"
    db_session.refresh(payment)
    db_session.refresh(membership)
    assert payment.status == "completed"
    assert membership.status == "active"
    events = db_session.query(models.PaymentWebhookEvent).filter(models.PaymentWebhookEvent.external_ref == payment.external_ref).all()
    assert len(events) == 1


def test_payment_webhook_failed_transitions_membership_to_failed(db_session):
    member = models.Member(
        email="member.webhook.failed@fitlio.com",
        hashed_password="x",
        full_name="Webhook Failed Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        status="pending",
        end_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(membership)
    db_session.flush()
    payment = models.Payment(
        member_id=member.id,
        membership_id=membership.id,
        amount=5000,
        currency="aud",
        status="pending",
        source="online",
        payment_method="card",
        external_ref="card_failed_20260101010101_abcd1234",
    )
    db_session.add(payment)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    body = {
        "provider": "card",
        "event_type": "payment.updated",
        "external_ref": payment.external_ref,
        "status": "failed",
        "payload": {"trace": "failed-state"},
    }
    res = client.post("/member/payments/webhook", json=body)
    app.dependency_overrides.clear()

    assert res.status_code == 200
    assert res.json()["processed"] is True
    assert res.json()["payment_metadata"]["provider"] == "card_gateway_sim"
    assert res.json()["payment_metadata"]["settlement_state"] == "settlement_failed"
    db_session.refresh(payment)
    db_session.refresh(membership)
    assert payment.status == "failed"
    assert membership.status == "failed"


def test_payment_webhook_rejects_invalid_secret_when_configured(db_session, monkeypatch):
    member = models.Member(
        email="member.webhook.secret@fitlio.com",
        hashed_password="x",
        full_name="Webhook Secret Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        status="pending",
        end_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(membership)
    db_session.flush()
    payment = models.Payment(
        member_id=member.id,
        membership_id=membership.id,
        amount=5000,
        currency="aud",
        status="pending",
        source="online",
        payment_method="card",
        external_ref="card_secret_check_20260101010101",
    )
    db_session.add(payment)
    db_session.commit()

    import app.member_experience as member_experience

    monkeypatch.setattr(member_experience, "PAYMENT_WEBHOOK_SECRET", "top-secret")
    app.dependency_overrides[get_db] = _override_db(db_session)
    body = {
        "provider": "card",
        "event_type": "payment.updated",
        "external_ref": payment.external_ref,
        "status": "completed",
        "payload": {"trace": "secret-check"},
    }
    res = client.post(
        "/member/payments/webhook",
        json=body,
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    app.dependency_overrides.clear()

    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid webhook secret"
    db_session.refresh(payment)
    assert payment.status == "pending"


def test_retry_after_failure_purchase_reuses_membership(db_session):
    member = models.Member(
        email="member.retry.purchase@fitlio.com",
        hashed_password="x",
        full_name="Retry Purchase Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    failed_membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        status="failed",
        end_date=datetime.utcnow() - timedelta(days=2),
    )
    db_session.add(failed_membership)
    db_session.flush()
    db_session.add(
        models.Payment(
            member_id=member.id,
            membership_id=failed_membership.id,
            amount=5000,
            currency="aud",
            status="failed",
            source="online",
            payment_method="card",
            external_ref="card_retry_old_ref",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(
        "/member/purchase",
        json={"plan": "monthly", "payment_method": "card"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["attempt_type"] == "retry"
    assert payload["membership_id"] == failed_membership.id
    assert payload["payment_status"] == "pending"
    assert payload["payment_lifecycle"] == "in_flight"
    assert payload["payment_metadata"]["provider"] == "card_gateway_sim"
    assert payload["payment_metadata"]["settlement_state"] == "awaiting_settlement"
    db_session.refresh(failed_membership)
    assert failed_membership.status == "pending"

    pending_payments = (
        db_session.query(models.Payment)
        .filter(
            models.Payment.membership_id == failed_membership.id,
            models.Payment.status == "pending",
        )
        .all()
    )
    assert len(pending_payments) == 1


@pytest.mark.parametrize(
    "method,provider,settlement_state",
    [
        ("paypal", "paypal", "awaiting_settlement"),
        ("naverpay", "naverpay", "awaiting_settlement"),
        ("kakaopay", "kakaopay", "awaiting_settlement"),
        ("payco", "payco", "awaiting_settlement"),
        ("bank_transfer", "bank_transfer", "awaiting_deposit"),
        ("card", "card_gateway_sim", "awaiting_settlement"),
    ],
)
def test_purchase_method_specific_metadata_contract(
    db_session, method, provider, settlement_state
):
    member = models.Member(
        email=f"purchase.meta.{method}@fitlio.com",
        hashed_password="x",
        full_name=f"Purchase Meta {method}",
        role="member",
    )
    db_session.add(member)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(
        "/member/purchase",
        json={"plan": "monthly", "payment_method": method},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["payment_method"] == method
    assert payload["payment_metadata"]["provider"] == provider
    assert payload["payment_metadata"]["provider_reference"] == payload["external_ref"]
    assert payload["payment_metadata"]["settlement_state"] == settlement_state
    assert "fee_hint_bps" in payload["payment_metadata"]
    assert "settlement_mode" in payload["payment_metadata"]


def test_webhook_bank_transfer_completed_returns_manual_settlement_state(db_session):
    member = models.Member(
        email="member.webhook.bank.completed@fitlio.com",
        hashed_password="x",
        full_name="Webhook Bank Completed",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        status="pending",
        end_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(membership)
    db_session.flush()
    payment = models.Payment(
        member_id=member.id,
        membership_id=membership.id,
        amount=5000,
        currency="aud",
        status="pending",
        source="online",
        payment_method="bank_transfer",
        external_ref="bank_transfer_20260101010101_abcdff11",
    )
    db_session.add(payment)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    body = {
        "provider": "bank_transfer",
        "payment_method": "bank_transfer",
        "event_type": "payment.updated",
        "external_ref": payment.external_ref,
        "status": "completed",
        "payload": {"trace": "bank-complete"},
    }
    res = client.post("/member/payments/webhook", json=body)
    app.dependency_overrides.clear()

    assert res.status_code == 200
    payload = res.json()
    assert payload["processed"] is True
    assert payload["payment_metadata"]["provider"] == "bank_transfer"
    assert payload["payment_metadata"]["settlement_state"] == "settled_manual"
    db_session.refresh(payment)
    db_session.refresh(membership)
    assert payment.status == "completed"
    assert membership.status == "active"


def test_admin_payments_list_includes_reconciliation_metadata_and_csv_export(db_session):
    admin = models.Member(
        email="admin.payments.meta@fitlio.com",
        hashed_password="x",
        full_name="Admin Payments Meta",
        role="admin",
    )
    member = models.Member(
        email="member.payments.meta@fitlio.com",
        hashed_password="x",
        full_name="Member Payments Meta",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        status="active",
        end_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(membership)
    db_session.flush()
    payment = models.Payment(
        member_id=member.id,
        membership_id=membership.id,
        amount=5000,
        currency="aud",
        status="completed",
        source="online",
        payment_method="paypal",
        external_ref="paypal_20260101010101_abc12121",
    )
    db_session.add(payment)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.get("/admin/payments")
    csv_response = client.get("/admin/payments?format=csv")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 1
    target = next(row for row in rows if row["id"] == payment.id)
    assert target["provider"] == "paypal"
    assert target["provider_reference"] == payment.external_ref
    assert target["settlement_state"] == "settled"
    assert target["fee_hint_bps"] > 0
    assert target["amount_cents"] == 5000

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    csv_body = csv_response.text
    assert "provider,external_ref,provider_reference,fee_hint_bps,settlement_state" in csv_body
    assert "paypal_20260101010101_abc12121" in csv_body


def test_member_home_expired_failed_payment_payload(db_session):
    member = models.Member(
        email="member.home.failed@fitlio.com",
        hashed_password="x",
        full_name="Expired Failed Member",
        role="member",
    )
    db_session.add(member)
    db_session.flush()
    membership = models.Membership(
        member_id=member.id,
        plan="monthly",
        status="failed",
        end_date=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add(membership)
    db_session.flush()
    db_session.add(
        models.Payment(
            member_id=member.id,
            membership_id=membership.id,
            amount=5000,
            currency="aud",
            status="failed",
            source="online",
            payment_method="card",
            external_ref="card_failed_member_home",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.get("/member/home")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    m = payload["membership"]
    assert m["is_expired"] is True
    assert m["can_pay_now"] is True
    assert m["renewal_prompt"] == "retry_payment"
    assert m["latest_payment_status"] == "failed"
    assert m["payment_state"]["status"] == "failed"
    assert m["payment_state"]["severity"] == "error"
    assert m["payment_state"]["retry_ready"] is True


def test_moderation_report_status_update(db_session):
    admin = models.Member(
        email="admin.moderation@fitlio.com",
        hashed_password="x",
        full_name="Mod Admin",
        role="admin",
    )
    member = models.Member(
        email="member.moderation@fitlio.com",
        hashed_password="x",
        full_name="Mod Member",
        role="member",
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.flush()
    report = models.ContentReport(
        reporter_member_id=member.id,
        target_type="community_post",
        target_id=123,
        reason="abuse",
        status="open",
    )
    db_session.add(report)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": admin.id, "role": "admin"}
    response = client.post(
        "/member/moderation/reports/status",
        json={"report_id": report.id, "status": "resolved"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    db_session.refresh(report)
    assert report.status == "resolved"


def test_community_post_media_validation_accept_and_reject(db_session):
    member = models.Member(
        email="community.media.member@fitlio.com",
        hashed_password="x",
        full_name="Community Media Member",
        role="member",
    )
    db_session.add(member)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}

    ok = client.post(
        "/member/community/posts",
        json={
            "content": "",
            "media_url": "https://cdn.fitlio.local/community/photo.jpg",
            "media_type": "image",
        },
    )
    assert ok.status_code == 200
    row = db_session.query(models.CommunityPost).filter(models.CommunityPost.id == ok.json()["id"]).first()
    assert row is not None
    assert row.media_url == "https://cdn.fitlio.local/community/photo.jpg"
    assert row.media_type == "image"

    bad_scheme = client.post(
        "/member/community/posts",
        json={
            "content": "bad",
            "media_url": "javascript:alert(1)",
            "media_type": "image",
        },
    )
    assert bad_scheme.status_code == 400
    assert "http or https" in bad_scheme.json()["detail"]

    bad_type = client.post(
        "/member/community/posts",
        json={
            "content": "bad",
            "media_url": "https://cdn.fitlio.local/community/photo.jpg",
            "media_type": "video",
        },
    )
    assert bad_type.status_code == 400
    assert "does not match media type" in bad_type.json()["detail"]
    app.dependency_overrides.clear()


def test_community_feed_excludes_hidden_post_and_hidden_comments(db_session):
    member = models.Member(
        email="community.feed.member@fitlio.com",
        hashed_password="x",
        full_name="Community Feed Member",
        role="member",
    )
    author = models.Member(
        email="community.feed.author@fitlio.com",
        hashed_password="x",
        full_name="Community Feed Author",
        role="member",
    )
    db_session.add(member)
    db_session.add(author)
    db_session.flush()
    visible_post = models.CommunityPost(
        author_member_id=author.id,
        content="visible post",
        is_hidden=False,
    )
    hidden_post = models.CommunityPost(
        author_member_id=author.id,
        content="hidden post",
        is_hidden=True,
    )
    db_session.add(visible_post)
    db_session.add(hidden_post)
    db_session.flush()
    db_session.add(
        models.CommunityReaction(
            post_id=visible_post.id,
            member_id=author.id,
            type="comment",
            content="visible comment",
            is_hidden=False,
        )
    )
    db_session.add(
        models.CommunityReaction(
            post_id=visible_post.id,
            member_id=author.id,
            type="comment",
            content="hidden comment",
            is_hidden=True,
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.get("/member/community/posts")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["content"] == "visible post"
    assert all(c["content"] != "hidden comment" for c in rows[0]["comments"])


def test_report_and_moderation_state_transitions(db_session):
    admin = models.Member(
        email="community.mod.admin@fitlio.com",
        hashed_password="x",
        full_name="Community Mod Admin",
        role="admin",
    )
    reporter = models.Member(
        email="community.mod.reporter@fitlio.com",
        hashed_password="x",
        full_name="Community Reporter",
        role="member",
    )
    author = models.Member(
        email="community.mod.author@fitlio.com",
        hashed_password="x",
        full_name="Community Author",
        role="member",
    )
    db_session.add(admin)
    db_session.add(reporter)
    db_session.add(author)
    db_session.flush()
    post = models.CommunityPost(author_member_id=author.id, content="moderate me")
    db_session.add(post)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": reporter.id, "role": "member"}
    report_res = client.post(
        "/member/community/reports",
        json={"target_type": "community_post", "target_id": post.id, "reason": "abuse"},
    )
    assert report_res.status_code == 200
    report_id = report_res.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: {"id": admin.id, "role": "admin"}
    hide_res = client.post(
        "/member/moderation/hide",
        json={"target_type": "community_post", "target_id": post.id, "hide": True, "reason": "reported"},
    )
    assert hide_res.status_code == 200
    assert hide_res.json()["hidden"] is True

    resolve_res = client.post(
        "/member/moderation/reports/status",
        json={"report_id": report_id, "status": "resolved"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"

    unhide_res = client.post(
        "/member/moderation/hide",
        json={"target_type": "community_post", "target_id": post.id, "hide": False},
    )
    assert unhide_res.status_code == 200
    assert unhide_res.json()["hidden"] is False

    reject_res = client.post(
        "/member/moderation/reports/status",
        json={"report_id": report_id, "status": "rejected"},
    )
    app.dependency_overrides.clear()

    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    db_post = db_session.query(models.CommunityPost).filter(models.CommunityPost.id == post.id).first()
    db_report = db_session.query(models.ContentReport).filter(models.ContentReport.id == report_id).first()
    assert db_post is not None
    assert db_report is not None
    assert db_post.is_hidden is False
    assert db_report.status == "rejected"


def test_center_member_cannot_interact_with_other_center_post(db_session):
    center_a = models.Center(name="Center A", slug="center-a", is_active=True)
    center_b = models.Center(name="Center B", slug="center-b", is_active=True)
    actor = models.Member(
        email="center.scope.actor@fitlio.com",
        hashed_password="x",
        full_name="Center Scope Actor",
        role="member",
    )
    author = models.Member(
        email="center.scope.author@fitlio.com",
        hashed_password="x",
        full_name="Center Scope Author",
        role="member",
    )
    db_session.add(center_a)
    db_session.add(center_b)
    db_session.add(actor)
    db_session.add(author)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center_a.id,
            member_id=actor.id,
            role="member",
            status="active",
        )
    )
    db_session.add(
        models.CenterMembership(
            center_id=center_b.id,
            member_id=author.id,
            role="member",
            status="active",
        )
    )
    post = models.CommunityPost(
        author_member_id=author.id,
        center_id=center_b.id,
        content="B-only post",
        is_hidden=False,
    )
    db_session.add(post)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": actor.id, "role": "member"}
    like_res = client.post(f"/member/community/posts/{post.id}/like")
    report_res = client.post(
        "/member/community/reports",
        json={"target_type": "community_post", "target_id": post.id, "reason": "abuse"},
    )
    app.dependency_overrides.clear()

    assert like_res.status_code == 403
    assert report_res.status_code == 403


def test_member_cannot_post_to_unjoined_center(db_session):
    center = models.Center(name="Locked Center", slug="locked-center", is_active=True)
    member = models.Member(
        email="center.post.denied@fitlio.com",
        hashed_password="x",
        full_name="Center Post Denied",
        role="member",
    )
    db_session.add(center)
    db_session.add(member)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(
        "/member/community/posts",
        json={"center_id": center.id, "content": "hello locked center"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Not allowed to post to this center"


def test_staff_cannot_moderate_other_center_content(db_session):
    center_a = models.Center(name="Mod Center A", slug="mod-center-a", is_active=True)
    center_b = models.Center(name="Mod Center B", slug="mod-center-b", is_active=True)
    staff = models.Member(
        email="moderation.staff@fitlio.com",
        hashed_password="x",
        full_name="Moderation Staff",
        role="member",
    )
    author = models.Member(
        email="moderation.author@fitlio.com",
        hashed_password="x",
        full_name="Moderation Author",
        role="member",
    )
    reporter = models.Member(
        email="moderation.reporter@fitlio.com",
        hashed_password="x",
        full_name="Moderation Reporter",
        role="member",
    )
    db_session.add(center_a)
    db_session.add(center_b)
    db_session.add(staff)
    db_session.add(author)
    db_session.add(reporter)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center_a.id,
            member_id=staff.id,
            role="staff",
            status="active",
        )
    )
    db_session.add(
        models.CenterMembership(
            center_id=center_b.id,
            member_id=author.id,
            role="member",
            status="active",
        )
    )
    post = models.CommunityPost(
        author_member_id=author.id,
        center_id=center_b.id,
        content="center-b content",
        is_hidden=False,
    )
    db_session.add(post)
    db_session.flush()
    report = models.ContentReport(
        reporter_member_id=reporter.id,
        target_type="community_post",
        target_id=post.id,
        reason="abuse",
        status="open",
    )
    db_session.add(report)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": staff.id, "role": "member"}
    hide_res = client.post(
        "/member/moderation/hide",
        json={"target_type": "community_post", "target_id": post.id, "hide": True},
    )
    status_res = client.post(
        "/member/moderation/reports/status",
        json={"report_id": report.id, "status": "resolved"},
    )
    reports_res = client.get("/member/moderation/reports")
    app.dependency_overrides.clear()

    assert hide_res.status_code == 403
    assert status_res.status_code == 403
    assert reports_res.status_code == 200
    assert all(item["id"] != report.id for item in reports_res.json())


def test_admin_class_create_supports_center_and_level(db_session):
    admin = models.Member(
        email="admin.class@fitlio.com",
        hashed_password="x",
        full_name="Class Admin",
        role="admin",
    )
    instructor = models.InstructorProfile(
        display_name="Coach Class",
        hourly_rate_cents=100000,
        pay_per_class_cents=150000,
    )
    db_session.add(admin)
    db_session.add(instructor)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    payload = {
        "name": "Center Elite HIIT",
        "instructor": "Coach Class",
        "schedule": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "capacity": 18,
        "center_id": 7,
        "level_required": "elite",
    }
    response = client.post("/admin/classes", json=payload)
    app.dependency_overrides.clear()

    assert response.status_code == 201
    class_id = response.json()["id"]
    row = db_session.query(models.FitnessClass).filter(models.FitnessClass.id == class_id).first()
    assert row is not None
    assert row.center_id == 7
    assert row.level_required == "elite"


def test_admin_class_update_supports_center_and_level(db_session):
    admin = models.Member(
        email="admin.class.update@fitlio.com",
        hashed_password="x",
        full_name="Class Update Admin",
        role="admin",
    )
    instructor = models.InstructorProfile(
        display_name="Coach Update",
        hourly_rate_cents=100000,
        pay_per_class_cents=150000,
    )
    klass = models.FitnessClass(
        name="Starter Flow",
        instructor="Coach Update",
        schedule=datetime.utcnow() + timedelta(days=2),
        capacity=20,
        center_id=1,
        level_required="starter",
    )
    db_session.add(admin)
    db_session.add(instructor)
    db_session.add(klass)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    payload = {
        "name": "Core Flow",
        "instructor": "Coach Update",
        "schedule": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        "capacity": 22,
        "center_id": 9,
        "level_required": "core",
    }
    response = client.put(f"/admin/classes/{klass.id}", json=payload)
    app.dependency_overrides.clear()

    assert response.status_code == 200
    db_session.refresh(klass)
    assert klass.center_id == 9
    assert klass.level_required == "core"


def test_tablet_check_in_includes_days_left(db_session):
    center = models.Center(
        name="Tablet Center",
        slug="tablet-center",
    )
    member = models.Member(
        email="tablet.member@fitlio.com",
        hashed_password="x",
        full_name="Tablet Member",
        phone="+82-10-9999-1234",
        role="member",
        is_active=True,
    )
    db_session.add(center)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center.id,
            member_id=member.id,
            role="member",
            status="active",
        )
    )
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="monthly",
            status="active",
            monthly_limit=12,
            end_date=datetime.utcnow() + timedelta(days=9),
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in",
        json={"center_slug": "tablet-center", "phone_last4": "1234"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "days_left" in payload
    assert payload["days_left"] is not None
    assert payload["days_left"] >= 0


def test_tablet_check_in_contract_additive_fields(db_session):
    center = models.Center(
        name="Tablet Contract Center",
        slug="tablet-contract-center",
    )
    member = models.Member(
        email="tablet.contract@fitlio.com",
        hashed_password="x",
        full_name="Tablet Contract Member",
        phone="+82-10-2222-8888",
        role="member",
        is_active=True,
    )
    db_session.add(center)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center.id,
            member_id=member.id,
            role="member",
            status="active",
        )
    )
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="monthly",
            status="active",
            monthly_limit=5,
            end_date=datetime.utcnow() + timedelta(days=14),
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in",
        json={"center_slug": "tablet-contract-center", "phone_last4": "8888"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["status_label"] == "success"
    assert payload["severity"] == "success"
    assert payload["result_code"] == "CHECK_IN_OK"
    assert payload["ui_state"] == "success"
    assert payload["can_retry"] is False
    assert isinstance(payload["reset_after_ms"], int)
    assert payload["reset_after_ms"] >= 900
    assert payload["usage_limit"] == 5
    assert payload["usage_used_this_month"] >= 1
    assert isinstance(payload["remaining_usage_count"], int)
    assert payload["remaining_usage_count"] >= 0
    assert "remaining_usage" in payload
    assert "days_left" in payload


def test_tablet_check_in_duplicate_returns_contract_headers(db_session):
    center = models.Center(
        name="Tablet Duplicate Center",
        slug="tablet-duplicate-center",
    )
    member = models.Member(
        email="tablet.duplicate@fitlio.com",
        hashed_password="x",
        full_name="Tablet Duplicate Member",
        phone="+82-10-3030-4444",
        role="member",
        is_active=True,
    )
    db_session.add(center)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center.id,
            member_id=member.id,
            role="member",
            status="active",
        )
    )
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="monthly",
            status="active",
            monthly_limit=12,
            end_date=datetime.utcnow() + timedelta(days=7),
        )
    )
    db_session.add(
        models.Attendance(
            member_id=member.id,
            class_id=0,
            status="present",
            checked_in_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in",
        json={"center_slug": "tablet-duplicate-center", "phone_last4": "4444"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Already checked in today"
    assert response.headers["X-Tablet-Result-Code"] == "ALREADY_CHECKED_IN_TODAY"
    assert response.headers["X-Tablet-Status-Label"] == "error"
    assert response.headers["X-Tablet-UI-State"] == "error"
    assert response.headers["X-Tablet-Severity"] == "error"
    assert response.headers["X-Tablet-Can-Retry"] == "false"


def test_tablet_check_in_member_not_found_has_retry_header(db_session):
    center = models.Center(
        name="Tablet Retry Center",
        slug="tablet-retry-center",
    )
    db_session.add(center)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in",
        json={"center_slug": "tablet-retry-center", "phone_last4": "1234"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Member not found"
    assert response.headers["X-Tablet-Result-Code"] == "MEMBER_NOT_FOUND"
    assert response.headers["X-Tablet-Severity"] == "error"
    assert response.headers["X-Tablet-Can-Retry"] == "true"


def test_payments_membership_state_includes_severity(db_session):
    member = models.Member(
        email="payments.severity@fitlio.com",
        hashed_password="x",
        full_name="Payments Severity",
        role="member",
    )
    db_session.add(member)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(
        f"/payments/membership?member_id={member.id}",
        json={"plan": "monthly", "payment_method": "card"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["payment"]["state"]["status"] == "completed"
    assert payload["payment"]["state"]["severity"] == "success"


def test_tablet_check_in_rejects_nondigit_phone_last4(db_session):
    center = models.Center(
        name="Tablet Validation Center",
        slug="tablet-validation-center",
    )
    db_session.add(center)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in",
        json={"center_slug": "tablet-validation-center", "phone_last4": "12x4"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "phone_last4 must contain only digits"
    assert response.headers["X-Tablet-Result-Code"] == "INVALID_PHONE_LAST4"


def test_tablet_check_in_rejects_ambiguous_member_match(db_session):
    center = models.Center(
        name="Tablet Ambiguous Center",
        slug="tablet-ambiguous-center",
    )
    member_one = models.Member(
        email="tablet.ambiguous.one@fitlio.com",
        hashed_password="x",
        full_name="Tablet Ambiguous One",
        phone="+82-10-1111-1234",
        role="member",
        is_active=True,
    )
    member_two = models.Member(
        email="tablet.ambiguous.two@fitlio.com",
        hashed_password="x",
        full_name="Tablet Ambiguous Two",
        phone="+82-10-2222-1234",
        role="member",
        is_active=True,
    )
    db_session.add(center)
    db_session.add(member_one)
    db_session.add(member_two)
    db_session.flush()
    for member in (member_one, member_two):
        db_session.add(
            models.CenterMembership(
                center_id=center.id,
                member_id=member.id,
                role="member",
                status="active",
            )
        )
        db_session.add(
            models.Membership(
                member_id=member.id,
                plan="monthly",
                status="active",
                monthly_limit=12,
                end_date=datetime.utcnow() + timedelta(days=10),
            )
        )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in",
        json={"center_slug": "tablet-ambiguous-center", "phone_last4": "1234"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "Multiple members match phone suffix"
    assert response.headers["X-Tablet-Result-Code"] == "AMBIGUOUS_MEMBER_MATCH"


def test_center_discover_response_shape(db_session):
    center_a = models.Center(name="Gangnam Prime", slug="gangnam-prime", is_active=True)
    center_b = models.Center(name="Mapo Move", slug="mapo-move", is_active=True)
    member = models.Member(
        email="discover.member@fitlio.com",
        hashed_password="x",
        full_name="Discover Member",
        role="member",
    )
    db_session.add(center_a)
    db_session.add(center_b)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center_a.id,
            member_id=member.id,
            role="member",
            status="pending",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.get("/centers/discover?query=mapo")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "total" in payload
    assert payload["total"] == 1
    row = payload["items"][0]
    for key in (
        "center_id",
        "name",
        "slug",
        "membership_status",
        "membership_role",
        "can_request",
    ):
        assert key in row
    assert row["slug"] == "mapo-move"
    assert row["membership_status"] == "none"
    assert row["can_request"] is True


def test_center_join_request_success(db_session):
    center = models.Center(name="Join Center", slug="join-center", is_active=True)
    member = models.Member(
        email="join.success@fitlio.com",
        hashed_password="x",
        full_name="Join Success",
        role="member",
    )
    db_session.add(center)
    db_session.add(member)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post("/centers/join-request", json={"center_slug": "join-center"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["center_id"] == center.id
    row = (
        db_session.query(models.CenterMembership)
        .filter(
            models.CenterMembership.center_id == center.id,
            models.CenterMembership.member_id == member.id,
        )
        .first()
    )
    assert row is not None
    assert row.status == "pending"


def test_center_join_request_duplicate_pending_protection(db_session):
    center = models.Center(name="Dup Center", slug="dup-center", is_active=True)
    member = models.Member(
        email="join.dup@fitlio.com",
        hashed_password="x",
        full_name="Join Dup",
        role="member",
    )
    db_session.add(center)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center.id,
            member_id=member.id,
            role="member",
            status="pending",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post("/centers/join-request", json={"center_slug": "dup-center"})
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "Join request already pending"


def test_center_membership_status_visibility(db_session):
    center_pending = models.Center(name="Pending Hub", slug="pending-hub", is_active=True)
    center_active = models.Center(name="Active Hub", slug="active-hub", is_active=True)
    member = models.Member(
        email="status.member@fitlio.com",
        hashed_password="x",
        full_name="Status Member",
        role="member",
    )
    db_session.add(center_pending)
    db_session.add(center_active)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center_pending.id,
            member_id=member.id,
            role="member",
            status="pending",
        )
    )
    db_session.add(
        models.CenterMembership(
            center_id=center_active.id,
            member_id=member.id,
            role="member",
            status="active",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.get("/centers/my-memberships")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    by_slug = {row["center_slug"]: row for row in rows}
    assert by_slug["pending-hub"]["status"] == "pending"
    assert by_slug["active-hub"]["status"] == "active"
    for key in ("center_id", "center_name", "center_slug", "role", "status", "updated_at"):
        assert key in by_slug["active-hub"]


def test_center_landing_admin_create_and_publish_flow(db_session):
    admin = models.Member(
        email="landing.admin@fitlio.com",
        hashed_password="x",
        full_name="Landing Admin",
        role="admin",
        is_active=True,
    )
    center = models.Center(name="Landing Hub", slug="landing-hub", is_active=True)
    db_session.add(admin)
    db_session.add(center)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center.id,
            member_id=admin.id,
            role="admin",
            status="active",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": admin.id, "role": "admin"}
    payload = {
        "publish": True,
        "blocks": [
            {"type": "hero", "headline": "Train Better", "subheadline": "Move with us"},
            {"type": "about", "title": "About", "body": "Premium coaching daily"},
            {"type": "schedule", "title": "Schedule", "body": "Weekdays 06:00-22:00"},
            {
                "type": "cta",
                "title": "Join now",
                "button_text": "Book trial",
                "button_url": "https://fitlio.example.com/trial",
            },
        ],
    }
    update = client.post(f"/centers/{center.id}/landing", json=payload)
    get_admin = client.get(f"/centers/{center.id}/landing")
    public_get = client.get(f"/centers/public/{center.slug}/landing")
    page_get = client.get(f"/center/{center.slug}")
    app.dependency_overrides.clear()

    assert update.status_code == 200
    update_payload = update.json()
    assert update_payload["landing_is_published"] is True
    assert len(update_payload["landing_content"]["blocks"]) == 4

    assert get_admin.status_code == 200
    admin_payload = get_admin.json()
    assert admin_payload["center_id"] == center.id
    assert admin_payload["center_slug"] == center.slug
    assert admin_payload["landing_is_published"] is True

    assert public_get.status_code == 200
    public_payload = public_get.json()
    assert public_payload["center_slug"] == center.slug
    assert public_payload["branding"]["tablet_accent_color"] == "#2f855a"
    assert public_payload["landing_content"]["blocks"][0]["type"] == "hero"

    assert page_get.status_code == 200
    assert "Fitlio Center" in page_get.text


def test_center_landing_validation_and_unpublished_access(db_session):
    admin = models.Member(
        email="landing.validation.admin@fitlio.com",
        hashed_password="x",
        full_name="Landing Validation Admin",
        role="admin",
        is_active=True,
    )
    center = models.Center(name="Landing Draft", slug="landing-draft", is_active=True)
    db_session.add(admin)
    db_session.add(center)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center.id,
            member_id=admin.id,
            role="admin",
            status="active",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": admin.id, "role": "admin"}
    bad_payload = {
        "publish": False,
        "blocks": [
            {
                "type": "cta",
                "title": "Book",
                "button_text": "Open",
                "button_url": "javascript:alert(1)",
            }
        ],
    }
    bad_update = client.post(f"/centers/{center.id}/landing", json=bad_payload)
    good_update = client.post(
        f"/centers/{center.id}/landing",
        json={
            "publish": False,
            "blocks": [{"type": "hero", "headline": "Draft", "subheadline": "Coming soon"}],
        },
    )
    public_get = client.get(f"/centers/public/{center.slug}/landing")
    app.dependency_overrides.clear()

    assert bad_update.status_code == 400
    assert "http:// or https://" in bad_update.json()["detail"]
    assert good_update.status_code == 200
    assert good_update.json()["landing_is_published"] is False
    assert public_get.status_code == 404
    assert public_get.json()["detail"] == "Landing page not published"


def test_quick_reserve_success_path(db_session):
    member = models.Member(
        email="quick.reserve.success@fitlio.com",
        hashed_password="x",
        full_name="Quick Reserve Success",
        role="member",
        is_active=True,
    )
    klass = models.FitnessClass(
        name="Quick Reserve Yoga",
        instructor="Coach Quick",
        schedule=datetime.utcnow() + timedelta(hours=3),
        capacity=2,
        current_count=0,
    )
    db_session.add(member)
    db_session.add(klass)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(f"/member/classes/{klass.id}/quick-reserve")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "confirmed"
    assert payload["message"] == "Class reserved successfully."
    booking = (
        db_session.query(models.Booking)
        .filter(models.Booking.class_id == klass.id, models.Booking.member_id == member.id)
        .first()
    )
    db_session.refresh(klass)
    assert booking is not None
    assert booking.status == "confirmed"
    assert klass.current_count == 1


def test_quick_reserve_full_class_waitlist_path(db_session):
    member = models.Member(
        email="quick.reserve.waitlist@fitlio.com",
        hashed_password="x",
        full_name="Quick Reserve Waitlist",
        role="member",
        is_active=True,
    )
    klass = models.FitnessClass(
        name="Quick Reserve Full",
        instructor="Coach Full",
        schedule=datetime.utcnow() + timedelta(hours=4),
        capacity=1,
        current_count=1,
    )
    db_session.add(member)
    db_session.add(klass)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(f"/member/classes/{klass.id}/quick-reserve")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "waitlisted"
    assert payload["waitlisted"] is True
    assert payload["waitlist_position"] == 1
    assert "waitlist" in payload["message"].lower()
    booking = (
        db_session.query(models.Booking)
        .filter(models.Booking.class_id == klass.id, models.Booking.member_id == member.id)
        .first()
    )
    db_session.refresh(klass)
    assert booking is not None
    assert booking.status == "waiting"
    assert klass.current_count == 1


def test_quick_reserve_duplicate_request_protection(db_session):
    member = models.Member(
        email="quick.reserve.duplicate@fitlio.com",
        hashed_password="x",
        full_name="Quick Reserve Duplicate",
        role="member",
        is_active=True,
    )
    klass = models.FitnessClass(
        name="Quick Reserve Duplicate Class",
        instructor="Coach Duplicate",
        schedule=datetime.utcnow() + timedelta(hours=5),
        capacity=3,
        current_count=0,
    )
    db_session.add(member)
    db_session.add(klass)
    db_session.flush()
    db_session.add(
        models.Booking(
            member_id=member.id,
            class_id=klass.id,
            status="confirmed",
        )
    )
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.post(f"/member/classes/{klass.id}/quick-reserve")
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "You already reserved this class."


def test_cancel_confirmed_booking_promotes_waitlist_member(db_session):
    canceller = models.Member(
        email="cancel.promote.canceller@fitlio.com",
        hashed_password="x",
        full_name="Cancel Promote Canceller",
        role="member",
        is_active=True,
    )
    waitlisted = models.Member(
        email="cancel.promote.waitlisted@fitlio.com",
        hashed_password="x",
        full_name="Cancel Promote Waitlisted",
        role="member",
        is_active=True,
    )
    klass = models.FitnessClass(
        name="Cancel Promote Class",
        instructor="Coach Promote",
        schedule=datetime.utcnow() + timedelta(hours=6),
        capacity=1,
        current_count=1,
    )
    db_session.add(canceller)
    db_session.add(waitlisted)
    db_session.add(klass)
    db_session.flush()
    confirmed = models.Booking(
        member_id=canceller.id,
        class_id=klass.id,
        status="confirmed",
    )
    waiting = models.Booking(
        member_id=waitlisted.id,
        class_id=klass.id,
        status="waiting",
    )
    db_session.add(confirmed)
    db_session.add(waiting)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": canceller.id,
        "role": "member",
    }
    response = client.request(
        "DELETE",
        f"/classes/{klass.id}/cancel",
        params={"member_id": canceller.id},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Booking cancelled successfully"
    assert payload["waitlist_promotion"]["promoted"] is True
    assert payload["waitlist_promotion"]["member_id"] == waitlisted.id
    assert payload["waitlist_promotion"]["notification_enqueued"] is True

    db_session.refresh(confirmed)
    db_session.refresh(waiting)
    db_session.refresh(klass)
    assert confirmed.status == "cancelled"
    assert waiting.status == "confirmed"
    assert klass.current_count == 1
    note = (
        db_session.query(models.NotificationRequest)
        .filter(
            models.NotificationRequest.member_id == waitlisted.id,
            models.NotificationRequest.topic == "waitlist_promoted",
        )
        .first()
    )
    assert note is not None
    assert note.status == "pending"


def test_capacity_increase_promotes_waitlist_in_fifo_order(db_session):
    first = models.Member(
        email="capacity.fifo.first@fitlio.com",
        hashed_password="x",
        full_name="Capacity FIFO First",
        role="member",
        is_active=True,
    )
    second = models.Member(
        email="capacity.fifo.second@fitlio.com",
        hashed_password="x",
        full_name="Capacity FIFO Second",
        role="member",
        is_active=True,
    )
    klass = models.FitnessClass(
        name="Capacity FIFO Class",
        instructor="Coach FIFO",
        schedule=datetime.utcnow() + timedelta(hours=7),
        capacity=1,
        current_count=1,
    )
    admin = models.Member(
        email="capacity.fifo.admin@fitlio.com",
        hashed_password="x",
        full_name="Capacity FIFO Admin",
        role="admin",
        is_active=True,
    )
    db_session.add(first)
    db_session.add(second)
    db_session.add(klass)
    db_session.add(admin)
    db_session.flush()
    first_waiting = models.Booking(
        member_id=first.id,
        class_id=klass.id,
        status="waiting",
        created_at=datetime.utcnow() - timedelta(minutes=2),
    )
    second_waiting = models.Booking(
        member_id=second.id,
        class_id=klass.id,
        status="waiting",
        created_at=datetime.utcnow() - timedelta(minutes=1),
    )
    db_session.add(first_waiting)
    db_session.add(second_waiting)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.put(
        f"/admin/classes/{klass.id}",
        json={"capacity": 3},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    db_session.refresh(first_waiting)
    db_session.refresh(second_waiting)
    db_session.refresh(klass)
    assert first_waiting.status == "confirmed"
    assert second_waiting.status == "confirmed"
    assert klass.current_count == 3
    notes = (
        db_session.query(models.NotificationRequest)
        .filter(models.NotificationRequest.topic == "waitlist_promoted")
        .order_by(models.NotificationRequest.created_at.asc())
        .all()
    )
    assert len(notes) == 2
    assert notes[0].member_id == first.id
    assert notes[1].member_id == second.id


def test_cancel_confirmed_booking_with_no_waitlist_has_no_promotion(db_session):
    member = models.Member(
        email="cancel.no.waitlist@fitlio.com",
        hashed_password="x",
        full_name="Cancel No Waitlist",
        role="member",
        is_active=True,
    )
    klass = models.FitnessClass(
        name="Cancel No Waitlist Class",
        instructor="Coach No Waitlist",
        schedule=datetime.utcnow() + timedelta(hours=8),
        capacity=2,
        current_count=1,
    )
    db_session.add(member)
    db_session.add(klass)
    db_session.flush()
    booking = models.Booking(member_id=member.id, class_id=klass.id, status="confirmed")
    db_session.add(booking)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.request(
        "DELETE",
        f"/classes/{klass.id}/cancel",
        params={"member_id": member.id},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["waitlist_promotion"]["promoted"] is False
    assert payload["waitlist_promotion"]["booking_id"] is None
    assert payload["waitlist_promotion"]["member_id"] is None
    assert payload["waitlist_promotion"]["notification_enqueued"] is False
    db_session.refresh(booking)
    db_session.refresh(klass)
    assert booking.status == "cancelled"
    assert klass.current_count == 0
    notes = (
        db_session.query(models.NotificationRequest)
        .filter(models.NotificationRequest.topic == "waitlist_promoted")
        .all()
    )
    assert len(notes) == 0


def test_admin_weekly_performance_requires_auth():
    response = client.get("/admin/reports/weekly-performance")
    assert response.status_code == 401


def test_admin_weekly_performance_response_shape(db_session):
    admin = models.Member(
        email="admin.weekly.shape@fitlio.com",
        hashed_password="x",
        full_name="Weekly Shape Admin",
        role="admin",
    )
    member = models.Member(
        email="member.weekly.shape@fitlio.com",
        hashed_password="x",
        full_name="Weekly Shape Member",
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
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow() + timedelta(days=20),
        )
    )
    db_session.flush()
    membership = db_session.query(models.Membership).filter(models.Membership.member_id == member.id).first()
    klass = models.FitnessClass(
        name="Weekly Shape Class",
        instructor="Coach Weekly",
        schedule=datetime.utcnow() - timedelta(days=1),
        capacity=20,
        current_count=0,
    )
    db_session.add(klass)
    db_session.flush()
    db_session.add(
        models.Booking(
            member_id=member.id,
            class_id=klass.id,
            status="confirmed",
        )
    )
    db_session.add(
        models.Payment(
            member_id=member.id,
            membership_id=membership.id,
            amount=12345,
            currency="aud",
            status="completed",
            payment_method="card",
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.get("/admin/reports/weekly-performance")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    for key in ("title", "generated_at", "period", "scope", "metrics", "highlights", "html"):
        assert key in payload
    assert "start" in payload["period"]
    assert "end" in payload["period"]
    assert "center_id" in payload["scope"]
    assert "label" in payload["scope"]
    for section in ("revenue", "member_growth", "occupancy", "at_risk"):
        assert section in payload["metrics"]


def test_admin_weekly_performance_html_has_key_sections(db_session):
    admin = models.Member(
        email="admin.weekly.html@fitlio.com",
        hashed_password="x",
        full_name="Weekly Html Admin",
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    response = client.get("/admin/reports/weekly-performance")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    html = response.json()["html"]
    assert "Revenue Summary" in html
    assert "Member Growth and Retention" in html
    assert "Class Occupancy Highlights" in html
    assert "At-Risk Members" in html


def test_admin_class_roster_lists_confirmed_bookings(db_session):
    admin = models.Member(
        email="admin.roster@fitlio.com",
        hashed_password="x",
        full_name="Roster Admin",
        role="admin",
    )
    member = models.Member(
        email="member.roster@fitlio.com",
        hashed_password="x",
        full_name="Roster Member",
        role="member",
        phone="+1-555-000-1234",
    )
    instructor = models.InstructorProfile(
        display_name="Coach Roster",
        hourly_rate_cents=1000,
        pay_per_class_cents=2000,
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.add(instructor)
    db_session.flush()
    klass = models.FitnessClass(
        name="HIIT Roster",
        instructor="Coach Roster",
        schedule=datetime.utcnow() + timedelta(hours=2),
        capacity=12,
    )
    db_session.add(klass)
    db_session.flush()
    db_session.add(
        models.Booking(member_id=member.id, class_id=klass.id, status="confirmed")
    )
    db_session.commit()

    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.get(f"/admin/classes/{klass.id}/roster")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["class"]["name"] == "HIIT Roster"
    assert len(payload["roster"]) == 1
    row = payload["roster"][0]
    assert row["member_id"] == member.id
    assert row["checked_in_today"] is False
    assert row["phone_last4"] == "1234"


def test_admin_one_tap_attendance_success_and_duplicate(db_session):
    admin = models.Member(
        email="admin.attend@fitlio.com",
        hashed_password="x",
        full_name="Attend Admin",
        role="admin",
    )
    member = models.Member(
        email="member.attend@fitlio.com",
        hashed_password="x",
        full_name="Attend Member",
        role="member",
        phone="+1-555-000-9876",
        is_active=True,
    )
    instructor = models.InstructorProfile(
        display_name="Coach Attend",
        hourly_rate_cents=1000,
        pay_per_class_cents=2000,
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.add(instructor)
    db_session.flush()
    klass = models.FitnessClass(
        name="Flow Attend",
        instructor="Coach Attend",
        schedule=datetime.utcnow() + timedelta(hours=3),
        capacity=10,
    )
    db_session.add(klass)
    db_session.flush()
    db_session.add(
        models.Booking(member_id=member.id, class_id=klass.id, status="confirmed")
    )
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="monthly",
            status="active",
            monthly_limit=20,
            end_date=datetime.utcnow() + timedelta(days=30),
        )
    )
    db_session.commit()

    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    app.dependency_overrides[get_db] = _override_db(db_session)
    first = client.post(f"/admin/classes/{klass.id}/attendance/{member.id}")
    second = client.post(f"/admin/classes/{klass.id}/attendance/{member.id}")
    app.dependency_overrides.clear()

    assert first.status_code == 200
    body = first.json()
    assert body["member_name"] == "Attend Member"
    assert "celebration" in body
    assert second.status_code == 400


def test_admin_one_tap_attendance_requires_booking(db_session):
    admin = models.Member(
        email="admin.nobook@fitlio.com",
        hashed_password="x",
        full_name="No Book Admin",
        role="admin",
    )
    member = models.Member(
        email="member.nobook@fitlio.com",
        hashed_password="x",
        full_name="No Book Member",
        role="member",
        is_active=True,
    )
    instructor = models.InstructorProfile(
        display_name="Coach NoBook",
        hourly_rate_cents=1000,
        pay_per_class_cents=2000,
    )
    db_session.add(admin)
    db_session.add(member)
    db_session.add(instructor)
    db_session.flush()
    klass = models.FitnessClass(
        name="Solo NoBook",
        instructor="Coach NoBook",
        schedule=datetime.utcnow() + timedelta(hours=1),
        capacity=8,
    )
    db_session.add(klass)
    db_session.commit()

    app.dependency_overrides[require_admin] = lambda: {"id": admin.id, "role": "admin"}
    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(f"/admin/classes/{klass.id}/attendance/{member.id}")
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "booking" in response.json()["detail"].lower()


def test_member_checkin_qr_returns_short_lived_token(db_session):
    member = models.Member(
        email="member.qr@fitlio.com",
        hashed_password="x",
        full_name="QR Member",
        role="member",
        is_active=True,
    )
    db_session.add(member)
    db_session.commit()

    from app.deps import get_current_user

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: {"id": member.id, "role": "member"}
    response = client.get("/member/checkin-qr")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "token" in payload
    assert len(payload["token"]) > 40
    assert payload.get("expires_in_seconds", 0) > 0


def test_tablet_check_in_qr_success(db_session):
    from app.auth import create_checkin_qr_token

    center = models.Center(name="QR Gym", slug="qr-gym")
    member = models.Member(
        email="tablet.qr.member@fitlio.com",
        hashed_password="x",
        full_name="Tablet QR Member",
        role="member",
        is_active=True,
        phone="+82-10-1111-2222",
    )
    db_session.add(center)
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.CenterMembership(
            center_id=center.id,
            member_id=member.id,
            role="member",
            status="active",
        )
    )
    db_session.add(
        models.Membership(
            member_id=member.id,
            plan="monthly",
            status="active",
            monthly_limit=12,
            end_date=datetime.utcnow() + timedelta(days=14),
        )
    )
    db_session.commit()
    token, _ = create_checkin_qr_token(member.id)

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in-qr",
        json={"center_slug": "qr-gym", "token": token},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body.get("ok") is True
    assert body.get("result_code") == "CHECK_IN_OK"


def test_tablet_check_in_qr_rejects_bad_token(db_session):
    center = models.Center(name="Bad QR", slug="bad-qr")
    db_session.add(center)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    response = client.post(
        "/centers/tablet/check-in-qr",
        json={"center_slug": "bad-qr", "token": "not.a.valid.jwt.token.here"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.headers.get("X-Tablet-Result-Code") == "INVALID_CHECKIN_QR"