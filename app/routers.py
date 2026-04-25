from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Member
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter()

COUNTRY_CODES = {
    "US": "+1", "CN": "+86", "DE": "+49", "JP": "+81",
    "IN": "+91", "GB": "+44", "FR": "+33", "BR": "+55",
    "IT": "+39", "CA": "+1", "KR": "+82", "RU": "+7",
    "AU": "+61", "ES": "+34", "MX": "+52", "ID": "+62",
    "NL": "+31", "SA": "+966", "TR": "+90", "CH": "+41"
}

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str
    country_code: str = "AU"

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/auth/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Member).filter(Member.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    country = req.country_code.upper()
    if country not in COUNTRY_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid country code '{req.country_code}'. Valid codes: {', '.join(COUNTRY_CODES.keys())}"
        )
full_phone = f"{COUNTRY_CODES[country]}-{req.phone}"

    full_phone = f"{COUNTRY_CODES[req.country_code]}-{req.phone}"

    member = Member(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        phone=full_phone
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"message": "Member registered successfully", "id": member.id}

@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.email == req.email).first()
    if not member or not verify_password(req.password, member.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(member.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "member_id": member.id,
        "full_name": member.full_name
    }