from passlib.context import CryptContext

# I create a password hashing context
# bcrypt is a safe default hashing algorithm for passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# I hash a plain text password before storing it
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# I verify a plain password against the stored hash
def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
