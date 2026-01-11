from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.session import engine, Base, get_db
from backend.models.user import User  # noqa: F401

from backend.app.auth import router as auth_router
from backend.app.feed import router as feed_router

app = FastAPI(title="Nuvie Backend API")


AUTO_CREATE_TABLES = (str(__import__("os").environ.get("AUTO_CREATE_TABLES", "0")) == "1")

if AUTO_CREATE_TABLES:
    # Sadece kendi SQLAlchemy modellerin (ör: User modelin) için geçerli.
    Base.metadata.create_all(bind=engine)


# Routers
app.include_router(auth_router)
app.include_router(feed_router)

# AI router opsiyonel (AI import hatası varsa backend yine de kalksın)
try:
    from backend.app.ai_router import router as ai_router
    app.include_router(ai_router)
except Exception as e:
    print("AI router disabled:", repr(e))


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
    movies_exists = db.execute(text("SELECT to_regclass('public.movies')")).scalar()
    ratings_exists = db.execute(text("SELECT to_regclass('public.ratings')")).scalar()

    return {
        "select_1": one,
        "users_table": users_exists,
        "movies_table": movies_exists,
        "ratings_table": ratings_exists,
    }
