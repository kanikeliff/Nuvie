"""
Circuit Breaker Implementation for Nuvie Backend.

Provides:
- Circuit breaker pattern for AI service calls
- Configurable failure thresholds and recovery times
- Automatic state management (CLOSED, OPEN, HALF_OPEN)
- Metrics and monitoring support
"""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from circuitbreaker import CircuitBreakerError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# -----------------------
# Configuration
# -----------------------
AI_FAILURE_THRESHOLD = int(os.getenv("AI_CIRCUIT_FAILURE_THRESHOLD", "5"))
AI_RECOVERY_TIMEOUT = int(os.getenv("AI_CIRCUIT_RECOVERY_TIMEOUT", "30"))
AI_EXPECTED_EXCEPTION = Exception


# -----------------------
# Circuit Breaker States
# -----------------------
class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


# -----------------------
# Custom Circuit Breaker
# -----------------------
@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0


class ServiceCircuitBreaker:
    """
    Enhanced circuit breaker with metrics and manual controls.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered

    Transitions:
    - CLOSED -> OPEN: When failure_threshold consecutive failures occur
    - OPEN -> HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN -> CLOSED: On successful call
    - HALF_OPEN -> OPEN: On failed call
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: Type[BaseException] = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()
        self._metrics = CircuitBreakerMetrics()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state with automatic transition check."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._metrics.state_changes += 1
                    logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN")
            return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "total_calls": self._metrics.total_calls,
            "successful_calls": self._metrics.successful_calls,
            "failed_calls": self._metrics.failed_calls,
            "rejected_calls": self._metrics.rejected_calls,
            "last_failure": self._format_timestamp(self._metrics.last_failure_time),
            "last_success": self._format_timestamp(self._metrics.last_success_time),
        }

    def _format_timestamp(self, ts: Optional[float]) -> Optional[str]:
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        return (time.time() - self._last_failure_time) >= self.recovery_timeout

    def _record_success(self) -> None:
        """Record successful call."""
        with self._lock:
            self._failure_count = 0
            self._metrics.successful_calls += 1
            self._metrics.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._metrics.state_changes += 1
                logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED (recovered)")

    def _record_failure(self) -> None:
        """Record failed call."""
        with self._lock:
            self._failure_count += 1
            self._metrics.failed_calls += 1
            self._metrics.last_failure_time = time.time()
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._metrics.state_changes += 1
                logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN (still failing)")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._metrics.state_changes += 1
                logger.warning(f"Circuit {self.name}: CLOSED -> OPEN " f"(threshold {self.failure_threshold} reached)")

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If the wrapped function raises an exception
        """
        self._metrics.total_calls += 1

        # Check if circuit is open
        current_state = self.state
        if current_state == CircuitState.OPEN:
            self._metrics.rejected_calls += 1
            logger.warning(f"Circuit {self.name} is OPEN, rejecting call")
            raise CircuitBreakerError(f"Circuit {self.name} is open")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception:
            self._record_failure()
            raise

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit {self.name}: Manually reset to CLOSED")

    def force_open(self) -> None:
        """Manually force circuit to open state."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
            logger.warning(f"Circuit {self.name}: Manually forced to OPEN")


# -----------------------
# Decorator
# -----------------------
def circuit_protected(circuit_breaker: ServiceCircuitBreaker) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to protect a function with circuit breaker.

    Example:
        @circuit_protected(ai_circuit)
        def call_ai_service():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return circuit_breaker.call(func, *args, **kwargs)

        # Attach circuit breaker to function for inspection
        setattr(wrapper, "circuit_breaker", circuit_breaker)
        return wrapper

    return decorator


# -----------------------
# Global Circuit Breakers
# -----------------------
ai_service_circuit = ServiceCircuitBreaker(
    name="ai_service",
    failure_threshold=AI_FAILURE_THRESHOLD,
    recovery_timeout=AI_RECOVERY_TIMEOUT,
)


def get_circuit_status() -> Dict[str, Any]:
    """Get status of all circuit breakers."""
    return {
        "ai_service": ai_service_circuit.metrics,
    }
