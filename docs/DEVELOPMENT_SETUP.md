# Nuvie Development Environment Setup

This guide provides step-by-step instructions for setting up the Nuvie development environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Backend Setup](#backend-setup)
4. [AI Service Setup](#ai-service-setup)
5. [iOS App Setup](#ios-app-setup)
6. [Running with Docker](#running-with-docker)
7. [Environment Variables](#environment-variables)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|-----------------|---------|
| Python | 3.9+ | Backend API & AI Service |
| PostgreSQL | 15+ | Primary database |
| Redis | 7+ | Caching & rate limiting |
| Xcode | 15+ | iOS development |
| Node.js | 18+ | Tooling & scripts |
| Docker | 24+ | Containerization (optional) |
| Git | 2.40+ | Version control |

### Verify Installations

```bash
# Check Python
python3 --version  # Should be 3.9+

# Check PostgreSQL
psql --version  # Should be 15+

# Check Redis
redis-cli --version  # Should be 7+

# Check Docker (optional)
docker --version  # Should be 24+
```

---

## Quick Start

For the impatient, here's how to get everything running in 5 minutes:

```bash
# 1. Clone repository
git clone https://github.com/bestfriendai/Nuvie.git
cd Nuvie

# 2. Copy environment template
cp infra/env.example .env

# 3. Generate JWT secret
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env

# 4. Start with Docker Compose
docker-compose up -d

# 5. Access the API
curl http://localhost:8000/health
```

---

## Backend Setup

### 1. Create Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip
```

### 2. Install Dependencies

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Copy the example file
cp infra/env.example .env
```

Edit `.env` with your configuration:

```bash
# Required Settings
JWT_SECRET=your-secret-key-at-least-32-characters-long
DATABASE_URL=postgresql://nuvie:nuvie_password@localhost:5432/nuvie

# Optional Settings
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
REDIS_URL=redis://localhost:6379/0
AI_BASE_URL=http://localhost:9000
```

### 4. Set Up Database

```bash
# Create database
createdb nuvie

# Or using psql
psql -c "CREATE DATABASE nuvie;"

# Run migrations (when available)
# alembic upgrade head
```

### 5. Start Backend Server

```bash
# Development mode with auto-reload
uvicorn backend.app.main:app --reload --port 8000

# Production mode
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Verify Backend

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"...","version":"1.0.0"}

# API documentation (development only)
open http://localhost:8000/docs
```

---

## AI Service Setup

### 1. Prepare Data

```bash
# Download and prepare MovieLens data
python aii/data/load_movielens_data.py

# Run feature pipeline
python aii/features/feature_pipeline.py
```

### 2. Train Model (Optional)

```bash
# Train IBCF model
python aii/models/train_ibcf.py

# Evaluate model
python aii/models/evaluate.py
```

### 3. Start AI Service

```bash
# Development mode
uvicorn aii.serving.app:app --reload --port 9000

# Production mode
uvicorn aii.serving.app:app --host 0.0.0.0 --port 9000 --workers 2
```

### 4. Verify AI Service

```bash
# Health check
curl http://localhost:9000/health

# Test recommendation
curl -X POST http://localhost:9000/ai/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "limit": 5}'
```

---

## iOS App Setup

### 1. Open Xcode Project

```bash
# Open in Xcode
open Nuvie.xcodeproj
```

### 2. Configure API Endpoint

Create `Nuvie/Resources/Config-Debug.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>API_BASE_URL</key>
    <string>http://localhost:8000</string>
    <key>TMDB_API_KEY</key>
    <string>your-tmdb-api-key</string>
</dict>
</plist>
```

> **Important:** Add `Config-Debug.plist` to `.gitignore` to keep secrets safe.

### 3. Build and Run

1. Select the `Nuvie` scheme
2. Choose a simulator (iPhone 15 recommended)
3. Press `Cmd + R` to build and run

### 4. Run Tests

```bash
# From command line
xcodebuild test \
  -project Nuvie.xcodeproj \
  -scheme Nuvie \
  -destination 'platform=iOS Simulator,name=iPhone 15'

# Or press Cmd + U in Xcode
```

---

## Running with Docker

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Individual Services

```bash
# Backend only
docker build -t nuvie-backend backend/
docker run -p 8000:8000 --env-file .env nuvie-backend

# AI service only
docker build -t nuvie-ai aii/
docker run -p 9000:9000 nuvie-ai
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | Yes | - | JWT signing key (32+ chars) |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `ENVIRONMENT` | No | `development` | `development`, `staging`, `production` |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `AI_BASE_URL` | No | `http://localhost:9000` | AI service URL |
| `AI_INTERNAL_TOKEN` | No | - | Token for AI service auth |
| `RATE_LIMIT_DEFAULT` | No | `100/minute` | Default rate limit |
| `RATE_LIMIT_AUTH` | No | `5/minute` | Auth endpoint rate limit |

### AI Service (`aii/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MODEL_PATH` | No | `models/ibcf.pkl` | Path to trained model |
| `INTERNAL_TOKEN` | No | - | Expected auth token |
| `LOG_LEVEL` | No | `INFO` | Logging level |

---

## Troubleshooting

### Common Issues

#### 1. "JWT_SECRET environment variable is required"

```bash
# Generate a secure secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env file
echo "JWT_SECRET=<generated-secret>" >> .env
```

#### 2. Database connection failed

```bash
# Check PostgreSQL is running
pg_isready

# Check connection string format
# postgresql://user:password@host:port/database
```

#### 3. Redis connection failed

```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

#### 4. iOS build fails with signing errors

In Xcode:
1. Select your project in the navigator
2. Go to "Signing & Capabilities"
3. Check "Automatically manage signing"
4. Select your team

#### 5. Port already in use

```bash
# Find process using port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn backend.app.main:app --port 8001
```

### Getting Help

- **GitHub Issues:** [Report bugs](https://github.com/bestfriendai/Nuvie/issues)
- **Documentation:** Check the `docs/` folder
- **Architecture:** See `Architecture.md`

---

## Next Steps

1. Review the [Architecture Documentation](../Architecture.md)
2. Set up your IDE with recommended extensions
3. Run the test suite to verify setup
4. Create your first feature branch

Happy coding! 🎬
