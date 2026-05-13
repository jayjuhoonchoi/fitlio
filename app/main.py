from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.database import engine
from app import models
from app.schema_migrate import ensure_columns
from app.routers import router as auth_router
from app.bookings import router as booking_router
from app.payments import router as payment_router
from app.attendance import router as attendance_router
from app.admin import router as admin_router
from app.me import router as me_router

models.Base.metadata.create_all(bind=engine)
ensure_columns(engine)

from app.seed import seed_database

seed_database()

TEMPLATES = Path(__file__).resolve().parent / "templates"


def _html(name: str) -> HTMLResponse:
    return HTMLResponse((TEMPLATES / name).read_text(encoding="utf-8"))


app = FastAPI(
    title="Fitlio",
    description="Sports facility management platform",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(payment_router)
app.include_router(attendance_router)
app.include_router(admin_router)
app.include_router(me_router)


@app.get("/", response_class=HTMLResponse)
def portal():
    return _html("portal.html")


@app.get("/login", response_class=HTMLResponse)
@app.get("/login/member", response_class=HTMLResponse)
def login_member_page():
    return _html("login_member.html")


@app.get("/admin-login", response_class=HTMLResponse)
def login_admin_page():
    return _html("login_admin.html")


@app.get("/app/member", response_class=HTMLResponse)
def member_app_page():
    return _html("member_app.html")


@app.get("/app/admin", response_class=HTMLResponse)
def admin_app_page():
    return _html("admin_app.html")


@app.get("/legacy", response_class=HTMLResponse)
def legacy_home():
    """Previous single-page home (optional)."""
    return _html("index.html")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fitlio"}
