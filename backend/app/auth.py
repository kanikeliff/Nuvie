import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.session import get_db
from backend.models.user import User
from backend.app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

from backend.app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=True)

def demo_mode_on() -> bool:
    v = os.getenv("DEMO_MODE", "").strip().lower()
    return v in {"1", "true", "yes", "on"}

@router.post("/register", response_model=UserPublic)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # DEMO kapalı olmalı
    if demo_mode_on():
        return {"id": "demo-user-123", "email": str(req.email)}

    email = str(req.email).lower().strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "email": user.email}

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if demo_mode_on():
        token = create_access_token({"sub": "demo-user-123"})
        return {"access_token": token, "token_type": "bearer"}

    email = str(req.email).lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    exp_min = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    token = create_access_token({"sub": user.id}, expires_minutes=exp_min)
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    token = creds.credentials
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
