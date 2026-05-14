from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import DirectMessage, Member

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageCreate(BaseModel):
    recipient_id: int
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("", status_code=201)
def send_message(
    body: MessageCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if body.recipient_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot send to yourself")
    recipient = db.query(Member).filter(Member.id == body.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    row = DirectMessage(
        sender_id=user["id"],
        recipient_id=body.recipient_id,
        content=body.content.strip(),
        is_read=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "sender_id": row.sender_id,
        "recipient_id": row.recipient_id,
        "content": row.content,
        "is_read": row.is_read,
        "created_at": row.created_at,
    }


@router.get("/thread/{other_member_id}")
def get_thread(
    other_member_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    exists = db.query(Member).filter(Member.id == other_member_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")
    rows = (
        db.query(DirectMessage)
        .filter(
            or_(
                (
                    (DirectMessage.sender_id == user["id"])
                    & (DirectMessage.recipient_id == other_member_id)
                ),
                (
                    (DirectMessage.sender_id == other_member_id)
                    & (DirectMessage.recipient_id == user["id"])
                ),
            )
        )
        .order_by(DirectMessage.created_at.asc(), DirectMessage.id.asc())
        .limit(min(max(limit, 1), 300))
        .all()
    )
    return [
        {
            "id": r.id,
            "sender_id": r.sender_id,
            "recipient_id": r.recipient_id,
            "content": r.content,
            "is_read": r.is_read,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/inbox")
def inbox(
    limit: int = 200,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rows = (
        db.query(DirectMessage)
        .filter(
            or_(
                DirectMessage.sender_id == user["id"],
                DirectMessage.recipient_id == user["id"],
            )
        )
        .order_by(DirectMessage.created_at.desc(), DirectMessage.id.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return [
        {
            "id": r.id,
            "sender_id": r.sender_id,
            "recipient_id": r.recipient_id,
            "content": r.content,
            "is_read": r.is_read,
            "created_at": r.created_at,
        }
        for r in rows
    ]


class MarkReadBody(BaseModel):
    message_id: int


@router.patch("/read")
def mark_as_read(
    body: MarkReadBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = db.query(DirectMessage).filter(DirectMessage.id == body.message_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")
    if row.recipient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Cannot update this message")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return {"id": row.id, "is_read": row.is_read}


@router.get("/admin/members")
def members_for_admin_messaging(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    rows = db.query(Member).order_by(Member.full_name.asc()).all()
    return [
        {
            "id": m.id,
            "full_name": m.full_name,
            "email": m.email,
            "member_no": getattr(m, "member_no", None),
            "role": getattr(m, "role", "member"),
        }
        for m in rows
    ]


@router.get("/admin-contact")
def admin_contact_for_members(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    admin = (
        db.query(Member)
        .filter(Member.role == "admin")
        .order_by(Member.id.asc())
        .first()
    )
    if not admin:
        raise HTTPException(status_code=404, detail="Admin contact not found")
    return {
        "id": admin.id,
        "full_name": admin.full_name,
        "email": admin.email,
    }
