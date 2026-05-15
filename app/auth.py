from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "fitlio-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
CHECKIN_QR_TOKEN_EXPIRE_MINUTES = 45

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_checkin_qr_token(member_id: int) -> tuple[str, datetime]:
    """Short-lived JWT for member phone QR; front desk scans into tablet check-in."""
    expire = datetime.utcnow() + timedelta(minutes=CHECKIN_QR_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(member_id),
        "typ": "checkin_qr",
        "exp": expire,
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_checkin_qr_token(token: str) -> int:
    from jose import JWTError

    raw = (token or "").strip()
    if len(raw) < 24:
        raise ValueError("invalid_token")
    try:
        payload = jwt.decode(raw, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise ValueError("invalid_token")
    if payload.get("typ") != "checkin_qr":
        raise ValueError("wrong_token_type")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("bad_subject")
