from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import traceback

from aii.serving.recommender import recommend_for_user, ai_status

router = APIRouter(prefix="/ai", tags=["ai"])


class RecommendIn(BaseModel):
    user_id: int
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


@router.get("/health")
def health():
    # ai_status() returns readiness/details; keep this endpoint public
    return {"ok": True, **ai_status()}


@router.post("/recommend")
def recommend(body: RecommendIn):
    try:
        items = recommend_for_user(
            user_id=body.user_id,
            limit=body.limit,
            offset=body.offset,
        )
        return {"user_id": body.user_id, "items": items}
    except Exception as e:
        tb = traceback.format_exc()
        # print to server logs for debugging
        print("[AI] recommend error:", repr(e))
        print(tb)
        # raise HTTPException with JSON detail so client always gets JSON
        raise HTTPException(status_code=500, detail={"error": repr(e), "trace": tb})
