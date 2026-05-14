from fastapi.testclient import TestClient
from unittest.mock import patch

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

with patch("app.database.engine") as mock_engine, \
     patch("app.models.Base.metadata.create_all"), \
     patch("app.seed.seed_database"):
    from app.main import app
    from app.database import get_db
    from app.deps import require_admin
    from app import models

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