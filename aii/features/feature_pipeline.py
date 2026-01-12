from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd


# ============================================================
# Pipeline Configuration
# ============================================================
# This config defines where raw MovieLens files live
# and where processed CSV outputs will be written.
#
# IMPORTANT:
# - Output CSV schemas must NOT change (used by iOS & backend)
# ============================================================

@dataclass
class PipelineConfig:
    raw_movies_path: str = "aii/data/movies.dat"
    raw_ratings_path: str = "aii/data/ratings.dat"
    processed_dir: str = "aii/data/processed"

    movies_csv: Optional[str] = None
    ratings_csv: Optional[str] = None
    popular_csv: Optional[str] = None
    stats_json: Optional[str] = None

    def __post_init__(self) -> None:
        # Derive output paths automatically if not provided
        if self.movies_csv is None:
            self.movies_csv = os.path.join(self.processed_dir, "movies.csv")
        if self.ratings_csv is None:
            self.ratings_csv = os.path.join(self.processed_dir, "ratings.csv")
        if self.popular_csv is None:
            self.popular_csv = os.path.join(self.processed_dir, "popular_movies.csv")
        if self.stats_json is None:
            self.stats_json = os.path.join(self.processed_dir, "dataset_stats.json")


# ============================================================
# Helpers
# ============================================================

_YEAR_REGEX = re.compile(r"\((\d{4})\)\s*$")


def _ensure_dir(path: str) -> None:
    """Ensure output directory exists."""
    os.makedirs(path, exist_ok=True)


# ============================================================
# Load and clean MovieLens movies.dat
# ============================================================

def _read_movies_dat(path: str) -> pd.DataFrame:
    """
    MovieLens movies.dat format:
        movie_id::title (YEAR)::Genre1|Genre2|...

    Output schema (DO NOT CHANGE):
        movie_id, title, clean_title, year, genres_raw, genres

    Reason:
    - iOS and backend rely on this exact schema.
    """
    df = pd.read_csv(
        path,
        sep="::",
        engine="python",
        header=None,
        names=["movie_id", "title", "genres_raw"],
        encoding="latin-1",
    )

    # Type normalization
    df["movie_id"] = df["movie_id"].astype(int)
    df["title"] = df["title"].fillna("").astype(str)
    df["genres_raw"] = df["genres_raw"].fillna("").astype(str)

    # Extract year from title if present
    def parse_year(title: str) -> Optional[int]:
        match = _YEAR_REGEX.search(title)
        return int(match.group(1)) if match else None

    # Remove "(YEAR)" from title
    def strip_year(title: str) -> str:
        return _YEAR_REGEX.sub("", title).strip()

    df["year"] = df["title"].apply(parse_year)
    df["clean_title"] = df["title"].apply(strip_year)

    # Convert genres string into list (kept as-is when saved to CSV)
    df["genres"] = df["genres_raw"].apply(
        lambda s: [g for g in s.split("|") if g and g != "(no genres listed)"]
    )

    return df[
        ["movie_id", "title", "clean_title", "year", "genres_raw", "genres"]
    ]


# ============================================================
# Load and clean MovieLens ratings.dat
# ============================================================

def _read_ratings_dat(path: str) -> pd.DataFrame:
    """
    MovieLens ratings.dat format:
        user_id::movie_id::rating::timestamp

    Output schema (DO NOT CHANGE):
        user_id, movie_id, rating, timestamp
    """
    df = pd.read_csv(
        path,
        sep="::",
        engine="python",
        header=None,
        names=["user_id", "movie_id", "rating", "timestamp"],
    )

    # Type normalization
    df["user_id"] = df["user_id"].astype(int)
    df["movie_id"] = df["movie_id"].astype(int)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")

    return df


# ============================================================
# Main pipeline (Hands-On ML / Recommender textbook style)
# ============================================================

def run_pipeline(cfg: PipelineConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    End-to-end preprocessing pipeline:
      1. Load raw MovieLens data
      2. Clean and validate records
      3. Deduplicate ratings
      4. Export processed CSVs
      5. Build popularity table for cold-start users
    """

    _ensure_dir(cfg.processed_dir)

    # Load raw data
    movies = _read_movies_dat(cfg.raw_movies_path)
    ratings = _read_ratings_dat(cfg.raw_ratings_path)

    # Remove invalid ratings
    ratings = ratings.dropna(subset=["user_id", "movie_id", "rating"])
    ratings = ratings[(ratings["rating"] >= 0.5) & (ratings["rating"] <= 5.0)]

    # Keep ratings only for known movies
    ratings = ratings.merge(
        movies[["movie_id"]],
        on="movie_id",
        how="inner",
    )

    # Deduplicate ratings:
    # keep latest rating per (user, movie)
    ratings = ratings.sort_values(
        ["user_id", "movie_id", "timestamp"],
        ascending=True,
    )
    ratings = ratings.drop_duplicates(
        ["user_id", "movie_id"],
        keep="last",
    )

    # Save processed datasets (schema unchanged)
    movies.to_csv(cfg.movies_csv, index=False)
    ratings.to_csv(cfg.ratings_csv, index=False)

    # Popularity table for cold-start recommendation
    pop = (
        ratings.groupby("movie_id")
        .agg(
            rating_count=("rating", "size"),
            rating_avg=("rating", "mean"),
        )
        .reset_index()
        .sort_values(
            ["rating_count", "rating_avg"],
            ascending=[False, False],
        )
    )
    pop.to_csv(cfg.popular_csv, index=False)

    # Dataset statistics (for reporting / debugging)
    stats = {
        "movies": int(len(movies)),
        "ratings": int(len(ratings)),
        "users": int(ratings["user_id"].nunique()),
        "items": int(ratings["movie_id"].nunique()),
        "min_rating": float(ratings["rating"].min()),
        "max_rating": float(ratings["rating"].max()),
    }

    with open(cfg.stats_json, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[PIPELINE] wrote {cfg.movies_csv}")
    print(f"[PIPELINE] wrote {cfg.ratings_csv}")
    print(f"[PIPELINE] wrote {cfg.popular_csv}")
    print(f"[PIPELINE] wrote {cfg.stats_json}")

    return movies, ratings


if __name__ == "__main__":
    run_pipeline(PipelineConfig())
