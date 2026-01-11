"""
AI Recommender Wrapper for Backend Integration

Singleton pattern: Model loaded once, reused across all requests.
Lazy loading: Model loads on first request (not at import time).
"""
from __future__ import annotations

import os
import time
from typing import Optional, List, Dict

from aii.models.ibcf import IBCFRecommender, ModelConfig

# Render free için güvenli cache dizini (RAM değil disk)
CACHE_DIR = os.getenv("AI_CACHE_DIR", "/tmp/nuvie_ai_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Eğer model çok ağırsa istersen kapatabilmek için
AI_ENABLED = os.getenv("AI_ENABLED", "1") == "1"

_model: Optional[IBCFRecommender] = None
_model_ready: bool = False
_model_error: Optional[str] = None


def _load_model_once() -> None:
    """
    Modeli sadece 1 kere yükler.
    Import sırasında değil; ilk ihtiyaç olduğunda çalıştırmak daha güvenli.
    """
    global _model, _model_ready, _model_error

    if not AI_ENABLED:
        _model_ready = False
        _model_error = "AI_DISABLED"
        return

    if _model_ready and _model is not None:
        return

    try:
        t0 = time.time()

        cfg = ModelConfig()
        m = IBCFRecommender(cfg)

        # mevcut repo içindeki model load/fitting fonksiyonlarımız:
        # load(): diskten artefact varsa okur
        # load_or_fit(): yoksa fit eder, varsa cache okur
        m.load()
        m.load_or_fit()

        _model = m
        _model_ready = True
        _model_error = None

        print(f"[AI] Model ready in {int((time.time() - t0) * 1000)} ms")

    except Exception as e:
        _model = None
        _model_ready = False
        _model_error = repr(e)
        print("[AI] Model failed:", _model_error)


def ai_status() -> dict:
    """Return current AI service status."""
    return {
        "enabled": AI_ENABLED,
        "ready": _model_ready,
        "error": _model_error,
    }


def recommend_for_user(user_id: int, limit: int = 20, offset: int = 0) -> List[Dict]:
    """
    Backend burayı çağıracak.
    Dönüş: en az movie_id olacak.
    """
    _load_model_once()

    if not _model_ready or _model is None:
        # Backend fallback yapsın diye boş liste döndür
        return []

    items = _model.recommend(
        user_id=int(user_id),
        limit=int(limit),
        offset=int(offset),
        exclude_movie_ids=[],
        use_social=True,
        seed_movie_ids=[],
    )

    # items zaten dict list. Normalize edelim.
    # Beklenen minimum format:
    # [{"movie_id": 123, "ai_score": 87, "explanation": {...}}, ...]
    out: List[Dict] = []
    for it in items:
        # IBCF "score" döndürüyor, bunu ai_score'a çevirelim
        raw_score = it.get("score", 0.5)
        ai_score = int(round(raw_score * 100))  # 0-100 scale

        # Explanation'dan primary_reason'ı alalım
        explanation = it.get("explanation", {})
        if isinstance(explanation, dict):
            primary_reason = explanation.get("primary_reason", "ibcf")
        else:
            primary_reason = it.get("reason", "ibcf")

        out.append({
            "movie_id": int(it["movie_id"]),
            "ai_score": ai_score,
            "social_score": 0,  # TODO: Social features Phase 4
            "reason": primary_reason,
            "raw": it,  # debug için
        })
    return out

