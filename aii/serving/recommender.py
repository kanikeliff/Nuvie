from __future__ import annotations

import os
import threading
import traceback
from typing import Dict, List, Optional

from aii.models.ibcf import IBCFRecommender, ModelConfig

# Module-level singleton state
_lock = threading.Lock()
_model: Optional[IBCFRecommender] = None
_model_ready: bool = False
_model_error: Optional[Dict[str, Optional[str]]] = None


def _ai_enabled() -> bool:
    try:
        return bool(int(os.environ.get("AI_ENABLED", "1")))
    except Exception:
        return True


def _load_model_once() -> None:
    """Idempotent model loader. Safe to call from multiple places.

    Does not perform heavy work on import — only when first invoked.
    """
    global _model, _model_ready, _model_error
    with _lock:
        if _model_ready or _model is not None:
            return

        if not _ai_enabled():
            _model_ready = False
            _model_error = {"message": "AI_DISABLED", "trace": None}
            print("[AI] disabled via AI_ENABLED env")
            return

        try:
            cfg = ModelConfig()
        except Exception as e:
            tb = traceback.format_exc()
            _model_error = {"message": repr(e), "trace": tb}
            _model_ready = False
            print("[AI] ModelConfig creation failed:", repr(e))
            print(tb)
            return

        try:
            m = IBCFRecommender(cfg)
            try:
                m.load()
            except Exception as e:
                tb = traceback.format_exc()
                _model_error = {"message": repr(e), "trace": tb}
                print("[AI] IBCFRecommender.load() failed:", repr(e))
                print(tb)
            try:
                m.load_or_fit()
            except Exception as e:
                tb = traceback.format_exc()
                _model_error = {"message": repr(e), "trace": tb}
                print("[AI] IBCFRecommender.load_or_fit() failed:", repr(e))
                print(tb)

            _model = m
            _model_ready = True
            _model_error = None
            print("[AI] model loaded")
        except Exception as e:
            tb = traceback.format_exc()
            _model_error = {"message": repr(e), "trace": tb}
            _model_ready = False
            print("[AI] Failed to initialize model:", repr(e))
            print(tb)


def ai_status() -> Dict[str, Optional[object]]:
    """Return consistent health dict for the AI subsystem."""
    return {"enabled": _ai_enabled(), "ready": bool(_model_ready), "error": _model_error}


def recommend_for_user(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    exclude_movie_ids: Optional[List[int]] = None,
    use_social: bool = True,
    seed_movie_ids: Optional[List[int]] = None,
) -> List[Dict]:
    """Return normalized recommendation items.

    Ensures model is loaded lazily and never raises — callers get an empty list
    if the model isn't ready.
    """
    global _model_ready, _model, _model_error

    # ensure model is loaded (lazy)
    _load_model_once()

    if not _model_ready or _model is None:
        print("[AI] recommend called but model not ready; user_id=", user_id)
        return []

    try:
        raw_items = _model.recommend(
            user_id=user_id,
            limit=limit,
            offset=offset,
            exclude_movie_ids=exclude_movie_ids,
            use_social=use_social,
            seed_movie_ids=seed_movie_ids,
        )
    except Exception as e:
        tb = traceback.format_exc()
        _model_error = {"message": repr(e), "trace": tb}
        print("[AI] recommend() raised:", repr(e))
        print(tb)
        return []

    normalized: List[Dict] = []
    for it in raw_items or []:
        # Accept dicts or plain ids
        if isinstance(it, dict):
            movie_id = None
            try:
                movie_id = int(it.get("movie_id", it.get("id", None)))
            except Exception:
                continue
            ai_score = int(it.get("ai_score", it.get("score", 50)))
            social_score = int(it.get("social_score", it.get("social", 0)))
            reason = str(it.get("reason", ""))
        else:
            try:
                movie_id = int(it)
            except Exception:
                continue
            ai_score = 50
            social_score = 0
            reason = ""

        normalized.append(
            {"movie_id": movie_id, "ai_score": ai_score, "social_score": social_score, "reason": reason}
        )

    # apply exclude filter
    if exclude_movie_ids:
        excl = set(int(x) for x in exclude_movie_ids)
        normalized = [x for x in normalized if int(x["movie_id"]) not in excl]

    return normalized
