# Nuvie Backend — Development Run Instructions

Quick steps to run the backend locally for development and testing.

Prereqs
- Python 3.10+ (container already prepared in dev environment)
- Install Python deps:

```bash
python3 -m pip install -r backend/requirements.txt
```

Create tables and seed sample data (sqlite fallback used when DATABASE_URL unset):

```bash
PYTHONPATH=. python3 backend/create_movies.py
```

Start the server (no reload, keeps process stable in dev container):

```bash
PYTHONPATH=. nohup uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 &
```

Health check:

```bash
curl -i http://127.0.0.1:8000/health
```

Auth / test user (seeded):
- email: `dev@example.com`
- password: `password`

Login to obtain token:

```bash
curl -sS -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"email": "dev@example.com", "password": "password"}'
```

Get feed (example):

```bash
TOKEN=$(curl -sS -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"email": "dev@example.com", "password": "password"}' | jq -r .access_token)
curl -i -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8000/feed/home?limit=5&offset=0"
```

Notes
- By default the app falls back to `sqlite:///./dev.db` when `DATABASE_URL` is not set.
- For production use a proper `DATABASE_URL` (Postgres/Neon) and remove sqlite fallback if desired.
