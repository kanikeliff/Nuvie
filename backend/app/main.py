# backend/app/main.py
import logging
import traceback
from backend.models.movie import Movie  # noqa

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

from backend.session import engine, Base, get_db
from backend.models.user import User  # noqa: F401

from backend.app.auth import router as auth_router
from backend.app.feed import router as feed_router
from backend.app.ai_router import router as ai_router  # sende varsa

app = FastAPI(title="Nuvie Backend API")

# tables
Base.metadata.create_all(bind=engine)

# routers
app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(ai_router)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db/ping")
def db_ping(db: Session = Depends(get_db)):
    one = db.execute(text("SELECT 1")).scalar()
    return {"select_1": one}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(tb)
    logging.exception("Unhandled exception in application")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
