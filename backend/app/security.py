import os
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = "HS256"

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def hash_password(password: str) -> str:
    # backward-compatible alias
    return get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt only uses the first 72 bytes; passlib may raise for longer inputs.
    # Treat too-long passwords as a simple verification failure.
    if len(plain_password.encode("utf-8")) > 72:
        return False

    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(payload: dict, expires_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)

    to_encode = payload.copy()
    to_encode.update({"iat": int(now.timestamp()), "exp": int(exp.timestamp())})

    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as e:
        raise ValueError("Invalid token") from e
