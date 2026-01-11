from fastapi import FastAPI
from .feed import router as feed_router
from .auth import get_current_user

app = FastAPI(title="NUVIE Backend API")

# Include routers
app.include_router(feed_router, prefix="/feed", tags=["feed"])

@app.get("/health")
def health():
    return {"status": "ok"}
