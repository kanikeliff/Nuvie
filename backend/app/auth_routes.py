from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import uuid
import os

from backend.models.user import User
from backend.session import get_db
from backend.app.auth_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set")

JWT_ALGO = "HS256"


# -----------------------
# REGISTER
# -----------------------
@router.post("/register")
def register(user_data: dict, db=Depends(get_db)):
    if "email" not in user_data or "password" not in user_data:
        raise HTTPException(status_code=400, detail="Email and password required")

    email = user_data["email"].lower().strip()
    password = user_data["password"].strip()

    # password byte-length check for bcrypt (max 72 bytes)
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password too long")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        hashed_password = hash_password(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Password validation error: {str(e)}")

    new_user = User(
        id=str(uuid.uuid4()),
        email=user_data["email"],
        password_hash=hashed_password,
    )

    db.add(new_user)
    db.commit()

    return {"message": "User registered successfully"}


# -----------------------
# LOGIN
# -----------------------
@router.post("/login")
def login(user_data: dict, db=Depends(get_db)):
    if "email" not in user_data or "password" not in user_data:
        raise HTTPException(status_code=400, detail="Email and password required")

    user = db.query(User).filter(User.email == user_data["email"]).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ✅ SADECE VERIFY (ASLA HASH YOK)
    if not verify_password(user_data["password"], user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {"sub": user.id},
        JWT_SECRET,
        algorithm=JWT_ALGO,
    )

    return {"access_token": token}


# -----------------------
# CURRENT USER (JWT)
# -----------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return {
        "id": user.id,
        "email": user.email,
    }
