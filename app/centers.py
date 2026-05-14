from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

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


class ApproveJoinBody(BaseModel):
    center_id: int
    member_id: int
    approve: bool = True


class TabletThemeBody(BaseModel):
    tablet_welcome_text: str | None = Field(default=None, max_length=256)
    tablet_theme: str | None = Field(default=None, max_length=64)
    tablet_logo_url: str | None = Field(default=None, max_length=512)


class OnsitePaymentBody(BaseModel):
    center_id: int
    member_id: int
    amount: int = Field(..., ge=1)
    currency: str = "aud"
    memo: str | None = Field(default=None, max_length=512)


class TabletCheckinBody(BaseModel):
    center_slug: str
    phone_last4: str = Field(..., min_length=4, max_length=4)


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
    else:
        row.status = "pending"
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"center_id": center.id, "member_id": user["id"], "status": "pending"}


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
    db.commit()
    db.refresh(center)
    return {
        "center_id": center.id,
        "tablet_welcome_text": center.tablet_welcome_text,
        "tablet_theme": center.tablet_theme,
        "tablet_logo_url": center.tablet_logo_url,
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
    center = db.query(Center).filter(Center.slug == body.center_slug.strip().lower()).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    member = (
        db.query(Member)
        .filter(Member.phone.endswith(body.phone_last4), Member.is_active == True)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
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
        raise HTTPException(status_code=403, detail="Member is not active in this center")
    membership = (
        db.query(Membership)
        .filter(Membership.member_id == member.id, Membership.status == "active")
        .order_by(Membership.end_date.desc())
        .first()
    )
    if not membership:
        raise HTTPException(status_code=400, detail="No active membership")
    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    exists = (
        db.query(Attendance)
        .filter(Attendance.member_id == member.id, Attendance.checked_in_at >= day_start)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Already checked in today")
    month_start = datetime(now.year, now.month, 1)
    usage = (
        db.query(Attendance)
        .filter(Attendance.member_id == member.id, Attendance.checked_in_at >= month_start)
        .count()
    )
    if membership.monthly_limit is not None and usage >= membership.monthly_limit:
        raise HTTPException(status_code=400, detail="Monthly usage limit reached")
    attendance = Attendance(member_id=member.id, class_id=0, status="present")
    db.add(attendance)
    db.commit()
    usage_after = usage + 1
    if membership.monthly_limit is not None:
        remaining_text = f"{max(0, membership.monthly_limit - usage_after)}/{membership.monthly_limit}"
    else:
        remaining_text = "unlimited"
    return {
        "message": f"Welcome back, {member.full_name}! Remaining usage {remaining_text}.",
        "member_name": member.full_name,
        "member_no": getattr(member, "member_no", None),
        "remaining_usage": remaining_text,
        "membership_status": membership.status,
        "center_name": center.name,
    }
