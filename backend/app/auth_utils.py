from passlib.hash import pbkdf2_sha256


# Use passlib's pbkdf2_sha256 hasher directly for consistent hash format
def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pbkdf2_sha256.verify(password, password_hash)
    except Exception:
        return False
