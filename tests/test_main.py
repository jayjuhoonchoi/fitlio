from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

with patch("app.database.engine") as mock_engine, \
     patch("app.models.Base.metadata.create_all"):
    from app.main import app

client = TestClient(app)

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