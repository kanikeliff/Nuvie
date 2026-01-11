from fastapi import APIRouter, Depends
from backend.app.auth import get_current_user
from aii.serving.app import recommend_for_user

router = APIRouter(prefix="/ai", tags=["ai"])

@router.get("/recommendations")
def get_recommendations(user=Depends(get_current_user)):
    user_id = user["id"]

    recs = recommend_for_user(user_id, top_k=10)

    return {
        "user_id": user_id,
        "recommendations": recs
    }
