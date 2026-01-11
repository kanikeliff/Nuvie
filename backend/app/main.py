from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

from backend.session import engine, Base, get_db
from backend.models.user import User  # noqa: F401

from backend.app.auth import router as auth_router
from backend.app.feed import router as feed_router
from backend.app.ai_router import router as ai_router  # varsa

app = FastAPI(title="Nuvie Backend API")

# tabloları oluştur
Base.metadata.create_all(bind=engine)

# routerlar
app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(ai_router)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/db/ping")
def db_ping(db: Session = Depends(get_db)):
    one = db.execute(text("SELECT 1")).scalar()
    users_exists = db.execute(text("SELECT to_regclass('public.users')")).scalar()
    return {"select_1": one, "users_table": users_exists}
