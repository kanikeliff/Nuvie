from __future__ import annotations

import os
import threading
import time
import traceback
from typing import Dict, List, Optional

from aii.models.ibcf import IBCFRecommender, ModelConfig

# ----------------------------------------
# Config
# ----------------------------------------

AI_ENABLED = os.getenv("AI_ENABLED", "1") == "1"

# ----------------------------------------
# Singleton state
# ----------------------------------------

_lock = threading.Lock()
_model: Optional[IBCFRecommender] = None
_model_error: Optional[Dict[str, Optional[str]]] = None


def _load_model_once() -> None:
    """Load the recommender once (safe for repeated calls)."""
    global _model, _model_error

    if not AI_ENABLED:
        _model = None
        _model_error = {"message": "AI_DISABLED", "trace": None}
        return

    # Fast path
    if _model is not None:
        return

    with _lock:
        if _model is not None:
            return

        try:
            t0 = time.time()
            print("[AI] Loading model...")

            cfg = ModelConfig()
            model = IBCFRecommender(cfg)

            model.load()
            if hasattr(model, "load_or_fit"):
                model.load_or_fit()
            else:
                model.fit()

            _model = model
            _model_error = None

            ms = int((time.time() - t0) * 1000)
            print(f"[AI] Model loaded in {ms} ms")

        except Exception as e:
            _model = None
            _model_error = {"message": repr(e), "trace": traceback.format_exc()}
            print("[AI] Model failed to load:", _model_error["message"])
            print(_model_error["trace"])


def ai_status() -> Dict:
    return {
        "enabled": AI_ENABLED,
        "ready": _model is not None,
        "error": _model_error,
    }


def recommend_for_user(user_id: int, limit: int = 20, offset: int = 0) -> List[Dict]:
    _load_model_once()

    if _model is None:
        return []

    items = _model.recommend(
        user_id=int(user_id),
        limit=int(limit),
        offset=int(offset),
        exclude_movie_ids=[],
        use_social=True,
        seed_movie_ids=[],
    )

    out: List[Dict] = []
    for it in items:
        explanation = it.get("explanation") if isinstance(it.get("explanation"), dict) else {}

        out.append(
            {
                "movie_id": int(it["movie_id"]),
                "ai_score": int(it.get("ai_score", 50)),
                "social_score": int(it.get("social_score", 0)),
                "reason": str(explanation.get("primary_reason", it.get("reason", "ibcf"))),
            }
        )

    return out
