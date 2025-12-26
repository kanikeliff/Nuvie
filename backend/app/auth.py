"""
Authentication module for Nuvie Backend API.

SECURITY IMPROVEMENTS:
- JWT_SECRET now fails fast if not configured (no insecure fallback)
- Added minimum secret length validation (32 characters)
- Added proper type annotations
- Enhanced password validation (min 8 chars with letters and numbers)
- Uses timezone-aware datetime
- Generic error messages to prevent user enumeration
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Final

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.session import get_db

from .auth_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)

# -----------------------
# Security Configuration
# -----------------------
JWT_SECRET: Final[str] = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
    )
if len(JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET must be at least 32 characters for security. "
        'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
    )

JWT_ALGO: Final[str] = "HS256"
JWT_EXPIRES_MINUTES: Final[int] = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))


# -----------------------
# Schemas (Pydantic v2)
# -----------------------
class AuthIn(BaseModel):
    """Authentication input schema with validation."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit: 72 bytes

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password has minimum complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain both letters and numbers")
        return v


class TokenOut(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRES_MINUTES * 60


class MessageOut(BaseModel):
    """Simple message response schema."""

    message: str


# -----------------------
# Routes
# -----------------------
@router.post("/register", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def register(user_data: AuthIn, db: Session = Depends(get_db)) -> MessageOut:
    """
    Register a new user account.

    - Validates email format and password strength
    - Hashes password with bcrypt before storage
    - Returns success message (no sensitive data in response)
    """
    # Check for existing user (case-insensitive email)
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Hash password and create user
    hashed_password = hash_password(user_data.password)

    new_user = User(
        id=str(uuid.uuid4()),
        email=user_data.email.lower(),
        password_hash=hashed_password,
    )

    db.add(new_user)
    db.commit()

    return MessageOut(message="User registered successfully")


@router.post("/login", response_model=TokenOut)
def login(user_data: AuthIn, db: Session = Depends(get_db)) -> TokenOut:
    """
    Authenticate user and return JWT token.

    - Validates credentials using constant-time comparison
    - Returns JWT with expiration claim
    - Generic error message to prevent user enumeration
    """
    user = db.query(User).filter(User.email == user_data.email.lower()).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp if model supports it
    if hasattr(user, "last_login_at"):
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

    # Generate token with expiration
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {"sub": str(user.id), "exp": exp, "iat": datetime.now(timezone.utc), "type": "access"}

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

    return TokenOut(access_token=token, token_type="bearer", expires_in=JWT_EXPIRES_MINUTES * 60)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """
    Dependency to get the current authenticated user from JWT token.

    - Validates token signature and expiration
    - Returns user dict with id and email
    - Raises 401 for any authentication failure
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"require_exp": True})
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active (if model supports it)
    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"id": str(user.id), "email": user.email}
