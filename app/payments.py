from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])

PAYMENT_KNOWN_STATUSES = {"pending", "completed", "failed", "cancelled"}


def _normalize_payment_status(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    return normalized if normalized in PAYMENT_KNOWN_STATUSES else "pending"


def _payment_state(status: str | None) -> dict:
    normalized = _normalize_payment_status(status)
    if normalized == "completed":
        return {
            "status": "completed",
            "severity": "success",
            "lifecycle": "succeeded",
            "is_terminal": True,
            "can_retry": False,
        }
    if normalized == "failed":
        return {
            "status": "failed",
            "severity": "error",
            "lifecycle": "terminal_failed",
            "is_terminal": True,
            "can_retry": True,
        }
    if normalized == "cancelled":
        return {
            "status": "cancelled",
            "severity": "warning",
            "lifecycle": "terminal_cancelled",
            "is_terminal": True,
            "can_retry": True,
        }
    return {
        "status": "pending",
        "severity": "pending",
        "lifecycle": "in_flight",
        "is_terminal": False,
        "can_retry": False,
    }

class MembershipCreate(BaseModel):
    plan: str  # monthly, yearly
    payment_method: str = "card"  # paypal | naverpay | kakaopay | payco | bank_transfer | card

class PaymentCreate(BaseModel):
    membership_id: int
    amount: int
    currency: str = "aud"

@router.post("/membership")
def create_membership(
    data: MembershipCreate,
    member_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if member_id != user["id"]:
        raise HTTPException(status_code=403, detail="Cannot purchase for another account")
    # 기간 설정
    if data.plan == "monthly":
        end_date = datetime.utcnow() + timedelta(days=30)
        amount = 5000  # $50.00 AUD
    elif data.plan == "yearly":
        end_date = datetime.utcnow() + timedelta(days=365)
        amount = 50000  # $500.00 AUD
    else:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # 회원권 생성
    membership = models.Membership(
        member_id=member_id,
        plan=data.plan,
        status="active",
        end_date=end_date,
        auto_renew=True
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    # 결제 레코드 생성 (Stripe 연동 준비)
    payment = models.Payment(
        member_id=member_id,
        membership_id=membership.id,
        amount=amount,
        currency="aud",
        status="completed",  # 실제론 Stripe 응답으로 업데이트
        source="online",
        payment_method=getattr(data, "payment_method", "card"),
        stripe_payment_intent_id="test_" + str(membership.id)  # Test Mode
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "membership": {
            "id": membership.id,
            "plan": membership.plan,
            "status": membership.status,
            "end_date": membership.end_date,
            "auto_renew": membership.auto_renew
        },
        "payment": {
            "id": payment.id,
            "amount": payment.amount / 100,  # cents → dollars
            "currency": payment.currency,
            "status": payment.status,
            "state": _payment_state(payment.status),
            "payment_method": getattr(payment, "payment_method", "card"),
            "stripe_payment_intent_id": payment.stripe_payment_intent_id
        }
    }

@router.get("/membership/{member_id}")
def get_membership(
    member_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if member_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    membership = db.query(models.Membership).filter(
        models.Membership.member_id == member_id,
        models.Membership.status == "active"
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="No active membership found")
    
    return {
        "id": membership.id,
        "plan": membership.plan,
        "status": membership.status,
        "end_date": membership.end_date,
        "auto_renew": membership.auto_renew
    }

@router.get("/history/{member_id}")
def get_payment_history(
    member_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if member_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    payments = db.query(models.Payment).filter(
        models.Payment.member_id == member_id
    ).all()
    
    return [
        {
            "id": p.id,
            "amount": p.amount / 100,
            "currency": p.currency,
            "status": p.status,
            "state": _payment_state(p.status),
            "source": getattr(p, "source", "online"),
            "payment_method": getattr(p, "payment_method", "card"),
            "center_id": getattr(p, "center_id", None),
            "external_ref": getattr(p, "external_ref", None),
            "memo": getattr(p, "memo", None),
            "created_at": p.created_at
        }
        for p in payments
    ]