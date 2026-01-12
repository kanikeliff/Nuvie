from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class ModelConfig:
    processed_dir: str = "aii/data/processed"
    ratings_csv: Optional[str] = None
    movies_csv: Optional[str] = None
    popular_csv: Optional[str] = None

    min_user_history: int = 5
    max_k: int = 50

    # similarity build controls
    min_common_raters: int = 2
    topk_sim_per_item: int = 200

    def __post_init__(self) -> None:
        # derive CSV paths from processed_dir when not explicitly provided
        if not self.ratings_csv:
            self.ratings_csv = os.path.join(self.processed_dir, "ratings.csv")
        if not self.movies_csv:
            self.movies_csv = os.path.join(self.processed_dir, "movies.csv")
        if not self.popular_csv:
            self.popular_csv = os.path.join(self.processed_dir, "popular_movies.csv")


class IBCFRecommender:
    """
    Baseline Item-Based CF:
      - mean-center ratings per user
      - compute item-item cosine similarity using co-rating dot products
      - predict score(u,i) = sum_j sim(i,j)*r_u,j / sum_j |sim(i,j)|
    """

    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg

        self.ratings: Optional[pd.DataFrame] = None
        self.movies: Optional[pd.DataFrame] = None
        self.popular: Optional[pd.DataFrame] = None

        # user_id -> [(movie_id, rating), ...]
        self.user_hist: Dict[int, List[Tuple[int, float]]] = {}

        # movie_id -> [(other_movie_id, sim, common_raters), ...]
        self.item_sims: Dict[int, List[Tuple[int, float, int]]] = {}

        self.movie_title: Dict[int, str] = {}

    # -----------------------------
    # Data I/O
    # -----------------------------
    def load(self) -> None:
        """Load processed CSVs and build user history."""
        self.ratings = self._read_csv(self.cfg.ratings_csv, "ratings")
        self.movies = self._read_csv(self.cfg.movies_csv, "movies")
        self.popular = self._read_csv(self.cfg.popular_csv, "popular")

        self.movie_title = dict(
            zip(self.movies["movie_id"].astype(int), self.movies["title"].astype(str))
        )

        self.user_hist.clear()
        for r in self.ratings.itertuples(index=False):
            uid = int(r.user_id)
            mid = int(r.movie_id)
            rating = float(r.rating)
            self.user_hist.setdefault(uid, []).append((mid, rating))

    def _read_csv(self, path: str, name: str) -> pd.DataFrame:
        """Read a CSV with a helpful error message."""
        try:
            return pd.read_csv(path)
        except Exception as e:
            raise RuntimeError(f"Failed to read {name} CSV at '{path}': {e}")

    # -----------------------------
    # Training (similarity building)
    # -----------------------------
    def fit(self) -> None:
        """Build item-item similarity lists."""
        if self.ratings is None:
            raise RuntimeError("Call load() before fit().")

        df = self._mean_center_ratings(self.ratings)
        norm, dot, common = self._accumulate_pair_stats(df)
        self.item_sims = self._build_similarity_lists(norm, dot, common)

    def _mean_center_ratings(self, ratings: pd.DataFrame) -> pd.DataFrame:
        """Add mean-centered rating column r_c = rating - mean(user)."""
        df = ratings.copy()
        user_mean = df.groupby("user_id")["rating"].mean()
        df["r_c"] = df["rating"] - df["user_id"].map(user_mean).astype(float)
        return df

    def _accumulate_pair_stats(
        self, df: pd.DataFrame
    ) -> Tuple[Dict[int, float], Dict[Tuple[int, int], float], Dict[Tuple[int, int], int]]:
        """
        Accumulate:
          - norm[item] = sum r_c^2
          - dot[(i,j)] = sum r_ci * r_cj over common users
          - common[(i,j)] = number of common raters
        """
        norm: Dict[int, float] = {}
        dot: Dict[Tuple[int, int], float] = {}
        common: Dict[Tuple[int, int], int] = {}

        for _uid, g in df.groupby("user_id"):
            items = list(zip(g["movie_id"].astype(int), g["r_c"].astype(float)))

            # norms
            for i, rci in items:
                norm[i] = norm.get(i, 0.0) + rci * rci

            # pairwise dot + common
            n = len(items)
            for a in range(n):
                i, rci = items[a]
                for b in range(a + 1, n):
                    j, rcj = items[b]
                    if i == j:
                        continue
                    key = (i, j) if i < j else (j, i)
                    dot[key] = dot.get(key, 0.0) + (rci * rcj)
                    common[key] = common.get(key, 0) + 1

        return norm, dot, common

    def _build_similarity_lists(
        self,
        norm: Dict[int, float],
        dot: Dict[Tuple[int, int], float],
        common: Dict[Tuple[int, int], int],
    ) -> Dict[int, List[Tuple[int, float, int]]]:
        """Compute cosine similarities and keep top-k neighbors per item."""
        sims: Dict[int, List[Tuple[int, float, int]]] = {}

        for (i, j), d in dot.items():
            c = common.get((i, j), 0)
            if c < self.cfg.min_common_raters:
                continue

            ni, nj = norm.get(i, 0.0), norm.get(j, 0.0)
            if ni <= 0.0 or nj <= 0.0:
                continue

            sim = float(d / (np.sqrt(ni) * np.sqrt(nj)))
            if sim <= 0.0:
                continue

            sims.setdefault(i, []).append((j, sim, c))
            sims.setdefault(j, []).append((i, sim, c))

        out: Dict[int, List[Tuple[int, float, int]]] = {}
        for i, lst in sims.items():
            lst.sort(key=lambda x: x[1], reverse=True)
            out[i] = lst[: self.cfg.topk_sim_per_item]

        return out

    # -----------------------------
    # Recommendation
    # -----------------------------
    def recommend(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        exclude_movie_ids: Optional[List[int]] = None,
        use_social: bool = False,  # reserved for later
        seed_movie_ids: Optional[List[int]] = None,
    ) -> List[Dict]:
        """Return ranked recommendations in backend-friendly format."""
        if limit > self.cfg.max_k:
            limit = self.cfg.max_k

        exclude = set(exclude_movie_ids or [])
        hist = self.user_hist.get(int(user_id), [])
        seen = {mid for mid, _ in hist}

        # Optional: treat seed_movie_ids as additional "history" (useful for demo)
        if seed_movie_ids:
            for mid in seed_movie_ids:
                if mid not in seen:
                    hist.append((int(mid), 4.0))  # neutral-ish positive
                    seen.add(int(mid))

        # Cold start
        if len(hist) < self.cfg.min_user_history:
            return self._popular_fallback(limit=limit, offset=offset, exclude=exclude)

        window, best_seed = self._score_and_slice(hist, seen, exclude, limit, offset)

        if not window:
            return self._popular_fallback(limit=limit, offset=offset, exclude=exclude)

        return self._format_window(window, best_seed, offset)

    def _score_and_slice(
        self,
        hist: List[Tuple[int, float]],
        seen: set[int],
        exclude: set[int],
        limit: int,
        offset: int,
    ) -> Tuple[List[Tuple[int, float]], Dict[int, Tuple[int, float]]]:
        """Score candidates and return the requested page window."""
        num: Dict[int, float] = {}
        den: Dict[int, float] = {}
        best_seed: Dict[int, Tuple[int, float]] = {}  # item -> (seed_movie, best_contrib)

        for seed_mid, seed_r in hist:
            for other_mid, sim, _common in self.item_sims.get(seed_mid, []):
                if other_mid in seen or other_mid in exclude:
                    continue

                contrib = sim * seed_r
                num[other_mid] = num.get(other_mid, 0.0) + contrib
                den[other_mid] = den.get(other_mid, 0.0) + abs(sim)

                prev = best_seed.get(other_mid)
                if prev is None or contrib > prev[1]:
                    best_seed[other_mid] = (seed_mid, contrib)

        scored: List[Tuple[int, float]] = []
        for mid, n in num.items():
            d = den.get(mid, 1e-9)
            scored.append((mid, float(n / d)))

        scored.sort(key=lambda x: x[1], reverse=True)
        window = scored[offset : offset + limit]
        return window, best_seed

    def _format_window(
        self,
        window: List[Tuple[int, float]],
        best_seed: Dict[int, Tuple[int, float]],
        offset: int,
    ) -> List[Dict]:
        """Convert scored results to response objects (same schema as before)."""
        vals = [s for _, s in window]
        vmin, vmax = min(vals), max(vals)

        def to01(x: float) -> float:
            if vmax - vmin < 1e-9:
                return 0.5
            return (x - vmin) / (vmax - vmin)

        items: List[Dict] = []
        for idx, (mid, pred) in enumerate(window, start=1):
            seed_mid, _ = best_seed.get(mid, (None, 0.0))
            items.append(
                {
                    "movie_id": int(mid),
                    "score": float(to01(pred)),
                    "rank": int(offset + idx),
                    "explanation": {
                        "primary_reason": "because_you_rated",
                        "confidence": 0.75,
                        "factors": [
                            {
                                "type": "because_you_rated",
                                "weight": 1.0,
                                "value": 1,
                                "payload": {"seed_movie_ids": [int(seed_mid)] if seed_mid else []},
                                "description": "Recommended based on similar movies you rated",
                            }
                        ],
                    },
                }
            )
        return items

    # -----------------------------
    # Explain
    # -----------------------------
    def explain(self, user_id: int, movie_id: int) -> Dict:
        """Return a simple explanation payload (same behavior)."""
        hist = self.user_hist.get(int(user_id), [])

        if len(hist) < self.cfg.min_user_history:
            return {
                "movie_id": int(movie_id),
                "ai_score": 50,
                "explanation": {
                    "primary_reason": "popular",
                    "confidence": 0.6,
                    "factors": [
                        {
                            "type": "popular",
                            "weight": 1.0,
                            "value": 1,
                            "payload": {},
                            "description": "Recommended because it's popular among users",
                        }
                    ],
                },
                "social_signals": {
                    "friend_ratings_count": 0,
                    "friend_ratings_avg": None,
                    "friend_watch_count": 0,
                },
            }

        best = self._best_similar_seed(hist, movie_id)

        if best is None:
            payload = {"seed_movie_ids": [mid for mid, _ in hist[:2]]}
            desc = "Recommended based on your rating history"
            conf = 0.65
        else:
            payload = {"seed_movie_ids": [int(best[0])]}
            desc = "Recommended because you rated a similar movie"
            conf = 0.78

        return {
            "movie_id": int(movie_id),
            "ai_score": int(round(conf * 100)),
            "explanation": {
                "primary_reason": "because_you_rated",
                "confidence": float(conf),
                "factors": [
                    {
                        "type": "because_you_rated",
                        "weight": 1.0,
                        "value": 1,
                        "payload": payload,
                        "description": desc,
                    }
                ],
            },
            "social_signals": {
                "friend_ratings_count": 0,
                "friend_ratings_avg": None,
                "friend_watch_count": 0,
            },
        }

    def _best_similar_seed(
        self, hist: List[Tuple[int, float]], movie_id: int
    ) -> Optional[Tuple[int, float]]:
        """Find the strongest (seed_movie, similarity) link in the user's history."""
        best: Optional[Tuple[int, float]] = None
        target = int(movie_id)

        for seed_mid, _r in hist:
            for other_mid, sim, _c in self.item_sims.get(seed_mid, []):
                if int(other_mid) != target:
                    continue
                if best is None or sim > best[1]:
                    best = (seed_mid, float(sim))

        return best

    # -----------------------------
    # Popular fallback
    # -----------------------------
    def _popular_fallback(self, limit: int, offset: int, exclude: set[int]) -> List[Dict]:
        assert self.popular is not None

        rows = self.popular[~self.popular["movie_id"].isin(list(exclude))].iloc[offset : offset + limit]

        items: List[Dict] = []
        for idx, r in enumerate(rows.itertuples(index=False), start=1):
            items.append(
                {
                    "movie_id": int(r.movie_id),
                    "score": 0.5,  # neutral for cold-start
                    "rank": int(offset + idx),
                    "explanation": {
                        "primary_reason": "popular",
                        "confidence": 0.6,
                        "factors": [
                            {
                                "type": "popular",
                                "weight": 1.0,
                                "value": int(getattr(r, "rating_count", 1)),
                                "payload": {},
                                "description": "Recommended because it's popular",
                            }
                        ],
                    },
                }
            )
        return items
