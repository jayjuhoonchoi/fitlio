from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from app.database import engine
from app import models
from app.schema_migrate import ensure_columns
from app.routers import router as auth_router
from app.bookings import router as booking_router
from app.payments import router as payment_router
from app.attendance import router as attendance_router
from app.admin import router as admin_router
from app.me import router as me_router
from app.messages import router as message_router
from app.reminders import maybe_queue_membership_expiry_reminders
from app.notification_dispatch import maybe_process_pending_notifications
from app.centers import router as center_router
from app.member_experience import router as member_experience_router

models.Base.metadata.create_all(bind=engine)
ensure_columns(engine)

from app.seed import seed_database

seed_database()

TEMPLATES = Path(__file__).resolve().parent / "templates"


def _html(name: str) -> HTMLResponse:
    body = (TEMPLATES / name).read_text(encoding="utf-8")
    return HTMLResponse(
        content=body,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


app = FastAPI(
    title="Fitlio",
    description="Sports facility management platform",
    version="1.0.0",
)


@app.middleware("http")
async def fitlio_response_marker(request, call_next):
    """Helps verify traffic hits this app (see X-Fitlio-App on curl -I)."""
    maybe_queue_membership_expiry_reminders()
    maybe_process_pending_notifications()
    response = await call_next(request)
    response.headers["X-Fitlio-App"] = "portal-v2"
    return response


app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(payment_router)
app.include_router(attendance_router)
app.include_router(admin_router)
app.include_router(me_router)
app.include_router(message_router)
app.include_router(center_router)
app.include_router(member_experience_router)


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


@app.get("/app/tablet/{center_slug}", response_class=HTMLResponse)
def tablet_kiosk_page(center_slug: str):
    return _html("tablet_kiosk.html")


@app.get("/legacy")
def legacy_home():
    """Old single-page URL; send users to the current portal."""
    return RedirectResponse(url="/", status_code=302)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fitlio"}
