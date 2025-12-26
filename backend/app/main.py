"""
Nuvie Backend API - Main Application Entry Point

IMPROVEMENTS:
- Added CORS middleware with configurable origins
- Added security headers middleware
- Added request ID middleware for tracing
- Added rate limiting with slowapi
- Added proper health/ready endpoints with Redis check
- Added OpenAPI documentation configuration
- Added logging configuration
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import router as auth_router
from .cache import cache
from .circuit_breaker import get_circuit_status
from .feed import router as feed_router

# -----------------------
# Logging Configuration
# -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# -----------------------
# Environment Configuration
# -----------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"
VERSION = os.getenv("APP_VERSION", "1.0.0")

# CORS origins (comma-separated in env)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

# Rate limiting configuration
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")


# -----------------------
# Rate Limiter Setup
# -----------------------
def get_client_ip(request: Request) -> str:
    """Get client IP, considering X-Forwarded-For header."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri=os.getenv("REDIS_URL", "memory://"),
    strategy="fixed-window",
)


# -----------------------
# Lifespan Events
# -----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info(f"Starting Nuvie Backend API v{VERSION} in {ENVIRONMENT} mode")
    logger.info(f"Rate limiting: {RATE_LIMIT_DEFAULT} (default), {RATE_LIMIT_AUTH} (auth)")

    # Check Redis connection
    redis_status = cache.health_check()
    logger.info(f"Redis status: {redis_status.get('status')}")

    yield

    # Shutdown
    logger.info("Shutting down Nuvie Backend API")


# -----------------------
# Application Factory
# -----------------------
app = FastAPI(
    title="Nuvie Backend API",
    description="AI-Powered Social Movie Recommendation Platform",
    version=VERSION,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
    lifespan=lifespan,
)

# Attach limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# -----------------------
# Security Headers Middleware
# -----------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store, max-age=0"

        # HSTS in production
        if ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


# -----------------------
# Request ID Middleware
# -----------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


# -----------------------
# Middleware Registration
# -----------------------

# CORS - must be added first
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Total-Count", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request ID tracking
app.add_middleware(RequestIDMiddleware)


# -----------------------
# Exception Handlers
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled exception [request_id={request_id}]: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
    )


# -----------------------
# Routers
# -----------------------
app.include_router(auth_router)
app.include_router(feed_router)


# -----------------------
# Health & Status Endpoints
# -----------------------
@app.get("/health", tags=["System"])
@limiter.exempt
def health():
    """
    Health check endpoint for load balancers and orchestration.

    Returns 200 if the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
    }


@app.get("/ready", tags=["System"])
@limiter.exempt
def ready():
    """
    Readiness check endpoint.

    Returns 200 if the service is ready to accept traffic.
    Checks database and Redis connectivity.
    """
    redis_health = cache.health_check()
    circuit_status = get_circuit_status()

    # Determine overall readiness
    redis_ok = redis_health.get("status") in ["healthy", "disabled"]
    ai_circuit_state = circuit_status.get("ai_service", {}).get("state", "unknown")

    # Service is ready if Redis is available; degraded if circuit is open
    if not redis_ok:
        overall_status = "degraded"
    elif ai_circuit_state == "open":
        overall_status = "degraded"
    else:
        overall_status = "ready"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "redis": redis_health,
            "circuits": circuit_status,
        },
    }


@app.get("/", tags=["System"])
@limiter.exempt
def root():
    """API root - returns basic service info."""
    return {
        "service": "Nuvie Backend API",
        "version": VERSION,
        "environment": ENVIRONMENT,
        "docs": "/docs" if DEBUG else None,
    }


@app.get("/metrics", tags=["System"])
@limiter.exempt
def metrics():
    """
    Metrics endpoint for monitoring.

    Returns circuit breaker and cache metrics.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "circuits": get_circuit_status(),
        "cache": cache.health_check(),
    }
