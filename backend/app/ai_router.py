from fastapi import APIRouter, Depends
from backend.app.auth import get_current_user
from aii.serving.recommender import recommend_for_user, _model_ready

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health")
def ai_status():
    return {"ready": bool(_model_ready)}


@router.post("/recommend")
def recommend_for_current_user(user=Depends(get_current_user)):
    user_id = user["id"]
    recs = recommend_for_user(user_id, top_k=10)
    return {"user_id": user_id, "recommendations": recs}
