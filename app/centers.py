from datetime import date, datetime
import json
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import decode_checkin_qr_token
from app.database import get_db
from app.deps import get_current_user
from app.models import (
    Attendance,
    Center,
    CenterMembership,
    Member,
    Membership,
    Payment,
)

router = APIRouter(prefix="/centers", tags=["centers"])


def _assert_center_admin(db: Session, center_id: int, member_id: int) -> CenterMembership:
    row = (
        db.query(CenterMembership)
        .filter(
            CenterMembership.center_id == center_id,
            CenterMembership.member_id == member_id,
            CenterMembership.status == "active",
            CenterMembership.role == "admin",
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=403, detail="Center admin access required")
    return row


def _calculate_age(birth_date: date | None) -> int | None:
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


class CenterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=2, max_length=128)


class GrantAdminBody(BaseModel):
    center_id: int
    member_email: str


class JoinByEmailBody(BaseModel):
    center_slug: str
    member_email: str


class JoinRequestBody(BaseModel):
    center_slug: str


class CenterDiscoverItem(BaseModel):
    center_id: int
    name: str
    slug: str
    membership_status: str
    membership_role: str | None = None
    can_request: bool


class ApproveJoinBody(BaseModel):
    center_id: int
    member_id: int
    approve: bool = True


class TabletThemeBody(BaseModel):
    tablet_welcome_text: str | None = Field(default=None, max_length=256)
    tablet_theme: str | None = Field(default=None, max_length=64)
    tablet_logo_url: str | None = Field(default=None, max_length=512)
    tablet_accent_color: str | None = Field(default=None, max_length=32)
    tablet_background_url: str | None = Field(default=None, max_length=1024)


ALLOWED_LANDING_BLOCK_TYPES = {"hero", "about", "schedule", "cta"}
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
DEFAULT_LANDING_BLOCKS = [
    {"type": "hero", "headline": "", "subheadline": ""},
    {"type": "about", "title": "", "body": ""},
    {"type": "schedule", "title": "", "body": ""},
    {"type": "cta", "title": "", "button_text": "", "button_url": ""},
]


class OnsitePaymentBody(BaseModel):
    center_id: int
    member_id: int
    amount: int = Field(..., ge=1)
    currency: str = "aud"
    memo: str | None = Field(default=None, max_length=512)


class TabletCheckinBody(BaseModel):
    center_slug: str
    phone_last4: str = Field(..., min_length=4, max_length=4)


class LandingBlockBody(BaseModel):
    type: str = Field(..., pattern="^(hero|about|schedule|cta)$")
    headline: str | None = Field(default=None, max_length=120)
    subheadline: str | None = Field(default=None, max_length=240)
    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, max_length=1200)
    button_text: str | None = Field(default=None, max_length=80)
    button_url: str | None = Field(default=None, max_length=1024)


class LandingContentBody(BaseModel):
    blocks: list[LandingBlockBody] = Field(default_factory=list, max_length=20)
    publish: bool | None = None


def _clean_text(value: str | None, max_len: int) -> str:
    if not value:
        return ""
    cleaned = value.strip()
    return cleaned[:max_len]


def _clean_optional_url(value: str | None, *, max_len: int) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if len(candidate) > max_len:
        raise HTTPException(status_code=400, detail=f"URL must be <= {max_len} characters")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="URL host is required")
    return candidate


def _default_landing_payload() -> dict:
    return {"blocks": [dict(block) for block in DEFAULT_LANDING_BLOCKS]}


def _load_landing_payload(center: Center) -> dict:
    raw = (getattr(center, "landing_content_json", "") or "").strip()
    if not raw:
        return _default_landing_payload()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _default_landing_payload()
    if not isinstance(parsed, dict):
        return _default_landing_payload()
    blocks = parsed.get("blocks")
    if not isinstance(blocks, list):
        return _default_landing_payload()
    return {"blocks": blocks}


def _sanitize_landing_blocks(blocks: list[LandingBlockBody]) -> list[dict]:
    if not blocks:
        raise HTTPException(status_code=400, detail="At least one landing block is required")
    if len(blocks) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 blocks supported")
    seen_types = set()
    sanitized: list[dict] = []
    for block in blocks:
        block_type = block.type.strip().lower()
        if block_type not in ALLOWED_LANDING_BLOCK_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported block type: {block_type}")
        if block_type in seen_types:
            raise HTTPException(status_code=400, detail=f"Duplicate block type: {block_type}")
        seen_types.add(block_type)
        if block_type == "hero":
            sanitized.append(
                {
                    "type": "hero",
                    "headline": _clean_text(block.headline, 120),
                    "subheadline": _clean_text(block.subheadline, 240),
                }
            )
        elif block_type == "about":
            sanitized.append(
                {
                    "type": "about",
                    "title": _clean_text(block.title, 120),
                    "body": _clean_text(block.body, 1200),
                }
            )
        elif block_type == "schedule":
            sanitized.append(
                {
                    "type": "schedule",
                    "title": _clean_text(block.title, 120),
                    "body": _clean_text(block.body, 1200),
                }
            )
        else:
            sanitized.append(
                {
                    "type": "cta",
                    "title": _clean_text(block.title, 120),
                    "button_text": _clean_text(block.button_text, 80),
                    "button_url": _clean_optional_url(block.button_url, max_len=1024),
                }
            )
    return sanitized


def _tablet_checkin_error(
    *,
    http_status: int,
    detail: str,
    result_code: str,
    can_retry: bool,
):
    raise HTTPException(
        status_code=http_status,
        detail=detail,
        headers={
            "X-Tablet-Result-Code": result_code,
            "X-Tablet-Status-Label": "error",
            "X-Tablet-UI-State": "error",
            "X-Tablet-Severity": "error",
            "X-Tablet-Can-Retry": "true" if can_retry else "false",
        },
    )


def _tablet_complete_daily_checkin(db: Session, center: Center, member: Member) -> dict:
    """Shared finalize path for tablet PIN and QR check-in (same membership rules)."""
    membership = (
        db.query(Membership)
        .filter(Membership.member_id == member.id, Membership.status == "active")
        .order_by(Membership.end_date.desc())
        .first()
    )
    if not membership:
        _tablet_checkin_error(
            http_status=400,
            detail="No active membership",
            result_code="NO_ACTIVE_MEMBERSHIP",
            can_retry=False,
        )
    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    exists = (
        db.query(Attendance)
        .filter(Attendance.member_id == member.id, Attendance.checked_in_at >= day_start)
        .first()
    )
    if exists:
        _tablet_checkin_error(
            http_status=400,
            detail="Already checked in today",
            result_code="ALREADY_CHECKED_IN_TODAY",
            can_retry=False,
        )
    month_start = datetime(now.year, now.month, 1)
    usage = (
        db.query(Attendance)
        .filter(Attendance.member_id == member.id, Attendance.checked_in_at >= month_start)
        .count()
    )
    if membership.monthly_limit is not None and usage >= membership.monthly_limit:
        _tablet_checkin_error(
            http_status=400,
            detail="Monthly usage limit reached",
            result_code="MONTHLY_USAGE_LIMIT_REACHED",
            can_retry=False,
        )
    attendance = Attendance(member_id=member.id, class_id=0, status="present")
    db.add(attendance)
    db.commit()
    usage_after = usage + 1
    usage_limit = membership.monthly_limit
    remaining_usage_count = (
        max(0, usage_limit - usage_after) if usage_limit is not None else None
    )
    if membership.monthly_limit is not None:
        remaining_text = f"{remaining_usage_count}/{membership.monthly_limit}"
    else:
        remaining_text = "unlimited"
    days_left = max(0, (membership.end_date - now).days) if membership.end_date else None
    return {
        "ok": True,
        "status_label": "success",
        "severity": "success",
        "result_code": "CHECK_IN_OK",
        "ui_state": "success",
        "can_retry": False,
        "reset_after_ms": 2600,
        "message": (
            f"Welcome back, {member.full_name}! Remaining usage {remaining_text}."
            if days_left is None
            else f"Welcome back, {member.full_name}! Remaining usage {remaining_text}, {days_left} days left."
        ),
        "member_name": member.full_name,
        "member_no": getattr(member, "member_no", None),
        "remaining_usage": remaining_text,
        "remaining_usage_count": remaining_usage_count,
        "usage_limit": usage_limit,
        "usage_used_this_month": usage_after,
        "days_left": days_left,
        "membership_status": membership.status,
        "center_name": center.name,
    }


@router.post("", status_code=201)
def create_center(
    body: CenterCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    member = db.query(Member).filter(Member.id == user["id"]).first()
    if not member or getattr(member, "role", "member") != "admin":
        raise HTTPException(status_code=403, detail="Only platform admin can create center")
    exists = db.query(Center).filter(Center.slug == body.slug.strip()).first()
    if exists:
        raise HTTPException(status_code=400, detail="Center slug already exists")
    center = Center(
        name=body.name.strip(),
        slug=body.slug.strip().lower(),
        created_by_member_id=user["id"],
    )
    db.add(center)
    db.commit()
    db.refresh(center)
    db.add(
        CenterMembership(
            center_id=center.id,
            member_id=user["id"],
            role="admin",
            status="active",
            invited_by_member_id=user["id"],
        )
    )
    db.commit()
    return {"id": center.id, "name": center.name, "slug": center.slug}


@router.post("/grant-admin")
def grant_center_admin(
    body: GrantAdminBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, body.center_id, user["id"])
    member = (
        db.query(Member)
        .filter(Member.email == body.member_email.strip().lower())
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    row = (
        db.query(CenterMembership)
        .filter(
            CenterMembership.center_id == body.center_id,
            CenterMembership.member_id == member.id,
        )
        .first()
    )
    if not row:
        row = CenterMembership(
            center_id=body.center_id,
            member_id=member.id,
            role="admin",
            status="active",
            invited_by_member_id=user["id"],
        )
        db.add(row)
    else:
        row.role = "admin"
        row.status = "active"
        row.invited_by_member_id = user["id"]
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"center_id": body.center_id, "member_id": member.id, "role": "admin"}


@router.post("/join-by-email")
def join_center_by_email(
    body: JoinByEmailBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    center = db.query(Center).filter(Center.slug == body.center_slug.strip().lower()).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    _assert_center_admin(db, center.id, user["id"])
    member = db.query(Member).filter(Member.email == body.member_email.strip().lower()).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    row = (
        db.query(CenterMembership)
        .filter(CenterMembership.center_id == center.id, CenterMembership.member_id == member.id)
        .first()
    )
    if not row:
        row = CenterMembership(
            center_id=center.id,
            member_id=member.id,
            role="member",
            status="active",
            invited_by_member_id=user["id"],
        )
        db.add(row)
    else:
        row.status = "active"
        row.role = "member" if row.role != "admin" else "admin"
        row.invited_by_member_id = user["id"]
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"center_id": center.id, "member_id": member.id, "status": "active"}


@router.post("/join-request")
def request_join_center(
    body: JoinRequestBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    center = db.query(Center).filter(Center.slug == body.center_slug.strip().lower()).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    row = (
        db.query(CenterMembership)
        .filter(CenterMembership.center_id == center.id, CenterMembership.member_id == user["id"])
        .first()
    )
    if not row:
        row = CenterMembership(
            center_id=center.id,
            member_id=user["id"],
            role="member",
            status="pending",
        )
        db.add(row)
    elif row.status == "pending":
        raise HTTPException(status_code=409, detail="Join request already pending")
    elif row.status == "active":
        raise HTTPException(status_code=409, detail="Already joined this center")
    else:
        row.status = "pending"
        row.role = "member" if row.role != "admin" else "admin"
        row.updated_at = datetime.utcnow()
    db.commit()
    return {
        "center_id": center.id,
        "member_id": user["id"],
        "status": "pending",
        "message": "Join request submitted",
    }


@router.get("/discover")
def discover_centers(
    query: str = Query(default="", max_length=128),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    term = query.strip()
    q = db.query(Center).filter(Center.is_active == True)
    if term:
        like = f"%{term.lower()}%"
        q = q.filter(
            or_(
                Center.name.ilike(like),
                Center.slug.ilike(like),
            )
        )
    centers = q.order_by(Center.name.asc()).limit(limit).all()
    if not centers:
        return {"items": [], "total": 0}

    center_ids = [c.id for c in centers]
    memberships = (
        db.query(CenterMembership)
        .filter(
            CenterMembership.member_id == user["id"],
            CenterMembership.center_id.in_(center_ids),
        )
        .all()
    )
    membership_by_center = {m.center_id: m for m in memberships}
    items: list[CenterDiscoverItem] = []
    for center in centers:
        membership = membership_by_center.get(center.id)
        status = membership.status if membership else "none"
        items.append(
            CenterDiscoverItem(
                center_id=center.id,
                name=center.name,
                slug=center.slug,
                membership_status=status,
                membership_role=membership.role if membership else None,
                can_request=status in ("none", "rejected"),
            )
        )
    return {"items": [item.model_dump() for item in items], "total": len(items)}


@router.get("/my-memberships")
def my_center_memberships(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rows = (
        db.query(CenterMembership, Center)
        .join(Center, Center.id == CenterMembership.center_id)
        .filter(CenterMembership.member_id == user["id"])
        .order_by(Center.name.asc())
        .all()
    )
    return [
        {
            "center_id": center.id,
            "center_name": center.name,
            "center_slug": center.slug,
            "role": cm.role,
            "status": cm.status,
            "updated_at": cm.updated_at,
        }
        for cm, center in rows
    ]


@router.post("/join-approval")
def approve_join_request(
    body: ApproveJoinBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, body.center_id, user["id"])
    row = (
        db.query(CenterMembership)
        .filter(CenterMembership.center_id == body.center_id, CenterMembership.member_id == body.member_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Join request not found")
    row.status = "active" if body.approve else "rejected"
    row.updated_at = datetime.utcnow()
    db.commit()
    return {"center_id": body.center_id, "member_id": body.member_id, "status": row.status}


@router.get("/{center_id}/members")
def center_members(
    center_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, center_id, user["id"])
    rows = (
        db.query(CenterMembership, Member)
        .join(Member, Member.id == CenterMembership.member_id)
        .filter(CenterMembership.center_id == center_id, CenterMembership.status == "active")
        .all()
    )
    out = []
    for cm, member in rows:
        membership = (
            db.query(Membership)
            .filter(Membership.member_id == member.id, Membership.status == "active")
            .order_by(Membership.end_date.desc())
            .first()
        )
        today = datetime.utcnow()
        month_start = datetime(today.year, today.month, 1)
        usage = (
            db.query(Attendance)
            .filter(Attendance.member_id == member.id, Attendance.checked_in_at >= month_start)
            .count()
        )
        out.append(
            {
                "member_id": member.id,
                "member_no": getattr(member, "member_no", None),
                "full_name": member.full_name,
                "email": member.email,
                "birth_date": getattr(member, "birth_date", None),
                "age": _calculate_age(getattr(member, "birth_date", None)),
                "level": getattr(member, "member_level", "starter"),
                "center_role": cm.role,
                "membership_status": membership.status if membership else "none",
                "membership_plan": membership.plan if membership else None,
                "remaining_uses": (
                    (membership.monthly_limit - usage)
                    if membership and membership.monthly_limit is not None
                    else None
                ),
                "monthly_limit": membership.monthly_limit if membership else None,
            }
        )
    return out


@router.get("/{center_id}")
def center_detail(
    center_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, center_id, user["id"])
    center = db.query(Center).filter(Center.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    return {
        "id": center.id,
        "name": center.name,
        "slug": center.slug,
        "tablet_theme": center.tablet_theme,
        "tablet_welcome_text": center.tablet_welcome_text,
        "landing_is_published": bool(getattr(center, "landing_is_published", False)),
    }


@router.post("/{center_id}/tablet-theme")
def update_tablet_theme(
    center_id: int,
    body: TabletThemeBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, center_id, user["id"])
    center = db.query(Center).filter(Center.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    if body.tablet_welcome_text is not None:
        center.tablet_welcome_text = body.tablet_welcome_text.strip()
    if body.tablet_theme is not None:
        center.tablet_theme = body.tablet_theme.strip()
    if body.tablet_logo_url is not None:
        center.tablet_logo_url = body.tablet_logo_url.strip() if body.tablet_logo_url else None
    if body.tablet_accent_color is not None:
        color = body.tablet_accent_color.strip() if body.tablet_accent_color else ""
        if color and not HEX_COLOR_RE.match(color):
            raise HTTPException(status_code=400, detail="tablet_accent_color must be a hex color")
        center.tablet_accent_color = color or "#2f855a"
    if body.tablet_background_url is not None:
        center.tablet_background_url = (
            body.tablet_background_url.strip() if body.tablet_background_url else None
        )
    db.commit()
    db.refresh(center)
    return {
        "center_id": center.id,
        "tablet_welcome_text": center.tablet_welcome_text,
        "tablet_theme": center.tablet_theme,
        "tablet_logo_url": center.tablet_logo_url,
        "tablet_accent_color": getattr(center, "tablet_accent_color", "#2f855a"),
        "tablet_background_url": getattr(center, "tablet_background_url", None),
    }


@router.get("/{center_id}/landing")
def get_center_landing_admin(
    center_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, center_id, user["id"])
    center = db.query(Center).filter(Center.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    payload = _load_landing_payload(center)
    return {
        "center_id": center.id,
        "center_slug": center.slug,
        "center_name": center.name,
        "landing_is_published": bool(getattr(center, "landing_is_published", False)),
        "landing_content": payload,
    }


@router.post("/{center_id}/landing")
def update_center_landing_admin(
    center_id: int,
    body: LandingContentBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, center_id, user["id"])
    center = db.query(Center).filter(Center.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    sanitized_blocks = _sanitize_landing_blocks(body.blocks)
    center.landing_content_json = json.dumps(
        {"blocks": sanitized_blocks}, ensure_ascii=True, separators=(",", ":")
    )
    if body.publish is not None:
        center.landing_is_published = body.publish
    db.commit()
    db.refresh(center)
    return {
        "center_id": center.id,
        "landing_is_published": bool(getattr(center, "landing_is_published", False)),
        "landing_content": _load_landing_payload(center),
    }


@router.get("/public/{center_slug}/landing")
def get_center_public_landing(
    center_slug: str,
    db: Session = Depends(get_db),
):
    center = db.query(Center).filter(Center.slug == center_slug.strip().lower()).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    if not center.is_active or not bool(getattr(center, "landing_is_published", False)):
        raise HTTPException(status_code=404, detail="Landing page not published")
    payload = _load_landing_payload(center)
    return {
        "center_id": center.id,
        "center_name": center.name,
        "center_slug": center.slug,
        "branding": {
            "tablet_theme": center.tablet_theme,
            "tablet_logo_url": center.tablet_logo_url,
            "tablet_accent_color": getattr(center, "tablet_accent_color", "#2f855a"),
            "tablet_background_url": getattr(center, "tablet_background_url", None),
        },
        "landing_content": payload,
    }


@router.get("/tablet/{center_slug}")
def tablet_config(
    center_slug: str,
    db: Session = Depends(get_db),
):
    center = db.query(Center).filter(Center.slug == center_slug.strip().lower()).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    return {
        "center_id": center.id,
        "center_name": center.name,
        "center_slug": center.slug,
        "tablet_welcome_text": center.tablet_welcome_text,
        "tablet_theme": center.tablet_theme,
        "tablet_logo_url": center.tablet_logo_url,
        "tablet_accent_color": getattr(center, "tablet_accent_color", "#2f855a"),
        "tablet_background_url": getattr(center, "tablet_background_url", None),
    }


@router.post("/onsite-payment")
def onsite_payment_record(
    body: OnsitePaymentBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_center_admin(db, body.center_id, user["id"])
    member = db.query(Member).filter(Member.id == body.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    membership = (
        db.query(Membership)
        .filter(Membership.member_id == body.member_id, Membership.status == "active")
        .order_by(Membership.end_date.desc())
        .first()
    )
    if not membership:
        raise HTTPException(status_code=400, detail="No active membership to attach payment")
    payment = Payment(
        member_id=body.member_id,
        membership_id=membership.id,
        amount=body.amount,
        currency=body.currency,
        status="completed",
        source="onsite_manual",
        memo=body.memo,
        center_id=body.center_id,
        recorded_by_member_id=user["id"],
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {
        "id": payment.id,
        "source": payment.source,
        "amount": payment.amount / 100.0,
        "currency": payment.currency,
        "status": payment.status,
    }


@router.post("/tablet/check-in")
def tablet_check_in(
    body: TabletCheckinBody,
    db: Session = Depends(get_db),
):
    if not body.phone_last4.isdigit():
        _tablet_checkin_error(
            http_status=400,
            detail="phone_last4 must contain only digits",
            result_code="INVALID_PHONE_LAST4",
            can_retry=True,
        )
    center = db.query(Center).filter(Center.slug == body.center_slug.strip().lower()).first()
    if not center:
        _tablet_checkin_error(
            http_status=404,
            detail="Center not found",
            result_code="CENTER_NOT_FOUND",
            can_retry=False,
        )
    member = (
        db.query(Member)
        .filter(Member.phone.endswith(body.phone_last4), Member.is_active == True)
        .order_by(Member.id.asc())
        .first()
    )
    if not member:
        _tablet_checkin_error(
            http_status=404,
            detail="Member not found",
            result_code="MEMBER_NOT_FOUND",
            can_retry=True,
        )
    cm = (
        db.query(CenterMembership)
        .filter(
            CenterMembership.center_id == center.id,
            CenterMembership.member_id == member.id,
            CenterMembership.status == "active",
        )
        .first()
    )
    if not cm:
        _tablet_checkin_error(
            http_status=403,
            detail="Member is not active in this center",
            result_code="CENTER_MEMBERSHIP_INACTIVE",
            can_retry=False,
        )
    duplicates = (
        db.query(Member.id)
        .join(
            CenterMembership,
            (CenterMembership.member_id == Member.id)
            & (CenterMembership.center_id == center.id)
            & (CenterMembership.status == "active"),
        )
        .filter(Member.phone.endswith(body.phone_last4), Member.is_active == True)
        .limit(2)
        .all()
    )
    if len(duplicates) > 1:
        _tablet_checkin_error(
            http_status=409,
            detail="Multiple members match phone suffix",
            result_code="AMBIGUOUS_MEMBER_MATCH",
            can_retry=False,
        )
    return _tablet_complete_daily_checkin(db, center, member)


class TabletCheckinQrBody(BaseModel):
    center_slug: str
    token: str = Field(..., min_length=24, max_length=4096)


@router.post("/tablet/check-in-qr")
def tablet_check_in_qr(
    body: TabletCheckinQrBody,
    db: Session = Depends(get_db),
):
    try:
        member_id = decode_checkin_qr_token(body.token)
    except ValueError:
        _tablet_checkin_error(
            http_status=401,
            detail="Invalid or expired check-in code",
            result_code="INVALID_CHECKIN_QR",
            can_retry=True,
        )
    center = db.query(Center).filter(Center.slug == body.center_slug.strip().lower()).first()
    if not center:
        _tablet_checkin_error(
            http_status=404,
            detail="Center not found",
            result_code="CENTER_NOT_FOUND",
            can_retry=False,
        )
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.is_active == True)
        .first()
    )
    if not member:
        _tablet_checkin_error(
            http_status=404,
            detail="Member not found",
            result_code="MEMBER_NOT_FOUND",
            can_retry=False,
        )
    cm = (
        db.query(CenterMembership)
        .filter(
            CenterMembership.center_id == center.id,
            CenterMembership.member_id == member.id,
            CenterMembership.status == "active",
        )
        .first()
    )
    if not cm:
        _tablet_checkin_error(
            http_status=403,
            detail="Member is not active in this center",
            result_code="CENTER_MEMBERSHIP_INACTIVE",
            can_retry=False,
        )
    return _tablet_complete_daily_checkin(db, center, member)
