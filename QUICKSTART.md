# QUICKSTART — Running the AI Pipeline Locally

Quick reference for developers working on the AI recommendation system.

## Prerequisites

Install dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-ml.txt  # Optional: ML packages
```

## 0. Setup Database

Create environment file and setup database:

```bash
cp infra/env.example .env
# Edit .env and set your DATABASE_URL (e.g., Neon PostgreSQL)
python setup_database.py
```

This will create all required tables (users, movies, ratings, watch_events, recommendation_feed) and load MovieLens data.

## 1. Build Processed Dataset

Run the feature pipeline to prepare MovieLens data:

```bash
python -m aii.features.feature_pipeline
```

Outputs CSVs to `aii/data/processed/`:
- `movies.csv`
- `ratings.csv`
- `popular_movies.csv`
- `dataset_stats.json`

## 2. Run Offline Evaluation

Evaluate the IBCF recommender on a train/test split:

```bash
python -m aii.evaluation.offline_metrics
```

Prints metrics: `rmse`, `mae`, `recall@k`, `ndcg@k`, `map@k`.

## 3. Run the Mock AI Service

Start the FastAPI AI service on port 9000:

```bash
export AI_INTERNAL_TOKEN="dev-internal-token"
uvicorn aii.serving.app:app --reload --port 9000
```

Visit http://localhost:9000/docs to explore the API.

## 4. Test the /ai/recommend Endpoint

```bash
curl -X POST "http://localhost:9000/ai/recommend" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: dev-internal-token" \
  -d '{
    "request_id":"uuid-1234",
    "user_id":1,
    "limit":20,
    "offset":0,
    "exclude_movie_ids":[10,20],
    "context":{
      "use_social":true,
      "seed_movie_ids":[1,2],
      "locale":"en-US",
      "time":"2025-12-13T10:30:00Z"
    }
  }'
```

## 5. Run Tests

Smoke test the IBCF recommender:

```bash
pytest -q tests/test_ibcf.py
```

## Troubleshooting

- **"No such file or directory" for CSVs**: Ensure you've run step 1 (feature pipeline) first.
- **Missing dependencies**: Run `pip install -r requirements.txt` and `pip install -r requirements-ml.txt`.
- **Port 9000 already in use**: Change `--port 9000` to another port, e.g., `--port 9001`.
- **X-Internal-Token validation fails**: Verify you're passing the correct token in the request header.

## Docker (Full Stack)

To run the entire stack (backend + AI service + database):

```bash
cp infra/env.example .env
docker-compose up --build
```

Backend: http://localhost:8000/docs
AI Service: http://localhost:9000/docs
