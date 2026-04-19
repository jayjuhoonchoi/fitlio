from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Member
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str = None

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/auth/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Member).filter(Member.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    member = Member(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        phone=req.phone
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
    return {"access_token": token, "token_type": "bearer"}
