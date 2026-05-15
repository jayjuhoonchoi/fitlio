from email.utils import formatdate
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

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
_HTML_CACHE = {
    path.name: path.read_text(encoding="utf-8")
    for path in TEMPLATES.glob("*.html")
}
_LUXURY_TOKENS_PATH = TEMPLATES / "assets" / "luxury_tokens.css"
_LUXURY_TOKENS_BYTES = _LUXURY_TOKENS_PATH.read_bytes()
_LUXURY_TOKENS_ETAG = f"\"{sha256(_LUXURY_TOKENS_BYTES).hexdigest()}\""
_LUXURY_TOKENS_LAST_MODIFIED = formatdate(
    _LUXURY_TOKENS_PATH.stat().st_mtime, usegmt=True
)


def _html(name: str) -> HTMLResponse:
    body = _HTML_CACHE.get(name)
    if body is None:
        body = (TEMPLATES / name).read_text(encoding="utf-8")
        _HTML_CACHE[name] = body
    return HTMLResponse(
        content=body,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


def _css_asset(name: str, request: Request) -> Response:
    if name != "luxury_tokens.css":
        body = (TEMPLATES / "assets" / name).read_text(encoding="utf-8")
        return Response(
            content=body,
            media_type="text/css; charset=utf-8",
            headers={"Cache-Control": "public, max-age=300"},
        )

    headers = {
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        "ETag": _LUXURY_TOKENS_ETAG,
        "Last-Modified": _LUXURY_TOKENS_LAST_MODIFIED,
    }
    if request.headers.get("if-none-match") == _LUXURY_TOKENS_ETAG:
        return Response(status_code=304, headers=headers)
    return Response(
        content=_LUXURY_TOKENS_BYTES,
        media_type="text/css; charset=utf-8",
        headers=headers,
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


@app.get("/center/{center_slug}", response_class=HTMLResponse)
def center_landing_page(center_slug: str):
    return _html("center_landing.html")


@app.get("/assets/luxury_tokens.css")
def luxury_tokens_css(request: Request):
    return _css_asset("luxury_tokens.css", request)


@app.get("/legacy")
def legacy_home():
    """Old single-page URL; send users to the current portal."""
    return RedirectResponse(url="/", status_code=302)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fitlio"}
