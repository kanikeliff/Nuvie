#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "== Data checks =="
python - <<'PY'
import pandas as pd
r = pd.read_csv("aii/data/processed/ratings.csv")
m = pd.read_csv("aii/data/processed/movies.csv")
p = pd.read_csv("aii/data/processed/popular_movies.csv")
assert {"user_id","movie_id","rating"}.issubset(r.columns)
assert {"movie_id","title"}.issubset(m.columns)
assert {"movie_id"}.issubset(p.columns)
print("OK: CSV schema")
PY

echo "== Model smoke =="
python - <<'PY'
from aii.models.ibcf import IBCFRecommender, ModelConfig
cfg = ModelConfig(processed_dir="aii/data/processed")
m = IBCFRecommender(cfg)
m.load(); m.load_or_fit()
recs = m.recommend(user_id=1, limit=5)
assert len(recs)==5
print("OK: recommend")
cold = m.recommend(user_id=999999, limit=5)
assert all(x["explanation"]["primary_reason"]=="popular" for x in cold)
print("OK: cold-start")
PY

echo "== Offline eval =="
python -m aii.evaluation.offline_metrics --k 10 --sample-users 300
echo "OK: evaluation outputs in aii/evaluation/output/"
