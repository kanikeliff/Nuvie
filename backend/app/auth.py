import os
import uuid
import traceback
import logging
from typing import Any, Dict
from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.session import get_db
from backend.models.user import User
from backend.app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)

from backend.app.schemas import LoginRequest, TokenResponse, UserPublic


class RegisterIn(BaseModel):
    email: EmailStr
    password: str

print("AUTH.PY LOADED")

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=True)

def demo_mode_on() -> bool:
    v = os.getenv("DEMO_MODE", "").strip().lower()
    return v in {"1", "true", "yes", "on"}

@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        # DEMO kapalı olmalı
        if demo_mode_on():
            return {"ok": True, "email": str(body.email)}

        # validate/normalize
        email = str(body.email).lower().strip()
        pw = str(body.password).strip()

        # password byte-length check for bcrypt
        if len(pw.encode("utf-8")) > 72:
            raise HTTPException(status_code=400, detail="Password too long")
        if len(pw) < 6:
            raise HTTPException(status_code=400, detail="Password too short")

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            # user exists -> 409 with JSON detail
            raise HTTPException(status_code=409, detail={"error": "Email already registered"})

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=get_password_hash(pw),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {"ok": True, "email": user.email}
    except HTTPException:
        # re-raise HTTPExceptions as-is
        raise
    except Exception as e:  # pragma: no cover - global safety
        tb = traceback.format_exc()
        # print stacktrace for debugging and log it
        print(tb)
        logging.exception("Unhandled exception in register endpoint")
        # return a JSON-friendly 500
        raise HTTPException(status_code=500, detail={"error": repr(e)})

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
