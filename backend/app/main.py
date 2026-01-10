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

