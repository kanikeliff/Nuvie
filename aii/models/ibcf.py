from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Explanation engine (safe import)
try:
    from aii.explanations.reason_generator import ReasonInput, generate_reason
except ModuleNotFoundError:
    ReasonInput = None  # type: ignore

    def generate_reason(*_args, **_kwargs):  # type: ignore
        return {
            "primary_reason": "because_you_rated",
            "confidence": 0.70,
            "text": "Recommended based on similar movies you rated.",
            "factors": [],
        }


# -----------------------------
# Configuration
# -----------------------------
@dataclass
class ModelConfig:
    processed_dir: str = "aii/data/processed"
    ratings_csv: Optional[str] = None
    movies_csv: Optional[str] = None
    popular_csv: Optional[str] = None
    sims_cache: Optional[str] = None

    min_user_history: int = 5
    max_k: int = 50

    min_common_raters: int = 2
    topk_sim_per_item: int = 200

    def __post_init__(self) -> None:
        if not self.ratings_csv:
            self.ratings_csv = os.path.join(self.processed_dir, "ratings.csv")
        if not self.movies_csv:
            self.movies_csv = os.path.join(self.processed_dir, "movies.csv")
        if not self.popular_csv:
            self.popular_csv = os.path.join(self.processed_dir, "popular_movies.csv")
        if not self.sims_cache:
            self.sims_cache = os.path.join(self.processed_dir, "item_sims.npz")


# -----------------------------
# Item-Based Collaborative Filtering
# -----------------------------
class IBCFRecommender:
    """
    Item-Based Collaborative Filtering (baseline):
      1) Mean-center ratings per user
      2) Compute item-item cosine similarity
      3) Predict with weighted sum of similar items
    """

    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg

        self.ratings: Optional[pd.DataFrame] = None
        self.movies: Optional[pd.DataFrame] = None
        self.popular: Optional[pd.DataFrame] = None

        self.user_hist: Dict[int, List[Tuple[int, float]]] = {}
        self.item_sims: Dict[int, List[Tuple[int, float, int]]] = {}

        self.movie_title: Dict[int, str] = {}
        self.movie_genres: Dict[int, set[str]] = {}

    # -----------------------------
    # Data loading
    # -----------------------------
    def load(self) -> None:
        self.ratings = pd.read_csv(self.cfg.ratings_csv)
        self.movies = pd.read_csv(self.cfg.movies_csv)
        self.popular = pd.read_csv(self.cfg.popular_csv)

        self.movie_title = dict(
            zip(self.movies["movie_id"].astype(int), self.movies["title"].astype(str))
        )

        def parse_genres(s: str) -> set[str]:
            if not isinstance(s, str):
                return set()
            return {g.strip().lower() for g in s.split("|") if g.strip()}

        if "genres" in self.movies.columns:
            self.movie_genres = dict(
                zip(
                    self.movies["movie_id"].astype(int),
                    self.movies["genres"].astype(str).map(parse_genres),
                )
            )

        self.user_hist.clear()
        for r in self.ratings.itertuples(index=False):
            self.user_hist.setdefault(int(r.user_id), []).append(
                (int(r.movie_id), float(r.rating))
            )

    # -----------------------------
    # Training
    # -----------------------------
    def load_or_fit(self) -> None:
        if self.cfg.sims_cache and os.path.exists(self.cfg.sims_cache):
            try:
                data = np.load(self.cfg.sims_cache, allow_pickle=True)
                self.item_sims = data["item_sims"].item()
                return
            except Exception:
                pass

        self.fit()

        try:
            np.savez_compressed(self.cfg.sims_cache, item_sims=self.item_sims)
        except Exception:
            pass

    def fit(self) -> None:
        df = self.ratings.copy()

        # Mean-centering (feature engineering)
        user_mean = df.groupby("user_id")["rating"].mean()
        df["r_c"] = df["rating"] - df["user_id"].map(user_mean)

        norm: Dict[int, float] = {}
        dot: Dict[Tuple[int, int], float] = {}
        common: Dict[Tuple[int, int], int] = {}

        for _, g in df.groupby("user_id"):
            items = list(zip(g["movie_id"], g["r_c"]))
            for i, rci in items:
                norm[i] = norm.get(i, 0.0) + rci * rci

            for a in range(len(items)):
                i, rci = items[a]
                for b in range(a + 1, len(items)):
                    j, rcj = items[b]
                    key = (i, j) if i < j else (j, i)
                    dot[key] = dot.get(key, 0.0) + rci * rcj
                    common[key] = common.get(key, 0) + 1

        sims: Dict[int, List[Tuple[int, float, int]]] = {}
        for (i, j), d in dot.items():
            if common[(i, j)] < self.cfg.min_common_raters:
                continue
            sim = d / (np.sqrt(norm[i]) * np.sqrt(norm[j]))
            if sim <= 0:
                continue
            sims.setdefault(i, []).append((j, sim, common[(i, j)]))
            sims.setdefault(j, []).append((i, sim, common[(i, j)]))

        self.item_sims = {
            i: sorted(v, key=lambda x: x[1], reverse=True)[: self.cfg.topk_sim_per_item]
            for i, v in sims.items()
        }

    # -----------------------------
    # Recommendation
    # -----------------------------
    def recommend(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        exclude_movie_ids: Optional[List[int]] = None,
        use_social: bool = False,
        seed_movie_ids: Optional[List[int]] = None,
    ) -> List[Dict]:
        exclude = set(exclude_movie_ids or [])
        hist = list(self.user_hist.get(int(user_id), []))
        seen = {m for m, _ in hist}

        if len(seen) < self.cfg.min_user_history:
            return self._popular_fallback(limit, offset, exclude)

        num: Dict[int, float] = {}
        den: Dict[int, float] = {}
        best_seed: Dict[int, int] = {}

        for seed_mid, seed_r in hist:
            for other_mid, sim, _ in self.item_sims.get(seed_mid, []):
                if other_mid in seen or other_mid in exclude:
                    continue
                num[other_mid] = num.get(other_mid, 0.0) + sim * seed_r
                den[other_mid] = den.get(other_mid, 0.0) + abs(sim)
                best_seed[other_mid] = seed_mid

        scored = [(m, num[m] / den[m]) for m in num]
        scored.sort(key=lambda x: x[1], reverse=True)
        window = scored[offset : offset + limit]

        if not window:
            return self._popular_fallback(limit, offset, exclude)

        vals = [s for _, s in window]
        vmin, vmax = min(vals), max(vals)

        def to01(x: float) -> float:
            return 0.5 if vmax == vmin else (x - vmin) / (vmax - vmin)

        out = []
        for i, (mid, score) in enumerate(window, start=1):
            reason = generate_reason() if ReasonInput is None else generate_reason(
                ReasonInput(
                    user_id=user_id,
                    rec_movie_id=mid,
                    seed_movie_id=best_seed.get(mid),
                    movie_title=self.movie_title,
                    movie_genres=self.movie_genres,
                    use_social=use_social,
                    friend_ids=None,
                )
            )
            out.append(
                {
                    "movie_id": mid,
                    "score": to01(score),
                    "rank": offset + i,
                    "explanation": reason,
                }
            )
        return out

    # -----------------------------
    # Popular fallback
    # -----------------------------
    def _popular_fallback(self, limit: int, offset: int, exclude: set[int]) -> List[Dict]:
        rows = self.popular[~self.popular["movie_id"].isin(list(exclude))]
        rows = rows.iloc[offset : offset + limit]

        return [
            {
                "movie_id": int(r.movie_id),
                "score": 0.5,
                "rank": offset + i + 1,
                "explanation": {
                    "primary_reason": "popular",
                    "confidence": 0.60,
                    "text": "Recommended because it's popular among users.",
                    "factors": [],
                },
            }
            for i, r in enumerate(rows.itertuples(index=False))
        ]
