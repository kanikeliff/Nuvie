# aii/evaluation/offline_metrics.py
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from aii.models.ibcf import IBCFRecommender, ModelConfig


@dataclass
class EvalResult:
    rmse: float
    rmse_n: int
    recall_at_k: float
    recall_users: int
    k: int
    test_rows: int
    used_rows_for_rmse: int
    skipped_rows_no_pred: int


def _train_test_split_last_per_user(
    ratings: pd.DataFrame,
    min_train_ratings: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Leave-one-out split per user using latest timestamp as test.
    Only users with >= min_train_ratings + 1 total ratings are kept.
    """
    df = ratings.copy()
    df["user_id"] = df["user_id"].astype(int)
    df["movie_id"] = df["movie_id"].astype(int)
    df["rating"] = df["rating"].astype(float)

    # We assume timestamp exists (MovieLens style). If not, it still works by stable sort.
    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].astype(int)
        df = df.sort_values(["user_id", "timestamp"], kind="mergesort")
    else:
        df = df.sort_values(["user_id"], kind="mergesort")

    # Keep only users with enough ratings to have a meaningful train set
    counts = df.groupby("user_id")["movie_id"].size()
    good_users = counts[counts >= (min_train_ratings + 1)].index
    df = df[df["user_id"].isin(good_users)]

    # Last rating per user as test
    last_idx = df.groupby("user_id").tail(1).index
    test_df = df.loc[last_idx].copy()
    train_df = df.drop(index=last_idx).copy()

    return train_df, test_df


def _build_user_hist_from_df(train_df: pd.DataFrame) -> Dict[int, List[Tuple[int, float]]]:
    hist: Dict[int, List[Tuple[int, float]]] = {}
    for r in train_df.itertuples(index=False):
        hist.setdefault(int(r.user_id), []).append((int(r.movie_id), float(r.rating)))
    return hist


def _predict_raw_rating(
    model: IBCFRecommender,
    user_id: int,
    target_movie_id: int,
) -> Optional[float]:
    """
    Predict raw score for (user, target_movie) using the SAME scoring rule as recommend():
      pred = sum_j sim(target, j) * r_u,j / sum_j |sim(target, j)|
    Implementation is evaluation-only (does not change backend/model code).
    """
    hist = model.user_hist.get(int(user_id), [])
    if not hist:
        return None

    num = 0.0
    den = 0.0
    tgt = int(target_movie_id)

    for seed_mid, seed_r in hist:
        # We have sims stored as: item_sims[seed_mid] = [(other_mid, sim, common), ...]
        # We need sim(seed_mid, target_movie) from this list.
        for other_mid, sim, _common in model.item_sims.get(int(seed_mid), []):
            if int(other_mid) == tgt:
                num += float(sim) * float(seed_r)
                den += abs(float(sim))
                break  # target found in this seed's neighbor list

    if den <= 1e-12:
        return None
    return float(num / den)


def evaluate_ibcf(
    cfg: ModelConfig,
    k: int = 10,
    seed: int = 42,
) -> EvalResult:
    """
    Offline evaluation:
      - Split ratings per user: last rating -> test, rest -> train
      - Fit IBCF on train
      - RMSE: compare raw predicted score vs true rating for test rows (when prediction possible)
      - Recall@K: run recommend(user) and see if test item appears in top-K
    """
    # 1) Load full data using the same config paths
    model = IBCFRecommender(cfg)
    model.load()  # loads ratings + movies + popular

    assert model.ratings is not None
    ratings = model.ratings

    # 2) Train-test split
    train_df, test_df = _train_test_split_last_per_user(
        ratings=ratings,
        min_train_ratings=cfg.min_user_history,
    )

    # 3) Override model's train data ONLY for evaluation (backend unchanged)
    model.ratings = train_df
    model.user_hist = _build_user_hist_from_df(train_df)

    # 4) Fit (or load cached) similarities on TRAIN set
    # For evaluation correctness, we should fit on the train_df.
    # Using load_or_fit() could load cache from a different dataset, so we call fit().
    model.fit()

    # 5) RMSE
    sq_err_sum = 0.0
    used_for_rmse = 0
    skipped_no_pred = 0

    for r in test_df.itertuples(index=False):
        uid = int(r.user_id)
        mid = int(r.movie_id)
        true = float(r.rating)

        pred = _predict_raw_rating(model, uid, mid)
        if pred is None:
            skipped_no_pred += 1
            continue

        sq_err_sum += (pred - true) ** 2
        used_for_rmse += 1

    rmse = float(np.sqrt(sq_err_sum / used_for_rmse)) if used_for_rmse > 0 else float("nan")

    # 6) Recall@K
    hits = 0
    users_count = 0

    # Evaluate only users present in test_df (each user exactly 1 test row here)
    for r in test_df.itertuples(index=False):
        uid = int(r.user_id)
        test_mid = int(r.movie_id)

        # Get top-K recs
        recs = model.recommend(
            user_id=uid,
            limit=int(k),
            offset=0,
            exclude_movie_ids=None,
            use_social=False,
            seed_movie_ids=None,
        )

        rec_ids = {int(x["movie_id"]) for x in recs}
        if test_mid in rec_ids:
            hits += 1
        users_count += 1

    recall_at_k = float(hits / users_count) if users_count > 0 else float("nan")

    return EvalResult(
        rmse=rmse,
        rmse_n=used_for_rmse,
        recall_at_k=recall_at_k,
        recall_users=users_count,
        k=int(k),
        test_rows=int(len(test_df)),
        used_rows_for_rmse=used_for_rmse,
        skipped_rows_no_pred=skipped_no_pred,
    )


def write_report(
    out_dir: str,
    cfg: ModelConfig,
    result: EvalResult,
) -> Tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    report_md = os.path.join(out_dir, "evaluation_report.md")
    report_json = os.path.join(out_dir, "evaluation_metrics.json")

    md = []
    md.append("# Offline Evaluation Report (IBCF)")
    md.append("")
    md.append(f"Generated: **{ts}**")
    md.append("")
    md.append("## Setup")
    md.append(f"- Ratings CSV: `{cfg.ratings_csv}`")
    md.append(f"- Movies CSV: `{cfg.movies_csv}`")
    md.append(f"- Popular CSV: `{cfg.popular_csv}`")
    md.append(f"- min_user_history: `{cfg.min_user_history}`")
    md.append("")
    md.append("## Split Method")
    md.append("- Leave-one-out per user: **last rating by timestamp** is the test example, rest is train.")
    md.append(f"- Only users with at least `{cfg.min_user_history + 1}` total ratings are included.")
    md.append("")
    md.append("## Metrics")
    md.append(f"- **RMSE**: `{result.rmse:.4f}` (computed on `{result.rmse_n}` test rows)")
    md.append(f"- **Recall@{result.k}**: `{result.recall_at_k:.4f}` (users: `{result.recall_users}`)")
    md.append("")
    md.append("## Notes")
    md.append(f"- Test rows total: `{result.test_rows}`")
    md.append(f"- RMSE skipped (no similarity path): `{result.skipped_rows_no_pred}`")
    md.append("")

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    payload = {
        "generated_utc": ts,
        "model": "IBCFRecommender",
        "split": "leave_one_out_last_timestamp",
        "k": result.k,
        "rmse": result.rmse,
        "rmse_n": result.rmse_n,
        "recall_at_k": result.recall_at_k,
        "recall_users": result.recall_users,
        "test_rows": result.test_rows,
        "used_rows_for_rmse": result.used_rows_for_rmse,
        "skipped_rows_no_pred": result.skipped_rows_no_pred,
        "config": {
            "processed_dir": cfg.processed_dir,
            "ratings_csv": cfg.ratings_csv,
            "movies_csv": cfg.movies_csv,
            "popular_csv": cfg.popular_csv,
            "min_user_history": cfg.min_user_history,
            "min_common_raters": cfg.min_common_raters,
            "topk_sim_per_item": cfg.topk_sim_per_item,
        },
    }

    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return report_md, report_json


def main() -> None:
    p = argparse.ArgumentParser(description="Offline evaluation for IBCF (RMSE + Recall@K)")
    p.add_argument("--processed-dir", default="aii/data/processed")
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--out-dir", default="aii/evaluation/output")
    args = p.parse_args()

    cfg = ModelConfig(processed_dir=args.processed_dir)
    result = evaluate_ibcf(cfg, k=args.k)

    md_path, json_path = write_report(args.out_dir, cfg, result)

    print("Done.")
    print(f"RMSE: {result.rmse:.4f} (n={result.rmse_n}, skipped={result.skipped_rows_no_pred})")
    print(f"Recall@{result.k}: {result.recall_at_k:.4f} (users={result.recall_users})")
    print(f"Report: {md_path}")
    print(f"Metrics: {json_path}")


if __name__ == "__main__":
    main()
