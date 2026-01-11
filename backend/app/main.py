from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

from backend.session import engine, Base, get_db
from backend.models.user import User  # noqa: F401  (modeli import ederek Base'e kayıt ettiriyoruz)

from .auth import router as auth_router
from .feed import router as feed_router

# Eğer ai_router dosyan varsa (backend/app/ai_router.py)
try:
    from backend.app.ai_router import router as ai_router
    HAS_AI_ROUTER = True
except Exception:
    HAS_AI_ROUTER = False


app = FastAPI(title="Nuvie Backend API")

# ------------------------------------
# OPTIONAL: Auto-create tables
# (DB’de tablo zaten varsa değiştirmez)
# ------------------------------------
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"
if AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)

# ------------------------------------
# Routers
# ------------------------------------
app.include_router(auth_router)
app.include_router(feed_router)

if HAS_AI_ROUTER:
    app.include_router(ai_router)


# ------------------------------------
# Health & Root
# ------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "nuvie-backend"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ------------------------------------
# DB Ping (debug)
# ------------------------------------
@app.get("/db/ping")
def db_ping(db: Session = Depends(get_db)):
    one = db.execute(text("SELECT 1")).scalar()
    users_exists = db.execute(text("SELECT to_regclass('public.users')")).scalar()
    return {
        "select_1": one,
        "users_table": users_exists,
    }
