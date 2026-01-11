from __future__ import annotations

import os
import time
import threading
import traceback
from typing import Optional, Dict, List

from aii.models.ibcf import IBCFRecommender, ModelConfig

# ----------------------------------------
# Config
# ----------------------------------------

AI_ENABLED = os.getenv("AI_ENABLED", "1") == "1"
CACHE_DIR = os.getenv("AI_CACHE_DIR", "/tmp/nuvie_ai_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ----------------------------------------
# Singleton state
# ----------------------------------------

_lock = threading.Lock()
_model: Optional[IBCFRecommender] = None
_model_ready: bool = False
_model_error: Optional[Dict[str, str]] = None


# ----------------------------------------
# Internal: load model exactly once
# ----------------------------------------

def _load_model_once() -> None:
    global _model, _model_ready, _model_error

    if not AI_ENABLED:
        _model_ready = False
        _model_error = {"message": "AI_DISABLED", "trace": None}
        return

    # Fast path
    if _model_ready:
        return

    with _lock:
        # double-check inside lock
        if _model_ready:
            return

        try:
            t0 = time.time()
            print("[AI] Loading model...")

            cfg = ModelConfig()
            model = IBCFRecommender(cfg)

            # Use whichever your repo provides
            if hasattr(model, "load"):
                model.load()
            if hasattr(model, "load_or_fit"):
                model.load_or_fit()

            _model = model
            _model_ready = True
            _model_error = None

            print(f"[AI] Model loaded in {int((time.time() - t0) * 1000)} ms")

        except Exception as e:
            _model = None
            _model_ready = False
            _model_error = {
                "message": repr(e),
                "trace": traceback.format_exc(),
            }
            print("[AI] Model failed to load:", _model_error["message"])
            print(_model_error["trace"])


# ----------------------------------------
# Public API
# ----------------------------------------

def ai_status() -> dict:
    return {
        "enabled": AI_ENABLED,
        "ready": _model_ready,
        "error": _model_error,
    }


def recommend_for_user(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict]:

    _load_model_once()

    if not _model_ready or _model is None:
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
        out.append({
            "movie_id": int(it["movie_id"]),
            "ai_score": int(it.get("ai_score", 50)),
            "social_score": int(it.get("social_score", 0)),
            "reason": (
                (it.get("explanation") or {}).get("primary_reason")
                if isinstance(it.get("explanation"), dict)
                else it.get("reason", "ibcf")
            ),
        })

    return out
