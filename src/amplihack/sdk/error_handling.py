"""
Comprehensive Error Handling and Recovery for Auto-Mode

Implements circuit breakers, retry logic, graceful degradation,
and security controls for the Claude Agent SDK integration.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Type, Union
import uuid
import functools

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAK = "circuit_break"
    ESCALATE = "escalate"
    IGNORE = "ignore"


@dataclass
class ErrorPattern:
    """Pattern definition for error classification"""
    id: str
    name: str
    exception_types: List[Type[Exception]]
    keywords: List[str]
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_break_threshold: int = 5
    timeout_seconds: float = 60.0


@dataclass
class ErrorOccurrence:
    """Record of a specific error occurrence"""
    id: str
    timestamp: datetime
    pattern_id: str
    exception_type: str
    error_message: str
    context: Dict[str, Any]
    severity: ErrorSeverity
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker"""
    name: str
    state: str  # "closed", "open", "half_open"
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3  # For half-open state
    consecutive_successes: int = 0


class SecurityViolationError(Exception):
    """Raised when security violations are detected"""
    pass


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class MaxRetriesExceededError(Exception):
    """Raised when maximum retries are exceeded"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.

    Protects against cascading failures by monitoring error rates
    and temporarily stopping calls when thresholds are exceeded.
    """

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.state = CircuitBreakerState(
            name=name,
            state="closed",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker"""
        if self.state.state == "open":
            if self._should_attempt_reset():
                self.state.state = "half_open"
                self.state.consecutive_successes = 0
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker {self.state.name} is open")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.state.last_failure_time:
            return True

        time_since_failure = datetime.now() - self.state.last_failure_time
        return time_since_failure.total_seconds() > self.state.recovery_timeout

    async def _on_success(self) -> None:
        """Handle successful call"""
        if self.state.state == "half_open":
            self.state.consecutive_successes += 1
            if self.state.consecutive_successes >= self.state.success_threshold:
                self.state.state = "closed"
                self.state.failure_count = 0
                logger.info(f"Circuit breaker {self.state.name} reset to closed")
        elif self.state.state == "closed":
            self.state.failure_count = max(0, self.state.failure_count - 1)

    async def _on_failure(self) -> None:
        """Handle failed call"""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.now()

        if self.state.failure_count >= self.state.failure_threshold:
            self.state.state = "open"
            logger.warning(f"Circuit breaker {self.state.name} opened due to failures")


class RetryConfig:
    """Configuration for retry logic"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        if attempt <= 0:
            return 0

        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)  # Add 0-50% jitter

        return delay


def with_retry(
    retry_config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,)
):
    """Decorator for adding retry logic to functions"""
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retry_config.max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    if attempt == retry_config.max_attempts - 1:
                        break

                    delay = retry_config.get_delay(attempt + 1)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)

            raise MaxRetriesExceededError(f"Max retries exceeded") from last_exception

        return wrapper
    return decorator


class SecurityValidator:
    """Validates inputs and operations for security violations"""

    def __init__(self):
        self.blocked_patterns = [
            r"__import__",
            r"eval\s*\(",
            r"exec\s*\(",
            r"subprocess",
            r"os\.system",
            r"file\s*=\s*open",
            r"rm\s+-rf",
            r"DELETE\s+FROM",
            r"DROP\s+TABLE"
        ]

    def validate_prompt_content(self, content: str) -> None:
        """Validate prompt content for security violations"""
        import re

        content_lower = content.lower()

        # Check for dangerous patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, content_lower):
                raise SecurityViolationError(f"Dangerous pattern detected: {pattern}")

        # Check for excessive length (potential DoS)
        if len(content) > 50000:
            raise SecurityViolationError("Prompt content exceeds maximum length")

        # Check for potential code injection
        if "```" in content and any(lang in content_lower for lang in ["python", "bash", "sh", "cmd"]):
            # Allow legitimate code blocks but log them
            logger.info("Code block detected in prompt - monitoring for safety")

    def validate_file_path(self, file_path: str) -> None:
        """Validate file paths for security violations"""
        import os

        # Normalize path
        normalized_path = os.path.normpath(file_path)

        # Check for path traversal
        if ".." in normalized_path:
            raise SecurityViolationError("Path traversal detected")

        # Check for absolute paths outside working directory
        if os.path.isabs(normalized_path):
            # Allow paths within specific directories only
            allowed_prefixes = ["/tmp", "/var/tmp", os.getcwd()]
            if not any(normalized_path.startswith(prefix) for prefix in allowed_prefixes):
                raise SecurityViolationError("Absolute path outside allowed directories")

    def validate_api_request(self, request_data: Dict[str, Any]) -> None:
        """Validate API request data"""
        # Check request size
        request_size = len(str(request_data))
        if request_size > 100000:  # 100KB limit
            raise SecurityViolationError("Request size exceeds limit")

        # Check for suspicious keys
        suspicious_keys = ["password", "secret", "token", "key", "auth"]
        for key in request_data.keys():
            if any(suspicious in key.lower() for suspicious in suspicious_keys):
                logger.warning(f"Potentially sensitive key in request: {key}")


class ErrorHandlingManager:
    """
    Comprehensive error handling manager for auto-mode integration.

    Provides centralized error classification, recovery strategies,
    circuit breakers, and security validation.
    """

    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.error_history: List[ErrorOccurrence] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.security_validator = SecurityValidator()
        self.recovery_callbacks: Dict[str, Callable] = {}

        # Rate limiting
        self.rate_limits: Dict[str, List[datetime]] = {}

    def _initialize_error_patterns(self) -> Dict[str, ErrorPattern]:
        """Initialize predefined error patterns"""
        patterns = [
            ErrorPattern(
                id="sdk_connection",
                name="SDK Connection Error",
                exception_types=[ConnectionError, TimeoutError],
                keywords=["connection", "timeout", "network", "sdk"],
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.CIRCUIT_BREAK,
                max_retries=3,
                retry_delay=2.0,
                circuit_break_threshold=3
            ),
            ErrorPattern(
                id="authentication",
                name="Authentication Error",
                exception_types=[PermissionError],
                keywords=["auth", "permission", "unauthorized", "forbidden"],
                severity=ErrorSeverity.CRITICAL,
                recovery_strategy=RecoveryStrategy.ESCALATE,
                max_retries=1
            ),
            ErrorPattern(
                id="rate_limit",
                name="Rate Limit Error",
                exception_types=[],
                keywords=["rate", "limit", "quota", "throttle"],
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=5,
                retry_delay=5.0
            ),
            ErrorPattern(
                id="validation",
                name="Input Validation Error",
                exception_types=[ValueError, TypeError],
                keywords=["invalid", "validation", "format", "type"],
                severity=ErrorSeverity.LOW,
                recovery_strategy=RecoveryStrategy.FALLBACK,
                max_retries=1
            ),
            ErrorPattern(
                id="security_violation",
                name="Security Violation",
                exception_types=[SecurityViolationError],
                keywords=["security", "violation", "dangerous", "blocked"],
                severity=ErrorSeverity.CRITICAL,
                recovery_strategy=RecoveryStrategy.ESCALATE,
                max_retries=0
            )
        ]

        return {pattern.id: pattern for pattern in patterns}

    async def handle_error(
        self,
        exception: Exception,
        context: Dict[str, Any],
        operation_name: str
    ) -> Dict[str, Any]:
        """
        Handle an error with appropriate recovery strategy.

        Args:
            exception: The exception that occurred
            context: Context information about the error
            operation_name: Name of the operation that failed

        Returns:
            Error handling result with recovery information
        """
        try:
            # Classify error
            pattern = self._classify_error(exception)

            # Create error occurrence record
            error_occurrence = ErrorOccurrence(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                pattern_id=pattern.id,
                exception_type=type(exception).__name__,
                error_message=str(exception),
                context=context,
                severity=pattern.severity
            )

            self.error_history.append(error_occurrence)

            # Log error
            logger.error(
                f"Error in {operation_name}: {pattern.name} - {exception}",
                extra={"error_id": error_occurrence.id, "pattern": pattern.id}
            )

            # Apply recovery strategy
            recovery_result = await self._apply_recovery_strategy(
                pattern, error_occurrence, operation_name
            )

            return {
                "error_id": error_occurrence.id,
                "pattern_id": pattern.id,
                "severity": pattern.severity.value,
                "recovery_strategy": pattern.recovery_strategy.value,
                "recovery_result": recovery_result
            }

        except Exception as e:
            logger.critical(f"Error in error handler: {e}")
            return {
                "error_id": "unknown",
                "pattern_id": "unknown",
                "severity": "critical",
                "recovery_strategy": "escalate",
                "recovery_result": {"success": False, "error": str(e)}
            }

    def _classify_error(self, exception: Exception) -> ErrorPattern:
        """Classify error based on patterns"""
        exception_type = type(exception)
        error_message = str(exception).lower()

        for pattern in self.error_patterns.values():
            # Check exception type
            if exception_type in pattern.exception_types:
                return pattern

            # Check keywords
            if any(keyword in error_message for keyword in pattern.keywords):
                return pattern

        # Default to unknown pattern
        return ErrorPattern(
            id="unknown",
            name="Unknown Error",
            exception_types=[],
            keywords=[],
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.RETRY
        )

    async def _apply_recovery_strategy(
        self,
        pattern: ErrorPattern,
        error_occurrence: ErrorOccurrence,
        operation_name: str
    ) -> Dict[str, Any]:
        """Apply recovery strategy for error pattern"""
        if pattern.recovery_strategy == RecoveryStrategy.RETRY:
            return await self._handle_retry_strategy(pattern, error_occurrence)

        elif pattern.recovery_strategy == RecoveryStrategy.CIRCUIT_BREAK:
            return await self._handle_circuit_break_strategy(pattern, operation_name)

        elif pattern.recovery_strategy == RecoveryStrategy.FALLBACK:
            return await self._handle_fallback_strategy(pattern, error_occurrence)

        elif pattern.recovery_strategy == RecoveryStrategy.ESCALATE:
            return await self._handle_escalate_strategy(pattern, error_occurrence)

        elif pattern.recovery_strategy == RecoveryStrategy.IGNORE:
            return {"success": True, "action": "ignored"}

        else:
            return {"success": False, "error": "Unknown recovery strategy"}

    async def _handle_retry_strategy(
        self,
        pattern: ErrorPattern,
        error_occurrence: ErrorOccurrence
    ) -> Dict[str, Any]:
        """Handle retry recovery strategy"""
        if error_occurrence.retry_count >= pattern.max_retries:
            return {"success": False, "error": "Max retries exceeded"}

        retry_delay = pattern.retry_delay * (2 ** error_occurrence.retry_count)
        return {
            "success": True,
            "action": "retry",
            "delay": retry_delay,
            "attempt": error_occurrence.retry_count + 1
        }

    async def _handle_circuit_break_strategy(
        self,
        pattern: ErrorPattern,
        operation_name: str
    ) -> Dict[str, Any]:
        """Handle circuit breaker recovery strategy"""
        circuit_breaker = self._get_circuit_breaker(operation_name, pattern)
        await circuit_breaker._on_failure()

        return {
            "success": False,
            "action": "circuit_break",
            "circuit_state": circuit_breaker.state.state,
            "failure_count": circuit_breaker.state.failure_count
        }

    async def _handle_fallback_strategy(
        self,
        pattern: ErrorPattern,
        error_occurrence: ErrorOccurrence
    ) -> Dict[str, Any]:
        """Handle fallback recovery strategy"""
        # Call registered fallback handler if available
        if pattern.id in self.recovery_callbacks:
            try:
                callback = self.recovery_callbacks[pattern.id]
                result = await callback(error_occurrence)
                return {"success": True, "action": "fallback", "result": result}
            except Exception as e:
                return {"success": False, "error": f"Fallback failed: {e}"}

        return {"success": True, "action": "fallback", "result": "default_fallback"}

    async def _handle_escalate_strategy(
        self,
        pattern: ErrorPattern,
        error_occurrence: ErrorOccurrence
    ) -> Dict[str, Any]:
        """Handle escalation recovery strategy"""
        # Log critical error
        logger.critical(
            f"Critical error requiring escalation: {error_occurrence.error_message}",
            extra={"error_id": error_occurrence.id}
        )

        # Could send notifications, create tickets, etc.
        return {"success": False, "action": "escalated", "requires_manual_intervention": True}

    def _get_circuit_breaker(self, operation_name: str, pattern: ErrorPattern) -> CircuitBreaker:
        """Get or create circuit breaker for operation"""
        key = f"{operation_name}_{pattern.id}"
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker(
                name=key,
                failure_threshold=pattern.circuit_break_threshold,
                recovery_timeout=60
            )
        return self.circuit_breakers[key]

    def check_rate_limit(self, operation: str, limit: int = 10, window_minutes: int = 1) -> bool:
        """Check if operation is within rate limits"""
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)

        if operation not in self.rate_limits:
            self.rate_limits[operation] = []

        # Remove old entries
        self.rate_limits[operation] = [
            timestamp for timestamp in self.rate_limits[operation]
            if timestamp > window_start
        ]

        # Check limit
        if len(self.rate_limits[operation]) >= limit:
            return False

        # Add current request
        self.rate_limits[operation].append(now)
        return True

    def register_recovery_callback(self, pattern_id: str, callback: Callable) -> None:
        """Register callback for specific error pattern recovery"""
        self.recovery_callbacks[pattern_id] = callback

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_history:
            return {"total_errors": 0}

        total_errors = len(self.error_history)
        severity_counts = {}
        pattern_counts = {}

        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            pattern = error.pattern_id
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        return {
            "total_errors": total_errors,
            "severity_distribution": severity_counts,
            "pattern_distribution": pattern_counts,
            "circuit_breakers": {
                name: breaker.state.state
                for name, breaker in self.circuit_breakers.items()
            }
        }