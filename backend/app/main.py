from sqlalchemy import text
from backend.session import get_db
from sqlalchemy.orm import Session
from fastapi import Depends

from backend.session import engine, Base
from backend.models.user import User  # noqa: F401
from fastapi import FastAPI

from .feed import router as feed_router
from .auth import router as auth_router

app = FastAPI(title="Nuvie Backend API")
Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(feed_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/db/ping")
def db_ping(db: Session = Depends(get_db)):
    # 1) basit ping
    one = db.execute(text("SELECT 1")).scalar()

    # 2) users tablosu var mı?
    users_exists = db.execute(text("SELECT to_regclass('public.users')")).scalar()

    return {
        "select_1": one,
        "users_table": users_exists
    }


from backend.app.ai_router import router as ai_router

app.include_router(ai_router)

