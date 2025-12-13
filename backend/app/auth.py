from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# I use Bearer auth because the mobile client will send a token in the header
security = HTTPBearer(auto_error=False)

def verify_token(token: str) -> bool:
    # Phase 2 note:
    # I'm keeping this intentionally simple.
    # If a token exists, we accept it. Real verification comes in Phase 3.
    return bool(token)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # I block access if the token is missing
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = credentials.credentials

    # I keep token verification lightweight for Phase 2
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    # I return a mock user for now (Phase 3 will decode real JWT claims)
    return {"id": "u1"}
