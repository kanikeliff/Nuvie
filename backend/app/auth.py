# backend/app/auth.py (DEMO MODE)

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)

# JWT settings (demo-friendly)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALGO = "HS256"
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))

# Demo user defaults (you can change these)
DEMO_USER_ID = os.getenv("DEMO_USER_ID", "demo-user-123")
DEMO_USER_EMAIL = os.getenv("DEMO_USER_EMAIL", "demo@nuvie.app")


# -----------------------
# Schemas (Pydantic)
# -----------------------
class AuthIn(BaseModel):
    # NOTE: We keep "email" as plain str to avoid email-validator dependency issues in demo.
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -----------------------
# Routes (DEMO)
# -----------------------
@router.post("/register")
def register(user_data: AuthIn):
    """
    DEMO MODE:
    - No database write
    - Always returns success
    """
    return {
        "message": "✅ Demo register ok (DB disabled)",
        "user": {
            "id": DEMO_USER_ID,
            "email": user_data.email,
        },
    }


@router.post("/login", response_model=TokenOut)
def login(user_data: AuthIn):
    """
    DEMO MODE:
    - No DB check
    - Always returns a JWT with sub=DEMO_USER_ID
    """
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {
        "sub": DEMO_USER_ID,
        "email": user_data.email,
        "exp": exp,
        "demo": True,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    DEMO MODE:
    - If Authorization: Bearer <jwt> exists -> decode and return user from token
    - If no token -> return demo user anyway (so /feed/home works without login)
    """

    # If no token provided, allow demo user
    if credentials is None or not credentials.credentials:
        return {"id": DEMO_USER_ID, "email": DEMO_USER_EMAIL}

    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = payload.get("sub") or DEMO_USER_ID
        email = payload.get("email") or DEMO_USER_EMAIL
        return {"id": str(user_id), "email": str(email)}
    except JWTError:
        # In demo, you can either:
        # 1) reject invalid token, OR
        # 2) fallback to demo user.
        # I'll fallback to demo user to keep demo smooth.
        return {"id": DEMO_USER_ID, "email": DEMO_USER_EMAIL}
