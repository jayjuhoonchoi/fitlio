from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.database import get_db
from app import models

router = APIRouter(prefix="/payments", tags=["payments"])

class MembershipCreate(BaseModel):
    plan: str  # monthly, yearly

class PaymentCreate(BaseModel):
    membership_id: int
    amount: int
    currency: str = "aud"

@router.post("/membership")
def create_membership(
    data: MembershipCreate,
    member_id: int,
    db: Session = Depends(get_db)
):
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
            "stripe_payment_intent_id": payment.stripe_payment_intent_id
        }
    }

@router.get("/membership/{member_id}")
def get_membership(member_id: int, db: Session = Depends(get_db)):
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
def get_payment_history(member_id: int, db: Session = Depends(get_db)):
    payments = db.query(models.Payment).filter(
        models.Payment.member_id == member_id
    ).all()
    
    return [
        {
            "id": p.id,
            "amount": p.amount / 100,
            "currency": p.currency,
            "status": p.status,
            "created_at": p.created_at
        }
        for p in payments
    ]