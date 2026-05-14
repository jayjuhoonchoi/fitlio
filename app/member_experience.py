from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
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
)

router = APIRouter(prefix="/member", tags=["member-experience"])

PAYMENT_METHODS = {"paypal", "naverpay", "kakaopay", "payco", "bank_transfer", "card"}


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


def _member_center_ids(db: Session, member_id: int):
    rows = (
        db.query(CenterMembership.center_id)
        .filter(CenterMembership.member_id == member_id, CenterMembership.status == "active")
        .all()
    )
    return [r[0] for r in rows]


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
    now = datetime.utcnow()
    is_expired = not membership or membership.end_date < now or membership.status != "active"
    month_start = datetime(now.year, now.month, 1)
    used = 0
    if membership:
        used = db.query(func.count()).select_from(Payment).filter(Payment.member_id == member.id).count()
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
                "can_pay_now": is_expired,
            }
            if membership
            else {"status": "none", "is_expired": True, "can_pay_now": True}
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
    membership = Membership(
        member_id=user["id"],
        plan=body.plan,
        status="active",
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
        status="completed",
        source="online",
        payment_method=body.payment_method,
        stripe_payment_intent_id=f"sim_{body.payment_method}_{membership.id}",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {"membership_id": membership.id, "payment_id": payment.id, "payment_method": body.payment_method}


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
    rows = q.order_by(CommunityPost.created_at.desc()).limit(80).all()
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
            .filter(CommunityReaction.post_id == p.id, CommunityReaction.type == "comment")
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
    if not (body.content or "").strip() and not (body.media_url or "").strip():
        raise HTTPException(status_code=400, detail="Post content or media required")
    row = CommunityPost(
        author_member_id=user["id"],
        center_id=body.center_id,
        content=(body.content or "").strip() or None,
        media_url=(body.media_url or "").strip() or None,
        media_type=body.media_type,
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
