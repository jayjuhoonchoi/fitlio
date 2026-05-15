from datetime import datetime, timedelta

import json
from urllib.parse import urlsplit, urlunsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    Attendance,
    Center,
    CenterMembership,
    CommunityPost,
    CommunityReaction,
    FitnessClass,
    InstructorProfile,
    InstructorReaction,
    Member,
    Membership,
    Payment,
    Suggestion,
    ContentReport,
    PaymentWebhookEvent,
)
from app.payment_gateway import create_payment_intent

router = APIRouter(prefix="/member", tags=["member-experience"])

PAYMENT_METHODS = {"paypal", "naverpay", "kakaopay", "payco", "bank_transfer", "card"}
PAYMENT_KNOWN_STATUSES = {"pending", "completed", "failed", "cancelled"}
PAYMENT_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
COMMUNITY_MEDIA_TYPES = {"image", "video"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".ogg"}


def _normalize_payment_status(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    return normalized if normalized in PAYMENT_KNOWN_STATUSES else "pending"


def _payment_state(status: str | None) -> dict:
    normalized = _normalize_payment_status(status)
    if normalized == "completed":
        return {
            "status": "completed",
            "phase": "succeeded",
            "is_terminal": True,
            "retry_ready": False,
            "member_message": "Payment completed. Membership is active.",
        }
    if normalized == "failed":
        return {
            "status": "failed",
            "phase": "terminal_failed",
            "is_terminal": True,
            "retry_ready": True,
            "member_message": "Payment failed. Please retry to activate your membership.",
        }
    if normalized == "cancelled":
        return {
            "status": "cancelled",
            "phase": "terminal_cancelled",
            "is_terminal": True,
            "retry_ready": True,
            "member_message": "Payment was cancelled. Retry whenever you are ready.",
        }
    return {
        "status": "pending",
        "phase": "in_flight",
        "is_terminal": False,
        "retry_ready": False,
        "member_message": "Payment is pending confirmation.",
    }


class MembershipPurchaseBody(BaseModel):
    plan: str = Field(..., pattern="^(monthly|yearly)$")
    payment_method: str = Field(..., pattern="^(paypal|naverpay|kakaopay|payco|bank_transfer|card)$")


class InstructorReactBody(BaseModel):
    instructor_id: int
    content: str | None = Field(default=None, max_length=1000)


class SuggestionBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    is_anonymous: bool = True


class CommunityPostBody(BaseModel):
    center_id: int | None = None
    content: str | None = Field(default=None, max_length=2000)
    media_url: str | None = Field(default=None, max_length=1024)
    media_type: str = Field(default="image", pattern="^(image|video)$")


class CommunityCommentBody(BaseModel):
    post_id: int
    content: str = Field(..., min_length=1, max_length=1000)


class ReportBody(BaseModel):
    target_type: str = Field(..., pattern="^(community_post|community_comment)$")
    target_id: int
    reason: str = Field(..., min_length=1, max_length=255)


class ModeratorHideBody(BaseModel):
    target_type: str = Field(..., pattern="^(community_post|community_comment)$")
    target_id: int
    hide: bool = True
    reason: str | None = Field(default=None, max_length=255)


class PaymentWebhookBody(BaseModel):
    provider: str
    event_type: str
    external_ref: str | None = None
    status: str | None = None
    payload: dict | None = None


class ModeratorDecisionBody(BaseModel):
    report_id: int
    status: str = Field(..., pattern="^(open|resolved|rejected)$")


def _member_center_ids(db: Session, member_id: int):
    rows = (
        db.query(CenterMembership.center_id)
        .filter(CenterMembership.member_id == member_id, CenterMembership.status == "active")
        .all()
    )
    return [r[0] for r in rows]


def _normalize_media_type(media_type: str | None) -> str:
    normalized = (media_type or "image").strip().lower()
    return normalized if normalized in COMMUNITY_MEDIA_TYPES else "image"


def _normalized_media_url(raw_url: str | None) -> str | None:
    value = (raw_url or "").strip()
    if not value:
        return None
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Media URL must use http or https")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Media URL host is required")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Media URL credentials are not allowed")
    cleaned = urlunsplit((scheme, parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
    return cleaned


def _media_url_matches_type(media_url: str, media_type: str) -> bool:
    lowered = media_url.lower()
    dot_idx = lowered.rfind(".")
    ext = lowered[dot_idx:] if dot_idx != -1 else ""
    if media_type == "image":
        return ext in IMAGE_EXTENSIONS
    return ext in VIDEO_EXTENSIONS


def _normalize_post_media(media_url: str | None, media_type: str | None) -> tuple[str | None, str | None]:
    normalized_url = _normalized_media_url(media_url)
    normalized_type = _normalize_media_type(media_type)
    if not normalized_url:
        return None, None
    if not _media_url_matches_type(normalized_url, normalized_type):
        expected = ", ".join(sorted(IMAGE_EXTENSIONS if normalized_type == "image" else VIDEO_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Media URL does not match media type '{normalized_type}'. Allowed extensions: {expected}",
        )
    return normalized_url, normalized_type


def _is_admin_or_staff(db: Session, member_id: int) -> bool:
    member = db.query(Member).filter(Member.id == member_id).first()
    if member and getattr(member, "role", "member") == "admin":
        return True
    row = (
        db.query(CenterMembership)
        .filter(
            CenterMembership.member_id == member_id,
            CenterMembership.status == "active",
            CenterMembership.role.in_(["admin", "staff"]),
        )
        .first()
    )
    return bool(row)


def _this_month_attendance_count(db: Session, member_id: int) -> int:
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    return (
        db.query(Attendance)
        .filter(Attendance.member_id == member_id, Attendance.checked_in_at >= month_start)
        .count()
    )


@router.get("/home")
def member_home_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    member = db.query(Member).filter(Member.id == user["id"]).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    membership = (
        db.query(Membership)
        .filter(Membership.member_id == member.id)
        .order_by(Membership.end_date.desc())
        .first()
    )
    latest_payment = None
    if membership:
        latest_payment = (
            db.query(Payment)
            .filter(Payment.membership_id == membership.id)
            .order_by(Payment.created_at.desc())
            .first()
        )
    if not latest_payment:
        latest_payment = (
            db.query(Payment)
            .filter(Payment.member_id == member.id)
            .order_by(Payment.created_at.desc())
            .first()
        )
    now = datetime.utcnow()
    is_expired = not membership or membership.end_date < now or membership.status != "active"
    payment_state = _payment_state(getattr(latest_payment, "status", None))
    can_retry_payment = payment_state["retry_ready"]
    can_pay_now = (
        is_expired
        or (membership and membership.status in {"cancelled", "expired", "failed"})
        or can_retry_payment
    )
    renewal_prompt = "retry_payment" if can_retry_payment else ("renew_membership" if can_pay_now else "none")
    used = _this_month_attendance_count(db, member.id) if membership else 0
    centers = (
        db.query(CenterMembership, Center)
        .join(Center, Center.id == CenterMembership.center_id)
        .filter(CenterMembership.member_id == member.id, CenterMembership.status == "active")
        .all()
    )
    return {
        "member": {
            "id": member.id,
            "full_name": member.full_name,
            "level": member.member_level,
        },
        "membership": (
            {
                "status": membership.status,
                "plan": membership.plan,
                "days_left": max(0, (membership.end_date - now).days),
                "monthly_limit": membership.monthly_limit,
                "visits_remaining": (
                    max(0, membership.monthly_limit - used)
                    if membership.monthly_limit is not None
                    else None
                ),
                "is_expired": is_expired,
                "can_pay_now": can_pay_now,
                "renewal_prompt": renewal_prompt,
                "latest_payment_status": payment_state["status"],
                "payment_state": payment_state,
            }
            if membership
            else {
                "status": "none",
                "is_expired": True,
                "can_pay_now": True,
                "renewal_prompt": renewal_prompt,
                "latest_payment_status": payment_state["status"],
                "payment_state": payment_state,
            }
        ),
        "centers": [{"id": c.id, "name": c.name, "slug": c.slug} for _, c in centers],
    }


@router.get("/classes")
def classes_for_member(
    center_id: int | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    member = db.query(Member).filter(Member.id == user["id"]).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    levels = ["starter", "core", "elite", "vip"]
    member_idx = levels.index(member.member_level) if member.member_level in levels else 0
    q = db.query(FitnessClass).filter(FitnessClass.schedule >= datetime.utcnow() - timedelta(hours=1))
    if center_id is not None:
        q = q.filter(FitnessClass.center_id == center_id)
    else:
        center_ids = _member_center_ids(db, member.id)
        if center_ids:
            q = q.filter((FitnessClass.center_id == None) | (FitnessClass.center_id.in_(center_ids)))
    rows = q.order_by(FitnessClass.schedule.asc()).all()
    out = []
    for c in rows:
        required_idx = levels.index(c.level_required) if c.level_required in levels else 0
        if member_idx < required_idx:
            continue
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "instructor": c.instructor,
                "schedule": c.schedule,
                "capacity": c.capacity,
                "current_count": c.current_count,
                "center_id": getattr(c, "center_id", None),
                "level_required": getattr(c, "level_required", "starter"),
            }
        )
    return out


@router.get("/instructors")
def instructors_feed(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    rows = db.query(InstructorProfile).order_by(InstructorProfile.display_name.asc()).all()
    out = []
    for inst in rows:
        likes = (
            db.query(InstructorReaction)
            .filter(InstructorReaction.instructor_id == inst.id, InstructorReaction.type == "like")
            .count()
        )
        comments = (
            db.query(InstructorReaction)
            .filter(
                InstructorReaction.instructor_id == inst.id,
                InstructorReaction.type == "comment",
            )
            .order_by(InstructorReaction.created_at.desc())
            .limit(20)
            .all()
        )
        out.append(
            {
                "id": inst.id,
                "display_name": inst.display_name,
                "bio": getattr(inst, "bio", None),
                "avatar_url": getattr(inst, "avatar_url", None),
                "specialties": getattr(inst, "specialties", None),
                "likes": likes,
                "comments": [
                    {"member_id": c.member_id, "content": c.content, "created_at": c.created_at}
                    for c in comments
                ],
            }
        )
    return out


@router.post("/instructors/{instructor_id}/like")
def like_instructor(
    instructor_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    inst = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instructor not found")
    existing = (
        db.query(InstructorReaction)
        .filter(
            InstructorReaction.instructor_id == instructor_id,
            InstructorReaction.member_id == user["id"],
            InstructorReaction.type == "like",
        )
        .first()
    )
    if existing:
        return {"ok": True, "message": "Already liked"}
    db.add(
        InstructorReaction(
            instructor_id=instructor_id,
            member_id=user["id"],
            type="like",
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/instructors/{instructor_id}/comments")
def comment_instructor(
    instructor_id: int,
    body: InstructorReactBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if instructor_id != body.instructor_id:
        raise HTTPException(status_code=400, detail="Instructor id mismatch")
    inst = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instructor not found")
    text = (body.content or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Comment content required")
    row = InstructorReaction(
        instructor_id=instructor_id,
        member_id=user["id"],
        type="comment",
        content=text,
    )
    db.add(row)
    db.commit()
    return {"ok": True}


@router.post("/purchase")
def purchase_membership(
    body: MembershipPurchaseBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if body.payment_method not in PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="Unsupported payment method")
    now = datetime.utcnow()
    if body.plan == "monthly":
        end_date = now + timedelta(days=30)
        amount = 5000
    else:
        end_date = now + timedelta(days=365)
        amount = 50000
    intent = create_payment_intent(body.payment_method, amount, "aud")
    retry_candidate_payment = (
        db.query(Payment)
        .filter(
            Payment.member_id == user["id"],
            Payment.status.in_(["failed", "cancelled"]),
        )
        .order_by(Payment.created_at.desc())
        .first()
    )
    membership = None
    is_retry = False
    if retry_candidate_payment:
        membership = (
            db.query(Membership)
            .filter(Membership.id == retry_candidate_payment.membership_id)
            .first()
        )
        if membership and membership.plan == body.plan:
            is_retry = True
            membership.status = "pending"
            membership.end_date = end_date
            membership.auto_renew = True
            db.commit()
            db.refresh(membership)

    if not membership:
        membership = Membership(
            member_id=user["id"],
            plan=body.plan,
            status="pending",
            end_date=end_date,
            auto_renew=True,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)

    payment = Payment(
        member_id=user["id"],
        membership_id=membership.id,
        amount=amount,
        currency="aud",
        status="pending",
        source="online",
        payment_method=body.payment_method,
        stripe_payment_intent_id=f"sim_{body.payment_method}_{membership.id}",
        external_ref=intent.external_ref,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    payment_state = _payment_state(payment.status)
    message = (
        "Bank transfer requested. Membership activates after admin confirmation."
        if body.payment_method == "bank_transfer"
        else (
            "Retry started. Complete checkout to reactivate your membership."
            if is_retry
            else "Payment initiated. Complete checkout to activate membership."
        )
    )
    return {
        "membership_id": membership.id,
        "payment_id": payment.id,
        "payment_method": body.payment_method,
        "payment_status": payment.status,
        "payment_state": payment_state,
        "payment_lifecycle": payment_state["phase"],
        "can_retry_payment": payment_state["retry_ready"],
        "attempt_type": "retry" if is_retry else "new_purchase",
        "checkout_url": intent.checkout_url,
        "external_ref": intent.external_ref,
        "message": message,
    }


@router.post("/suggestions")
def send_suggestion(
    body: SuggestionBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    center_ids = _member_center_ids(db, user["id"])
    row = Suggestion(
        member_id=None if body.is_anonymous else user["id"],
        center_id=center_ids[0] if center_ids else None,
        content=body.content.strip(),
        is_anonymous=body.is_anonymous,
        status="open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "is_anonymous": row.is_anonymous}


@router.get("/community/posts")
def community_posts(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    center_ids = _member_center_ids(db, user["id"])
    q = db.query(CommunityPost)
    if center_ids:
        q = q.filter((CommunityPost.center_id == None) | (CommunityPost.center_id.in_(center_ids)))
    rows = q.filter(CommunityPost.is_hidden == False).order_by(CommunityPost.created_at.desc()).limit(80).all()
    out = []
    for p in rows:
        author = db.query(Member).filter(Member.id == p.author_member_id).first()
        likes = (
            db.query(CommunityReaction)
            .filter(CommunityReaction.post_id == p.id, CommunityReaction.type == "like")
            .count()
        )
        comments = (
            db.query(CommunityReaction)
            .filter(
                CommunityReaction.post_id == p.id,
                CommunityReaction.type == "comment",
                CommunityReaction.is_hidden == False,
            )
            .order_by(CommunityReaction.created_at.asc())
            .limit(50)
            .all()
        )
        out.append(
            {
                "id": p.id,
                "author_name": author.full_name if author else "Unknown",
                "content": p.content,
                "media_url": p.media_url,
                "media_type": p.media_type,
                "likes": likes,
                "comments": [
                    {"member_id": c.member_id, "content": c.content, "created_at": c.created_at}
                    for c in comments
                ],
                "created_at": p.created_at,
            }
        )
    return out


@router.post("/community/posts")
def create_community_post(
    body: CommunityPostBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    content = (body.content or "").strip()
    media_url, media_type = _normalize_post_media(body.media_url, body.media_type)
    if not content and not media_url:
        raise HTTPException(status_code=400, detail="Post content or media required")
    row = CommunityPost(
        author_member_id=user["id"],
        center_id=body.center_id,
        content=content or None,
        media_url=media_url,
        media_type=media_type or "image",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.post("/community/posts/{post_id}/like")
def like_post(post_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.is_hidden:
        raise HTTPException(status_code=404, detail="Post not found")
    existing = (
        db.query(CommunityReaction)
        .filter(
            CommunityReaction.post_id == post_id,
            CommunityReaction.member_id == user["id"],
            CommunityReaction.type == "like",
        )
        .first()
    )
    if existing:
        return {"ok": True, "message": "Already liked"}
    db.add(CommunityReaction(post_id=post_id, member_id=user["id"], type="like"))
    db.commit()
    return {"ok": True}


@router.post("/community/comments")
def comment_post(
    body: CommunityCommentBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == body.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.is_hidden:
        raise HTTPException(status_code=404, detail="Post not found")
    db.add(
        CommunityReaction(
            post_id=body.post_id,
            member_id=user["id"],
            type="comment",
            content=body.content.strip(),
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/community/reports")
def report_content(
    body: ReportBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Report reason required")
    if body.target_type == "community_post":
        target = db.query(CommunityPost).filter(CommunityPost.id == body.target_id).first()
        if not target or target.is_hidden:
            raise HTTPException(status_code=404, detail="Target content not found")
    else:
        target = db.query(CommunityReaction).filter(CommunityReaction.id == body.target_id).first()
        if not target or target.type != "comment" or target.is_hidden:
            raise HTTPException(status_code=404, detail="Target content not found")
    row = ContentReport(
        reporter_member_id=user["id"],
        target_type=body.target_type,
        target_id=body.target_id,
        reason=reason,
        status="open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.get("/moderation/reports")
def moderation_reports(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not _is_admin_or_staff(db, user["id"]):
        raise HTTPException(status_code=403, detail="Moderator access required")
    rows = db.query(ContentReport).order_by(ContentReport.created_at.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/moderation/hide")
def moderation_hide(
    body: ModeratorHideBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not _is_admin_or_staff(db, user["id"]):
        raise HTTPException(status_code=403, detail="Moderator access required")
    if body.target_type == "community_post":
        row = db.query(CommunityPost).filter(CommunityPost.id == body.target_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        row.is_hidden = body.hide
        row.hidden_reason = (body.reason or "").strip() or None
    else:
        row = db.query(CommunityReaction).filter(CommunityReaction.id == body.target_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Comment not found")
        row.is_hidden = body.hide
    db.commit()
    return {"ok": True, "hidden": body.hide}


@router.post("/moderation/reports/status")
def moderation_report_status(
    body: ModeratorDecisionBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not _is_admin_or_staff(db, user["id"]):
        raise HTTPException(status_code=403, detail="Moderator access required")
    report = db.query(ContentReport).filter(ContentReport.id == body.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = body.status
    db.commit()
    return {"id": report.id, "status": report.status}


@router.post("/payments/webhook")
def payment_webhook(
    body: PaymentWebhookBody,
    db: Session = Depends(get_db),
):
    payload_raw = json.dumps(body.payload or {}, ensure_ascii=True)[:3800]
    duplicate = (
        db.query(PaymentWebhookEvent)
        .filter(
            PaymentWebhookEvent.provider == body.provider,
            PaymentWebhookEvent.event_type == body.event_type,
            PaymentWebhookEvent.external_ref == body.external_ref,
            PaymentWebhookEvent.payload == payload_raw,
        )
        .first()
    )
    if duplicate:
        return {"ok": True, "processed": bool(duplicate.processed), "duplicate": True}

    event = PaymentWebhookEvent(
        provider=body.provider,
        event_type=body.event_type,
        external_ref=body.external_ref,
        payload=payload_raw,
        processed=False,
    )
    db.add(event)
    if body.external_ref:
        payment = db.query(Payment).filter(Payment.external_ref == body.external_ref).first()
        normalized_status = _normalize_payment_status(body.status)
        if payment and normalized_status in PAYMENT_KNOWN_STATUSES:
            payment.status = normalized_status
            membership = db.query(Membership).filter(Membership.id == payment.membership_id).first()
            if membership:
                if normalized_status == "completed":
                    membership.status = "active"
                elif normalized_status == "pending" and membership.status in {"failed", "cancelled"}:
                    membership.status = "pending"
                elif normalized_status == "failed" and membership.status in {"pending", "cancelled"}:
                    membership.status = "failed"
                elif normalized_status == "cancelled" and membership.status in {"pending", "failed"}:
                    membership.status = "cancelled"
            event.processed = True
    db.commit()
    return {"ok": True, "processed": event.processed, "duplicate": False}
