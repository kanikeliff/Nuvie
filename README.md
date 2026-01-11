
# 🎬 NUVIE — AI Powered Social Movie Recommendation Platform

Nuvie is an AI-powered social movie recommendation platform that combines intelligent
personalization with real social interaction. Unlike traditional recommendation systems
that focus only on individual preferences, Nuvie integrates **friend activity, social feedback,
and machine learning** into one unified discovery experience.

Users can rate, review, and discuss movies with friends while receiving **dynamic,
friend-aware recommendations** powered by a hybrid AI model.

---

## 🚀 Core Features

- ✅ Hybrid Movie Recommendation System (IBCF + Genre Correlation + Neural CF)
- ✅ Friend-Aware & Socially Boosted Recommendations
- ✅ Real-Time Personalized Home Feed
- ✅ Explainable AI (Why this movie?)
- ✅ Native iOS Application (Swift)
- ✅ Scalable Backend with FastAPI
- ✅ Continuous Learning & Model Retraining

---

## 🧠 System Architecture

[iOS App (Swift)]
↓
[Backend API (FastAPI)]
↓
[AI Recommendation Service (FastAPI)]
↓
[PostgreSQL + Redis]


---


## 🗂 Repository Structure

nuvie/
├── ai/                        # 🤖 AI & Machine Learning Layer
│   ├── data/                  # Raw & processed datasets
│   ├── models/                # Recommendation algorithm implementations
│   ├── training/              # Model training pipelines
│   ├── evaluation/            # Offline evaluation metrics
│   ├── serving/               # AI API service (FastAPI)
│   └── explanations/          # Explainable AI logic
│
├── backend/                   # ⚙️ Backend API & Business Logic
│   ├── app/                   # FastAPI route definitions
│   ├── models/                # ORM models
│   ├── db/                    # Database connection & migrations
│   ├── schemas/               # Pydantic schemas
│   └── Dockerfile             # Backend container
│
├── ios/                       # 📱 Native iOS App (Swift)
│   └── NuvieApp/
│       ├── Views/             # UI screens
│       ├── ViewModels/        # MVVM logic
│       ├── Network/           # API & networking layer
│       ├── Models/            # Data models
│       └── Assets/            # Images, icons, colors
│
├── infra/                     # 🚀 DevOps & Deployment
│   ├── docker-compose.yml    # Local development orchestration
│   ├── github-actions.yml    # CI/CD pipeline
│   └── env.example           # Environment variables template
│
└── README.md                  # Project documentation




---

## 👥 Team & Responsibilities

| Name   | Role                         | Responsibilities |
|--------|------------------------------|------------------|
| Elif   | AI Engineer                  | Model training, inference, explainability, retraining |
| Berkay | Backend & DevOps Engineer   | API, authentication, infrastructure, CI/CD |
| Andaç  | Database & Data Engineer    | Schema design, data pipelines, feature tables |
| Öykü   | Mobile Frontend Developer  | UI/UX design, user flows |
| Can    | iOS Integration Developer  | Swift integration, API connectivity, notifications |

---

## 🧩 AI Technology Stack

- Python
- Scikit-learn
- PyTorch / TensorFlow
- Hybrid Recommender (Collaborative + Content + Social)
- Explainable AI Layer
- Continuous Retraining Pipelines

**Training Dataset:**
- MovieLens 1M / 10M
- TMDb Metadata

---

## 🛠 Backend & DevOps Stack

- FastAPI (Python)
- PostgreSQL (Neon)
- Redis (Upstash)
- Docker
- GitHub Actions (CI/CD)
- Sign in with Apple Authentication

---

## 📱 Mobile Stack

- Swift (Native iOS)
- MVVM Architecture
- REST API Integration
- Push Notifications
- Deep Linking

---

## 📋 Project Management & Task Tracking (Notion)

We actively use **Notion** for:
- Sprint planning
- Phase-based task tracking
- Team responsibilities
- Progress monitoring

---

## 🔄 Task-Based Development Roadmap

### Phase 1 — Foundation
- Repository setup
- Database schema
- API contracts

### Phase 2 — Data & Baseline
- MovieLens preprocessing
- IBCF baseline recommender
- Mock recommendation endpoints

### Phase 3 — Full Integration
- iOS → Backend → AI data flow
- Live recommendation feed

### Phase 4 — Social AI
- Friend-aware reranking
- Social explanations

### Phase 5 — Continuous Learning
- Feedback collection
- Automatic model retraining

---

## ✅ How to Run Locally (Development)

```bash
git clone https://github.com/your-username/nuvie.git
cd nuvie

# Setup environment
cp infra/env.example .env
# Edit .env with your DATABASE_URL and other settings

# Install dependencies
python -m pip install -r requirements.txt

# Setup database and load data
python setup_database.py

# Optional: Build processed dataset
python -m aii.features.feature_pipeline

# Run AI service
export AI_INTERNAL_TOKEN="dev-internal-token"
uvicorn aii.serving.app:app --reload --port 9000

# Run backend (in another terminal)
uvicorn backend.app.main:app --reload --port 8000
```

Backend will be available at:
http://localhost:8000/docs

AI Service will be available at:
http://localhost:9000/docs

Python dependencies
- Install runtime and test deps for the AI modules and local evaluation with:

```bash
python -m pip install -r requirements.txt
```
The minimal `requirements.txt` includes `pandas`, `numpy` and `pytest` used by data pipelines, models and smoke tests.

Optional ML dependencies
- For model training or larger ML workloads, install optional ML packages:

```bash
python -m pip install -r requirements-ml.txt
```
- `requirements-ml.txt` contains `scikit-learn`; for deep learning, install `torch` or `tensorflow` following their official guides.

PyTorch install notes
- PyTorch wheels depend on your OS and CUDA version. We recommend installing PyTorch with the official selector at https://pytorch.org/get-started/locally/.

Examples:

- CPU-only (cross-platform):

```bash
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

- CUDA 11.8 example (adjust for your CUDA version):

```bash
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Notes:
- If you have a GPU and need CUDA support, pick the appropriate wheel (the selector on the PyTorch site helps).
- TensorFlow is included in `requirements-ml.txt` pinned to a safe minor range; install with the same `pip` command above.

📊 Evaluation Metrics
RMSE
MAE
Recall@K
NDCG@K
Friend-Aware Engagement Rate

📜 License
This project is developed for academic and educational purposes.
All rights reserved by Team Nuvie.

