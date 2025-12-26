# 🏗️ Nuvie Codebase Improvement Blueprint

> **Generated:** December 2025
> **Platform Detected:** Full-Stack (FastAPI Backend + iOS Swift App + Python ML Service)
> **App Category:** AI-Powered Social Movie Recommendation Platform
> **Current Phase:** Phase 3 (End-to-End Integration)
> **Health Score:** 52/100

---

## 📋 Executive Summary

Nuvie is an ambitious AI-powered social movie recommendation platform with a well-architected multi-tier design consisting of a FastAPI backend, a Python ML service (IBCF-based), and a native iOS app built with SwiftUI. The codebase demonstrates solid foundational decisions including MVVM architecture on iOS, dependency injection patterns in Python, and separation of concerns between services.

**Key Strengths:**
- Clean separation between backend API, AI service, and mobile client
- Proper use of bcrypt for password hashing
- SwiftUI/MVVM architecture on iOS with Keychain token storage
- Well-documented architecture with clear phase-based development roadmap

**Critical Concerns:**
1. **P0 Security Issues:** API key hardcoded in source code, JWT secret fallback to insecure default, missing rate limiting
2. **P0 Code Quality:** Duplicate authentication modules (`auth.py` vs `auth_routes.py`), function signature mismatch in `ai_client.py`
3. **P1 Missing Features:** No input validation/rate limiting on backend, no CORS configuration, unpinned dependencies
4. **P1 iOS Issues:** Force-unwrap in URL construction, missing error handling in async flows, API key stored in UserDefaults

This report provides a comprehensive roadmap to transform Nuvie into a production-ready, secure, and scalable application.

---

## 🚨 Critical Issues (P0 - Fix Before Deploy)

### 1. HARDCODED API KEY IN SOURCE CODE

**File:** `Nuvie/NuvieApp.swift:15`

```swift
// ❌ CRITICAL: API key committed to source code
init() {
    UserDefaults.standard.set("503275072513d5e4766ffe7caa7300a7", forKey: "api_key")
}
```

**Impact:** API key exposed in version control, can be extracted from compiled app, violates security best practices.

**Fix:**

```swift
// ✅ AFTER: Use environment configuration or secure storage
import Foundation

@main
struct NuvieApp: App {
    @StateObject private var feedViewModel = FeedViewModel()

    init() {
        // API keys should be:
        // 1. Loaded from Info.plist (for non-sensitive keys)
        // 2. Fetched from secure backend after authentication
        // 3. Never stored in UserDefaults for sensitive keys

        #if DEBUG
        // Only for development - use configuration file
        if let path = Bundle.main.path(forResource: "Config-Debug", ofType: "plist"),
           let config = NSDictionary(contentsOfFile: path),
           let apiKey = config["API_KEY"] as? String {
            TokenStore.shared.saveAPIKey(apiKey)
        }
        #endif
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(feedViewModel)
        }
    }
}
```

**Additional Steps:**
1. Rotate the exposed API key immediately
2. Add `Config-Debug.plist` to `.gitignore`
3. Use Keychain for any API keys that must be stored locally

---

### 2. JWT SECRET FALLBACK TO INSECURE DEFAULT

**File:** `backend/app/auth.py:19`

```python
# ❌ CRITICAL: Insecure default secret in production code
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
```

**Impact:** If `JWT_SECRET` env var is not set, all tokens are signed with a guessable secret, allowing token forgery.

**Fix:**

```python
# ✅ AFTER: Fail fast if secret not configured
import os
from typing import Final

JWT_SECRET: Final[str] = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET must be set and at least 32 characters. "
        "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

JWT_ALGO: Final[str] = "HS256"
JWT_EXPIRES_MINUTES: Final[int] = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))
```

**Note:** `auth_routes.py:15-17` correctly raises `RuntimeError` if `JWT_SECRET` is not set - this pattern should be adopted in `auth.py`.

---

### 3. DUPLICATE AUTHENTICATION MODULES

**Files:** `backend/app/auth.py` and `backend/app/auth_routes.py`

**Issue:** Two separate authentication implementations exist with different behaviors:

| Aspect | `auth.py` | `auth_routes.py` |
|--------|-----------|------------------|
| Input validation | Pydantic `AuthIn` model | Raw `dict` |
| JWT expiration | Includes `exp` claim | No expiration |
| JWT_SECRET | Falls back to "dev-secret" | Raises RuntimeError |
| Password length | Validates 1-72 chars | No validation |

**Impact:** Confusion about which module is active, potential security gaps, maintenance burden.

**Fix:** Delete `auth_routes.py` and ensure `auth.py` is the single source of truth. Update `main.py` import if needed.

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .feed import router as feed_router
from .auth import router as auth_router  # Ensure this imports from auth.py only

app = FastAPI(
    title="Nuvie Backend API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(feed_router)
```

---

### 4. FUNCTION SIGNATURE MISMATCH IN AI CLIENT

**File:** `backend/app/ai_client.py:6` vs `backend/app/feed.py:48-52`

```python
# ❌ ai_client.py - Missing 'offset' parameter
def get_ai_recommendations(user_id: str, limit: int):
    # ...

# ❌ feed.py - Calls with 'offset' parameter that doesn't exist
items = get_ai_recommendations(
    user_id=user_id,
    limit=limit,
    offset=offset  # This parameter is not accepted!
)
```

**Impact:** Runtime `TypeError` when calling the AI client, breaking the recommendation flow.

**Fix:**

```python
# ✅ backend/app/ai_client.py
import os
import uuid
from typing import List, Dict, Any, Optional
import requests
from requests.exceptions import RequestException

AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_INTERNAL_TOKEN = os.getenv("AI_INTERNAL_TOKEN", "")

class AIServiceError(Exception):
    """Custom exception for AI service failures."""
    pass

def get_ai_recommendations(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    exclude_movie_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch personalized recommendations from the AI service.

    Args:
        user_id: The user's ID
        limit: Maximum number of recommendations (1-50)
        offset: Pagination offset
        exclude_movie_ids: Movie IDs to exclude from results

    Returns:
        List of recommendation dictionaries

    Raises:
        AIServiceError: If the AI service is unavailable or returns an error
    """
    if not AI_BASE_URL:
        raise AIServiceError("AI_BASE_URL not configured")

    try:
        response = requests.post(
            f"{AI_BASE_URL}/ai/recommend",
            json={
                "request_id": str(uuid.uuid4()),
                "user_id": int(user_id) if user_id.isdigit() else 0,
                "limit": min(max(limit, 1), 50),
                "offset": max(offset, 0),
                "exclude_movie_ids": exclude_movie_ids or [],
                "context": {"use_social": True}
            },
            headers={"X-Internal-Token": AI_INTERNAL_TOKEN},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    except RequestException as e:
        raise AIServiceError(f"AI service unavailable: {e}") from e
```

---

### 5. INTERNAL TOKEN EXPOSED TO CLIENT

**File:** `Nuvie/Networks/APIClient.swift:26-27`

```swift
// ❌ CRITICAL: Internal AI token should never be sent from client
private let internalToken = "INTERNAL_AI_TOKEN"

var defaultHeaders: [String: String] {
    var headers: [String: String] = [
        "Content-Type": "application/json",
        "X-Internal-Token": internalToken  // Exposes internal auth mechanism
    ]
    // ...
}
```

**Impact:** The internal token is meant for backend-to-AI-service communication only. Exposing it to the iOS app creates a security vulnerability.

**Fix:**

```swift
// ✅ AFTER: Remove internal token from client
final class APIClient {
    static let shared = APIClient()
    private init() {}

    private var authToken: String? {
        TokenStore.shared.load()
    }

    var defaultHeaders: [String: String] {
        var headers: [String: String] = [
            "Content-Type": "application/json",
            "Accept": "application/json"
        ]

        if let token = authToken {
            headers["Authorization"] = "Bearer \(token)"
        }

        // API key should only be sent for specific endpoints if needed
        // and should be stored securely, not in UserDefaults

        return headers
    }
}
```

---

### 6. FORCE-UNWRAP URL CONSTRUCTION

**File:** `Nuvie/Networks/EndPoints.swift:36`

```swift
// ❌ CRASH RISK: Force unwrap can crash the app
func url(baseURL: String) -> URL {
    return URL(string: baseURL + path)!
}
```

**Impact:** If URL construction fails (special characters, encoding issues), app crashes.

**Fix:**

```swift
// ✅ AFTER: Safe URL construction with validation
extension Endpoint {
    func url(baseURL: String) throws -> URL {
        guard let url = URL(string: baseURL + path) else {
            throw URLError(.badURL)
        }
        return url
    }
}

// Update APIClient to handle:
func get<T: Decodable>(
    endpoint: Endpoint,
    responseType: T.Type
) async throws -> T {
    let url = try endpoint.url(baseURL: baseURL)  // Now throws instead of crashing
    // ...
}
```

---

## ⚠️ High Priority Issues (P1 - Fix This Sprint)

### 7. MISSING RATE LIMITING

**Files:** All backend route files

**Issue:** No rate limiting on authentication or API endpoints.

**Impact:** Vulnerable to brute force attacks, credential stuffing, and DoS.

**Fix:**

```python
# ✅ Add to backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ✅ Apply to auth routes in backend/app/auth.py
from slowapi import limiter

@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")  # 5 login attempts per minute
def login(request: Request, user_data: AuthIn, db: Session = Depends(get_db)):
    # ...

@router.post("/register")
@limiter.limit("3/hour")  # 3 registrations per hour per IP
def register(request: Request, user_data: AuthIn, db: Session = Depends(get_db)):
    # ...
```

Add to `backend/requirements.txt`:
```
slowapi>=0.1.9
```

---

### 8. UNPINNED DEPENDENCIES

**File:** `backend/requirements.txt`

```
# ❌ BEFORE: Unpinned versions - builds may break
fastapi
uvicorn
sqlalchemy
psycopg
python-jose[cryptography]
passlib[bcrypt]
requests
```

**Impact:** Reproducibility issues, potential security vulnerabilities from outdated packages, breaking changes.

**Fix:**

```
# ✅ AFTER: Pinned versions with security-focused package selection
fastapi>=0.109.0,<0.110.0
uvicorn[standard]>=0.27.0,<0.28.0
sqlalchemy>=2.0.25,<2.1.0
psycopg[binary]>=3.1.17,<3.2.0
python-jose[cryptography]>=3.3.0,<3.4.0
passlib[bcrypt]>=1.7.4,<1.8.0
httpx>=0.26.0,<0.27.0  # Replace requests with async-compatible httpx
pydantic>=2.5.0,<2.6.0
pydantic-settings>=2.1.0,<2.2.0
slowapi>=0.1.9,<0.2.0
python-multipart>=0.0.6,<0.1.0
```

---

### 9. MISSING INPUT VALIDATION IN FEED ENDPOINT

**File:** `backend/app/feed.py:32-38`

```python
# ❌ BEFORE: No validation on query parameters
@router.get("/home")
def home_feed(
    limit: int = 20,
    offset: int = 0,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
```

**Impact:** Client can request unlimited data, causing performance issues or database overload.

**Fix:**

```python
# ✅ AFTER: Validated parameters with Query
from fastapi import Query
from pydantic import BaseModel
from typing import List, Optional

class FeedItem(BaseModel):
    movie_id: int
    title: str
    year: Optional[int]
    poster_url: Optional[str]
    overview: Optional[str]
    release_date: Optional[str]
    reason_chips: List[str] = []

class FeedResponse(BaseModel):
    user_id: str
    items: List[FeedItem]
    next_offset: int
    source: str

@router.get("/home", response_model=FeedResponse)
def home_feed(
    limit: int = Query(default=20, ge=1, le=50, description="Number of items to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get personalized movie recommendations for the authenticated user.

    Returns AI-powered recommendations with fallback to database if AI service unavailable.
    """
    user_id = user["id"]
    # ... rest of implementation
```

---

### 10. JWT TOKENS WITHOUT EXPIRATION CHECK

**File:** `backend/app/auth_routes.py:65-69`

```python
# ❌ BEFORE: JWT without expiration
token = jwt.encode(
    {"sub": user.id},
    JWT_SECRET,
    algorithm=JWT_ALGO,
)
```

**Impact:** Tokens never expire, meaning stolen tokens remain valid indefinitely.

**Fix:** Already implemented correctly in `auth.py:67-68`. Delete `auth_routes.py` and use only `auth.py`.

```python
# ✅ CORRECT (from auth.py)
exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRES_MINUTES)
payload = {"sub": str(user.id), "exp": exp}
token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
```

---

### 11. USER MODEL MISSING ESSENTIAL FIELDS

**File:** `backend/models/user.py`

```python
# ❌ BEFORE: Minimal user model
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
```

**Impact:** Missing audit fields, no account status, no failed login tracking.

**Fix:**

```python
# ✅ AFTER: Production-ready user model
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.sql import func
from backend.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Security tracking
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"
```

---

### 12. MISSING CORS CONFIGURATION

**File:** `backend/app/main.py`

```python
# ❌ BEFORE: No CORS configuration
app = FastAPI(title="Nuvie Backend API")
```

**Impact:** Web clients cannot access the API due to CORS restrictions.

**Fix:**

```python
# ✅ AFTER: Proper CORS configuration
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Nuvie Backend API",
    version="1.0.0",
    description="Backend API for Nuvie movie recommendation platform",
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
```

---

## 🏛️ Architecture Improvements

### Current State

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   iOS App       │────▶│  Backend API    │────▶│   AI Service    │
│   (SwiftUI)     │     │   (FastAPI)     │     │   (FastAPI)     │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   PostgreSQL    │
                        └─────────────────┘
```

### Recommended State

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   iOS App       │────▶│  API Gateway    │────▶│   Backend API   │
│   (SwiftUI)     │     │  (Rate Limit)   │     │   (FastAPI)     │
└─────────────────┘     └────────┬────────┘     └────────┬────────┘
                                 │                       │
                                 │              ┌────────┴────────┐
                                 │              ▼                 ▼
                                 │     ┌─────────────┐   ┌─────────────┐
                                 │     │ AI Service  │   │   Redis     │
                                 │     │ (FastAPI)   │   │  (Cache)    │
                                 │     └─────────────┘   └─────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   PostgreSQL    │
                        │   (Primary)     │
                        └─────────────────┘
```

### Key Architectural Recommendations

1. **Add Redis Caching Layer** - Cache recommendations (5 min TTL) and movie metadata (1 hour TTL)
2. **Implement API Gateway** - Rate limiting, request validation, authentication at edge
3. **Add Health Check Endpoints** - Proper `/health` and `/ready` endpoints for orchestration
4. **Implement Circuit Breaker** - Prevent cascade failures when AI service is down
5. **Add Request Tracing** - Correlation IDs for debugging across services

---

## 📦 Dependency Updates

### Backend Dependencies

| Current | Recommended | Reason |
|---------|-------------|--------|
| `fastapi` (unpinned) | `fastapi>=0.109.0,<0.110.0` | Pin to specific version |
| `requests` | `httpx>=0.26.0` | Async support, better performance |
| (missing) | `slowapi>=0.1.9` | Rate limiting |
| (missing) | `redis>=5.0.0` | Caching layer |
| (missing) | `sentry-sdk[fastapi]>=1.39.0` | Error monitoring |

### iOS Dependencies

| Current | Recommended | Reason |
|---------|-------------|--------|
| URLSession (built-in) | Consider Alamofire 5.8+ | Better error handling, retry logic |
| (missing) | Kingfisher 7.0+ | Image caching and loading |
| (missing) | SwiftLint | Code quality |

---

## 🎨 UI/UX Enhancements

### iOS App Improvements

#### 1. Missing Loading State Transitions

**File:** `Nuvie/Views/FeedView.swift:39-43`

```swift
// ❌ BEFORE: Abrupt state changes
if viewModel.isLoading {
    FeedSkeletonView()
} else if viewModel.showError {
    ErrorStateView(onRetry: viewModel.loadFeed)
}
```

**Fix:**

```swift
// ✅ AFTER: Smooth transitions
ZStack {
    Color(hex: "0f172a")
        .ignoresSafeArea()

    if viewModel.isLoading {
        FeedSkeletonView()
            .transition(.opacity.combined(with: .scale(scale: 0.98)))
    } else if viewModel.showError {
        ErrorStateView(onRetry: viewModel.loadFeed)
            .transition(.opacity.combined(with: .move(edge: .bottom)))
    } else {
        ScrollView {
            // content
        }
        .transition(.opacity)
    }
}
.animation(.easeInOut(duration: 0.3), value: viewModel.isLoading)
.animation(.easeInOut(duration: 0.3), value: viewModel.showError)
```

#### 2. Accessibility Missing

**File:** `Nuvie/Views/MovieCard.swift`

```swift
// ❌ BEFORE: No accessibility labels
struct MovieCard: View {
    let movie: Recommendation
    // ...
}
```

**Fix:**

```swift
// ✅ AFTER: Full accessibility support
struct MovieCard: View {
    let movie: Recommendation
    let compact: Bool
    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // ... existing content
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint("Double tap to view movie details")
        .accessibilityAddTraits(.isButton)
    }

    private var accessibilityLabel: String {
        var label = movie.title
        if let year = movie.year {
            label += ", released in \(year)"
        }
        if let rating = movie.rating {
            label += ", rated \(String(format: "%.1f", rating)) out of 5"
        }
        if let aiScore = movie.ai_score {
            label += ", AI match \(aiScore) percent"
        }
        return label
    }
}
```

#### 3. Color System Not Using Design Tokens

**Multiple files use hardcoded hex colors**

```swift
// ❌ BEFORE: Hardcoded colors everywhere
Color(hex: "0f172a")
Color(hex: "f59e0b")
Color(hex: "94a3b8")
```

**Fix:**

```swift
// ✅ AFTER: Create a design system
// Nuvie/Design/Colors.swift
import SwiftUI

extension Color {
    struct Nuvie {
        // Background colors
        static let background = Color(hex: "0f172a")
        static let surface = Color(hex: "1e293b")
        static let surfaceElevated = Color(hex: "334155")

        // Brand colors
        static let primary = Color(hex: "f59e0b")
        static let primaryDark = Color(hex: "d97706")
        static let secondary = Color(hex: "3b82f6")

        // Semantic colors
        static let success = Color(hex: "10b981")
        static let error = Color(hex: "ef4444")
        static let warning = Color(hex: "f97316")

        // Text colors
        static let textPrimary = Color.white
        static let textSecondary = Color(hex: "94a3b8")
        static let textMuted = Color(hex: "64748b")
    }
}

// Usage:
Color.Nuvie.background
Color.Nuvie.primary
```

---

## ⚡ Performance Optimizations

### 1. iOS Image Loading Without Caching

**File:** `Nuvie/Views/MovieCard.swift:23-35`

```swift
// ❌ BEFORE: AsyncImage with no caching strategy
AsyncImage(url: URL(string: movie.poster_url ?? "")) { phase in
    switch phase {
    case .empty:
        PosterPlaceholder()
    case .success(let image):
        image.resizable().aspectRatio(contentMode: .fill)
    case .failure:
        PosterPlaceholder()
    }
}
```

**Impact:** Images redownloaded on every scroll, poor performance, data waste.

**Fix:** Implement proper image caching:

```swift
// ✅ AFTER: Using Kingfisher for caching (recommended)
// Or implement URLCache-based solution

import Kingfisher

struct CachedAsyncImage: View {
    let url: URL?

    var body: some View {
        KFImage(url)
            .placeholder { PosterPlaceholder() }
            .retry(maxCount: 2, interval: .seconds(1))
            .fade(duration: 0.25)
            .resizable()
            .aspectRatio(contentMode: .fill)
    }
}
```

### 2. Backend Database Queries Without Pagination Limits

**File:** `backend/app/feed.py:69-77`

```python
# ❌ BEFORE: No maximum limit enforcement
rows = db.execute(
    text("""
        SELECT movie_id, title, poster_url, overview, release_date
        FROM movies
        ORDER BY movie_id
        LIMIT :limit OFFSET :offset
    """),
    {"limit": limit, "offset": offset}
).mappings().all()
```

**Fix:**

```python
# ✅ AFTER: Enforce maximum limits and add timeout
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as SQLTimeoutError

MAX_LIMIT = 50
QUERY_TIMEOUT = 5  # seconds

@router.get("/home", response_model=FeedResponse)
def home_feed(
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0, le=10000),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rows = db.execute(
            text("""
                SELECT movie_id, title, poster_url, overview, release_date
                FROM movies
                ORDER BY movie_id
                LIMIT :limit OFFSET :offset
            """).execution_options(timeout=QUERY_TIMEOUT),
            {"limit": min(limit, MAX_LIMIT), "offset": offset}
        ).mappings().all()
    except SQLTimeoutError:
        raise HTTPException(status_code=504, detail="Database query timeout")
```

### 3. AI Model Loading on Every Request

**File:** `aii/serving/app.py:57-64`

The model is correctly loaded at startup, but consider adding:

```python
# ✅ Add warmup and health monitoring
import threading
import time

model_load_time: float = 0
model_last_used: float = 0

@app.on_event("startup")
def _startup():
    global model, model_load_time
    start = time.time()

    m = IBCFRecommender(ModelConfig())
    m.load()
    m.load_or_fit()

    model = m
    model_load_time = time.time() - start

    # Warmup - make a test prediction
    try:
        model.recommend(user_id=1, limit=1)
    except Exception:
        pass  # Warmup failure is ok

@app.get("/health")
def health():
    global model_last_used
    return {
        "ok": True,
        "model_loaded": model is not None,
        "model_load_time_seconds": round(model_load_time, 2),
        "last_used_seconds_ago": round(time.time() - model_last_used, 2) if model_last_used else None
    }
```

---

## 🔒 Security Hardening

### Security Checklist

| Check | Status | Priority |
|-------|--------|----------|
| API keys not in source code | ❌ Failed | P0 |
| JWT secret configured | ⚠️ Partial | P0 |
| Password hashing (bcrypt) | ✅ Pass | - |
| HTTPS enforcement | ❓ Unknown | P1 |
| Rate limiting | ❌ Missing | P1 |
| Input validation | ⚠️ Partial | P1 |
| CORS configuration | ❌ Missing | P1 |
| SQL injection protection | ✅ Pass (parameterized) | - |
| XSS protection | N/A (API only) | - |
| CSRF protection | ❌ Missing | P2 |
| Security headers | ❌ Missing | P2 |
| Token storage (iOS Keychain) | ✅ Pass | - |

### Recommended Security Headers

```python
# backend/app/main.py
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

# Add in production
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
```

---

## 🧪 Testing Strategy

### Current Coverage

| Component | Unit Tests | Integration Tests | E2E Tests |
|-----------|------------|-------------------|-----------|
| Backend API | ❌ None | ❌ None | ❌ None |
| AI Service | ✅ Smoke test | ❌ None | ❌ None |
| iOS App | ❌ None | ❌ None | ❌ None |

### Recommended Testing Structure

```
tests/
├── backend/
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_feed.py
│   │   └── test_ai_client.py
│   ├── integration/
│   │   ├── test_auth_flow.py
│   │   └── test_recommendation_flow.py
│   └── conftest.py
├── aii/
│   ├── test_ibcf.py (existing)
│   ├── test_reason_generator.py
│   └── test_serving.py
└── ios/
    ├── NuvieTests/
    │   ├── FeedViewModelTests.swift
    │   └── APIClientTests.swift
    └── NuvieUITests/
        └── FeedFlowTests.swift
```

### Example Backend Test

```python
# tests/backend/unit/test_auth.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.app.main import app
from backend.app.auth import hash_password

client = TestClient(app)

class TestRegistration:
    def test_register_success(self, mock_db):
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "securepassword123"
        })
        assert response.status_code == 200
        assert response.json()["message"] == "User registered successfully"

    def test_register_duplicate_email(self, mock_db_with_user):
        response = client.post("/auth/register", json={
            "email": "existing@example.com",
            "password": "securepassword123"
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_weak_password(self):
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": ""
        })
        assert response.status_code == 422

class TestLogin:
    def test_login_success(self, mock_db_with_user):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "correctpassword"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_invalid_credentials(self, mock_db_with_user):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
```

---

## 🚀 CI/CD Enhancements

### Current CI/CD

**File:** `.github/workflows/python-package.yml`

- ✅ Multi-Python version testing (3.9, 3.10, 3.11)
- ✅ Flake8 linting
- ✅ Pytest execution
- ❌ No coverage reporting
- ❌ No iOS builds
- ❌ No deployment pipeline
- ❌ No security scanning

### Recommended CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # Backend tests
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: nuvie_test
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r backend/requirements.txt
          pip install pytest-cov pytest-asyncio httpx

      - name: Run tests with coverage
        run: pytest --cov=backend --cov-report=xml
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost/nuvie_test
          JWT_SECRET: test-secret-minimum-32-characters-long

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  # Security scanning
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'

      - name: Run Bandit security linter
        run: |
          pip install bandit
          bandit -r backend/ aii/ -ll

  # iOS build
  ios-build:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4

      - name: Select Xcode version
        run: sudo xcode-select -s /Applications/Xcode_15.2.app

      - name: Build iOS app
        run: |
          xcodebuild -project Nuvie.xcodeproj \
            -scheme Nuvie \
            -destination 'platform=iOS Simulator,name=iPhone 15' \
            build

      - name: Run iOS tests
        run: |
          xcodebuild -project Nuvie.xcodeproj \
            -scheme Nuvie \
            -destination 'platform=iOS Simulator,name=iPhone 15' \
            test
```

---

## 📚 Documentation Gaps

### Missing Documentation

| Document | Status | Priority |
|----------|--------|----------|
| API documentation (OpenAPI) | ✅ Auto-generated | - |
| README.md | ✅ Exists | - |
| CONTRIBUTING.md | ✅ Exists | - |
| Architecture.md | ✅ Comprehensive | - |
| Database schema | ✅ Exists | - |
| **Environment setup guide** | ❌ Missing | P1 |
| **Deployment runbook** | ❌ Missing | P1 |
| **iOS developer guide** | ❌ Missing | P2 |
| **API versioning strategy** | ❌ Missing | P2 |
| **Incident response playbook** | ❌ Missing | P2 |

### Recommended: Environment Setup Guide

Create `docs/DEVELOPMENT_SETUP.md`:

```markdown
# Development Environment Setup

## Prerequisites

- Python 3.11+
- Node.js 18+ (for tooling)
- PostgreSQL 15+
- Redis 7+
- Xcode 15+ (for iOS development)

## Backend Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r backend/requirements.txt
   ```

3. Configure environment:
   ```bash
   cp infra/env.example .env
   # Edit .env with your values
   ```

4. Run database migrations:
   ```bash
   # TODO: Add migration tool (Alembic)
   ```

5. Start backend:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

## AI Service Setup

1. Prepare data:
   ```bash
   python aii/data/load_movielens_data.py
   python aii/features/feature_pipeline.py
   ```

2. Start AI service:
   ```bash
   uvicorn aii.serving.app:app --reload --port 9000
   ```

## iOS Setup

1. Open Xcode project:
   ```bash
   open Nuvie.xcodeproj
   ```

2. Configure scheme for development environment

3. Build and run on simulator
```

---

## ✅ Production Readiness Checklist

### Security
- [ ] **P0** Remove hardcoded API key from NuvieApp.swift
- [ ] **P0** Remove JWT secret fallback to "dev-secret"
- [ ] **P0** Delete duplicate auth_routes.py module
- [ ] **P0** Remove X-Internal-Token from iOS client
- [ ] **P1** Implement rate limiting
- [ ] **P1** Add CORS configuration
- [ ] **P1** Pin all dependency versions
- [ ] **P1** Add security headers middleware
- [ ] **P2** Set up Sentry for error monitoring
- [ ] **P2** Implement CSRF protection

### Performance
- [ ] **P1** Add Redis caching layer
- [ ] **P1** Implement image caching in iOS app
- [ ] **P2** Add database query timeouts
- [ ] **P2** Implement circuit breaker for AI service
- [ ] **P2** Add response compression

### Reliability
- [ ] **P0** Fix ai_client.py function signature
- [ ] **P1** Add error boundaries in iOS app
- [ ] **P1** Implement retry logic for network requests
- [ ] **P2** Add health check endpoints
- [ ] **P2** Implement graceful shutdown

### Testing
- [ ] **P1** Add backend unit tests (target: 80% coverage)
- [ ] **P1** Add iOS unit tests
- [ ] **P2** Add integration tests
- [ ] **P2** Add E2E tests with Playwright/XCUITest
- [ ] **P2** Add load testing

### DevOps
- [ ] **P1** Add coverage reporting to CI
- [ ] **P1** Add security scanning to CI
- [ ] **P2** Add iOS build to CI
- [ ] **P2** Create deployment pipeline
- [ ] **P2** Set up monitoring dashboards

### Documentation
- [ ] **P1** Create environment setup guide
- [ ] **P1** Create deployment runbook
- [ ] **P2** Document API versioning strategy
- [ ] **P2** Create incident response playbook

---

## 📊 Priority Matrix

```
                    IMPACT
                    High ──────────────────────────┐
                    │  P0 (Do Now)    │  P1        │
                    │  • API key      │  • Tests   │
                    │  • JWT secret   │  • Redis   │
                    │  • Duplicate    │  • Rate    │
                    │    auth files   │    limits  │
                    │  • ai_client    │  • CORS    │
                    │    signature    │            │
         URGENCY    ├─────────────────┼────────────┤
                    │  P2             │  P3        │
                    │  • Security     │  • Nice to │
                    │    headers      │    have    │
                    │  • E2E tests    │  • Future  │
                    │  • Monitoring   │    ideas   │
                    │                 │            │
                    Low ──────────────────────────┘
                        Low           High
                           EFFORT
```

---

## 🗓️ Implementation Roadmap

### Week 1: Critical Security Fixes (P0)
- Remove hardcoded API key
- Fix JWT secret fallback
- Delete duplicate auth module
- Fix ai_client function signature
- Remove internal token from iOS

### Week 2: High Priority Improvements (P1)
- Implement rate limiting
- Add CORS configuration
- Pin dependency versions
- Add input validation
- Begin test suite

### Week 3-4: Testing & Documentation
- Backend unit tests (80% coverage target)
- iOS unit tests
- Integration tests
- Environment setup documentation
- Deployment runbook

### Week 5-6: Performance & Monitoring
- Redis caching implementation
- Image caching in iOS
- Sentry error monitoring
- Health check improvements
- CI/CD pipeline enhancement

---

## 📚 Resources & References

### Official Documentation
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [SwiftUI](https://developer.apple.com/documentation/swiftui/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)

### Security Best Practices
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
- [OWASP Mobile Security](https://owasp.org/www-project-mobile-app-security/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)

### Python Best Practices
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [pytest Documentation](https://docs.pytest.org/)

### iOS Best Practices
- [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/)
- [Combine Framework](https://developer.apple.com/documentation/combine)
- [Keychain Services](https://developer.apple.com/documentation/security/keychain_services)

---

**Report Generated:** December 2025
**Next Review:** After P0 fixes are implemented
**Auditor:** Claude (Senior Staff Engineer)
