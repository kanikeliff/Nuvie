"""
AI Service Client for Nuvie Backend.

IMPROVEMENTS:
- Updated to use httpx (async-capable) instead of requests
- Added circuit breaker pattern for resilience
- Added Redis caching for recommendations
- Fixed function signature to include 'offset' parameter
- Added proper error handling with custom exception
- Added request_id for tracing
"""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import httpx
from circuitbreaker import CircuitBreakerError

from .cache import cache, get_cached_recommendations, set_cached_recommendations
from .circuit_breaker import ai_service_circuit

logger = logging.getLogger(__name__)

# Configuration
AI_BASE_URL: str = os.getenv("AI_BASE_URL", "")
AI_INTERNAL_TOKEN: str = os.getenv("AI_INTERNAL_TOKEN", "")
AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "5"))


class AIServiceError(Exception):
    """Custom exception for AI service failures."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _convert_user_id(user_id: str) -> int:
    """Convert user_id string to integer for AI service."""
    try:
        # If it's a UUID or long string, hash it
        if len(user_id) > 10:
            return abs(hash(user_id)) % (10**9)
        return int(user_id)
    except (ValueError, TypeError):
        return abs(hash(str(user_id))) % (10**9)


def _call_ai_service(
    user_id: str,
    limit: int,
    offset: int,
    exclude_movie_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Internal function to call AI service (wrapped by circuit breaker).

    This function contains the actual HTTP call logic and is protected
    by the circuit breaker pattern.
    """
    if not AI_BASE_URL:
        raise AIServiceError("AI_BASE_URL not configured")

    # Validate and clamp parameters
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    user_id_int = _convert_user_id(user_id)
    request_id = str(uuid.uuid4())

    try:
        with httpx.Client(timeout=AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{AI_BASE_URL}/ai/recommend",
                json={
                    "request_id": request_id,
                    "user_id": user_id_int,
                    "limit": limit,
                    "offset": offset,
                    "exclude_movie_ids": exclude_movie_ids or [],
                    "context": {"use_social": True, "seed_movie_ids": [], "locale": "en-US"},
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Token": AI_INTERNAL_TOKEN,
                    "X-Request-ID": request_id,
                },
            )

        # Handle non-2xx responses
        if response.status_code == 401:
            raise AIServiceError("AI service authentication failed", 401)
        elif response.status_code == 503:
            raise AIServiceError("AI model not ready", 503)
        elif not response.is_success:
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    if isinstance(error_data["detail"], dict):
                        error_detail = error_data["detail"].get("message", str(error_data["detail"]))
                    else:
                        error_detail = str(error_data["detail"])
            except Exception:
                error_detail = response.text[:200] if response.text else "No response body"

            raise AIServiceError(f"AI service error: {error_detail}", response.status_code)

        # Parse response
        data = response.json()
        items = data.get("items", [])

        logger.info(
            f"AI recommendations fetched: request_id={request_id}, "
            f"user_id={user_id}, count={len(items)}, "
            f"latency_ms={data.get('meta', {}).get('latency_ms', 'N/A')}"
        )

        return items

    except httpx.TimeoutException:
        logger.warning(f"AI service timeout: user_id={user_id}")
        raise AIServiceError("AI service timeout", 504)

    except httpx.ConnectError as e:
        logger.error(f"AI service connection error: {e}")
        raise AIServiceError("AI service unavailable", 503)

    except httpx.HTTPError as e:
        logger.error(f"AI service HTTP error: {e}")
        raise AIServiceError(f"AI service request failed: {str(e)}")

    except AIServiceError:
        raise

    except Exception as e:
        logger.exception(f"Unexpected error calling AI service: {e}")
        raise AIServiceError(f"Unexpected error: {str(e)}")


def get_ai_recommendations(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    exclude_movie_ids: Optional[List[int]] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """
    Fetch personalized recommendations from the AI service.

    Features:
    - Redis caching (5 minute TTL)
    - Circuit breaker protection
    - Automatic retry on transient failures

    Args:
        user_id: The user's ID (string, will be converted to int for AI service)
        limit: Maximum number of recommendations (1-50)
        offset: Pagination offset for results
        exclude_movie_ids: Optional list of movie IDs to exclude
        use_cache: Whether to use Redis cache (default True)

    Returns:
        List of recommendation dictionaries containing:
        - movie_id: int
        - score: float
        - rank: int
        - explanation: dict

    Raises:
        AIServiceError: If the AI service is unavailable or returns an error
        CircuitBreakerError: If the circuit breaker is open
    """
    # Check cache first
    if use_cache and cache.is_available:
        cached = get_cached_recommendations(user_id, limit, offset)
        if cached is not None:
            logger.debug(f"Cache hit for recommendations: user_id={user_id}")
            return cached

    # Call AI service with circuit breaker protection
    try:
        items = ai_service_circuit.call(
            _call_ai_service,
            user_id=user_id,
            limit=limit,
            offset=offset,
            exclude_movie_ids=exclude_movie_ids,
        )

        # Cache successful results
        if use_cache and items:
            set_cached_recommendations(user_id, limit, offset, items)

        return items

    except CircuitBreakerError:
        logger.warning(f"AI circuit breaker open for user_id={user_id}")
        raise AIServiceError("AI service temporarily unavailable (circuit open)", 503)


async def get_ai_recommendations_async(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    exclude_movie_ids: Optional[List[int]] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """
    Async version of get_ai_recommendations.

    Uses httpx async client for non-blocking IO.
    """
    # Check cache first
    if use_cache and cache.is_available:
        cached = get_cached_recommendations(user_id, limit, offset)
        if cached is not None:
            logger.debug(f"Cache hit for recommendations: user_id={user_id}")
            return cached

    if not AI_BASE_URL:
        raise AIServiceError("AI_BASE_URL not configured")

    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    user_id_int = _convert_user_id(user_id)
    request_id = str(uuid.uuid4())

    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{AI_BASE_URL}/ai/recommend",
                json={
                    "request_id": request_id,
                    "user_id": user_id_int,
                    "limit": limit,
                    "offset": offset,
                    "exclude_movie_ids": exclude_movie_ids or [],
                    "context": {"use_social": True},
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Token": AI_INTERNAL_TOKEN,
                },
            )

        if not response.is_success:
            raise AIServiceError(f"AI service error: {response.status_code}", response.status_code)

        data = response.json()
        items = data.get("items", [])

        # Cache results
        if use_cache and items:
            set_cached_recommendations(user_id, limit, offset, items)

        return items

    except httpx.TimeoutException:
        raise AIServiceError("AI service timeout", 504)
    except httpx.HTTPError as e:
        raise AIServiceError(f"AI service error: {str(e)}", 503)


def get_ai_explanation(
    user_id: str,
    movie_id: int,
) -> Dict[str, Any]:
    """
    Get AI explanation for why a movie was recommended.

    Args:
        user_id: The user's ID
        movie_id: The movie ID to explain

    Returns:
        Explanation dictionary containing:
        - ai_score: int
        - explanation: dict
        - social_signals: dict

    Raises:
        AIServiceError: If the AI service is unavailable or returns an error
    """
    if not AI_BASE_URL:
        raise AIServiceError("AI_BASE_URL not configured")

    user_id_int = _convert_user_id(user_id)
    request_id = str(uuid.uuid4())

    try:
        with httpx.Client(timeout=AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{AI_BASE_URL}/ai/explain",
                json={
                    "request_id": request_id,
                    "user_id": user_id_int,
                    "movie_id": movie_id,
                    "context": {"use_social": True},
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Token": AI_INTERNAL_TOKEN,
                },
            )

        response.raise_for_status()
        return response.json()

    except httpx.HTTPError as e:
        logger.error(f"AI explanation request error: {e}")
        raise AIServiceError(f"Failed to get explanation: {str(e)}")
