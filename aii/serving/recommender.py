from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional

from aii.models.ibcf import IBCFRecommender, ModelConfig

# Simple module-level singleton
_lock = threading.Lock()
_model: Optional[IBCFRecommender] = None
_model_ready = False


def _load_model_once() -> None:
    global _model, _model_ready
    with _lock:
        if _model_ready:
            return

        try:
            cfg = ModelConfig()
        except Exception as e:
            print("[AI] Failed to import or create ModelConfig:", e)
            _model_ready = False
            return

        # If default cache directory isn't writable, fall back to /tmp
        try:
            if cfg.sims_cache:
                cache_dir = os.path.dirname(cfg.sims_cache)
                os.makedirs(cache_dir, exist_ok=True)
                test_path = os.path.join(cache_dir, ".ai_cache_test")
                with open(test_path, "w") as fh:
                    fh.write("ok")
                os.remove(test_path)
        except Exception:
            # fallback to /tmp
            cfg.sims_cache = os.path.join("/tmp", "ai_item_sims.npz")
            try:
                os.makedirs(os.path.dirname(cfg.sims_cache), exist_ok=True)
            except Exception:
                pass

        try:
            m = IBCFRecommender(cfg)
            # load() may raise; log details
            try:
                m.load()
            except Exception as e:
                print("[AI] IBCFRecommender.load() failed:", repr(e))
            # load_or_fit caches similarities; ensure it's invoked
            try:
                m.load_or_fit()
            except Exception as e:
                print("[AI] IBCFRecommender.load_or_fit() failed:", repr(e))

            _model = m
            _model_ready = True
            print("[AI] model loaded, sims_cache=", cfg.sims_cache)
        except Exception as e:
            print("[AI] Failed to initialize model:", repr(e))
            _model_ready = False


def recommend_for_user(
    user_id: Any,
    top_k: int = 20,
    offset: int = 0,
    exclude_movie_ids: Optional[List[int]] = None,
    use_social: bool = True,
    seed_movie_ids: Optional[List[int]] = None,
) -> List[Dict]:
    """Return a list of recommendation items (dicts). This normalizes output
    to include integer `movie_id` keys and protects against model not ready.
    """
    global _model_ready, _model
    # coerce user id to int when possible
    try:
        uid = int(user_id)
    except Exception:
        # if cannot cast, set sentinel and allow model to decide
        try:
            uid = int(str(user_id).split("-")[0])
        except Exception:
            uid = -1

    # ensure model loaded
    if not _model_ready or _model is None:
        _load_model_once()

    items: List[Dict] = []

    if not _model_ready or _model is None:
        # debug prints to help diagnosing on deployments
        print("[AI] user_id:", user_id)
        print("[AI] model ready:", _model_ready)
        print("[AI] items:", items)
        return []

    try:
        items = _model.recommend(
            user_id=uid,
            limit=top_k,
            offset=offset,
            exclude_movie_ids=exclude_movie_ids,
            use_social=use_social,
            seed_movie_ids=seed_movie_ids,
        )
    except Exception as e:
        print("[AI] recommend() raised:", repr(e))
        return []

    # Normalize items to ensure movie_id present as int
    normalized: List[Dict] = []
    for it in items or []:
        if isinstance(it, dict) and "movie_id" in it:
            try:
                it["movie_id"] = int(it["movie_id"])
            except Exception:
                try:
                    it["movie_id"] = int(str(it["movie_id"]).split("-")[0])
                except Exception:
                    continue
            normalized.append(it)
        else:
            # if it's just an id or tuple
            try:
                mid = int(it)
                normalized.append({"movie_id": mid})
            except Exception:
                continue

    return normalized


def ai_status() -> dict:
    """Return a small status dict for health endpoints."""
    return {"ready": bool(_model_ready)}
