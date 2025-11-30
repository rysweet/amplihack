#!/usr/bin/env python3
"""Comprehensive error handling examples for REST API Client.

This example demonstrates:
- Handling different exception types
- Implementing retry strategies
- Rate limit handling
- Circuit breaker pattern
- Graceful degradation
- Error logging and monitoring
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from rest_api_client import (
    APIClient,
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    Response,
    ServerError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResilientAPIClient:
    """API client with comprehensive error handling."""

    def __init__(self, base_url: str):
        self.client = APIClient(base_url=base_url)
        self.circuit_breaker = CircuitBreaker()
        self.cache = {}
        self.error_metrics = ErrorMetrics()

    def get_with_fallback(self, path: str) -> dict[str, Any] | None:
        """GET request with multiple fallback strategies."""
        try:
            # Check circuit breaker
            if self.circuit_breaker.is_open():
                logger.warning(f"Circuit breaker open for {path}")
                return self._get_from_cache(path)

            # Try primary request
            response = self.client.get(path)
            self.circuit_breaker.record_success()

            # Update cache
            self._update_cache(path, response.data)
            return response.data

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            self.error_metrics.record_error(e)
            # Could trigger token refresh here
            raise

        except RateLimitError as e:
            logger.warning(f"Rate limited: waiting {e.retry_after}s")
            self.error_metrics.record_error(e)
            time.sleep(e.retry_after or 60)
            # Retry after waiting
            return self.get_with_fallback(path)

        except NotFoundError as e:
            logger.info(f"Resource not found: {path}")
            self.error_metrics.record_error(e)
            return None

        except ServerError as e:
            logger.error(f"Server error: {e}")
            self.error_metrics.record_error(e)
            self.circuit_breaker.record_failure()
            # Try cache fallback
            return self._get_from_cache(path)

        except NetworkError as e:
            logger.error(f"Network error: {e}")
            self.error_metrics.record_error(e)
            self.circuit_breaker.record_failure()
            # Try cache fallback
            return self._get_from_cache(path)

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            # Try cache as last resort
            return self._get_from_cache(path)

    def _update_cache(self, path: str, data: Any):
        """Update cache with timestamp."""
        self.cache[path] = {"data": data, "timestamp": datetime.now()}

    def _get_from_cache(self, path: str) -> dict[str, Any] | None:
        """Get data from cache if available."""
        if path in self.cache:
            cached = self.cache[path]
            age = datetime.now() - cached["timestamp"]
            logger.info(f"Using cached data for {path} (age: {age})")
            return cached["data"]
        return None


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                time_since_failure = datetime.now() - self.last_failure_time
                if time_since_failure.total_seconds() > self.recovery_timeout:
                    logger.info("Circuit breaker entering half-open state")
                    self.state = "half-open"
                    return False
            return True
        return False

    def record_success(self):
        """Record successful request."""
        if self.state == "half-open":
            logger.info("Circuit breaker closing after successful request")
            self.state = "closed"
            self.failure_count = 0

    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit breaker opening after {self.failure_count} failures")
            self.state = "open"


class ErrorMetrics:
    """Track error metrics for monitoring."""

    def __init__(self):
        self.errors = defaultdict(list)
        self.window = timedelta(hours=1)

    def record_error(self, error: APIError):
        """Record error occurrence."""
        error_type = type(error).__name__
        self.errors[error_type].append(datetime.now())
        self._cleanup_old_errors()

    def get_error_rate(self, error_type: str = None) -> int:
        """Get error count in last hour."""
        self._cleanup_old_errors()

        if error_type:
            return len(self.errors.get(error_type, []))
        return sum(len(errors) for errors in self.errors.values())

    def get_error_summary(self) -> dict[str, int]:
        """Get summary of all error types."""
        self._cleanup_old_errors()
        return {error_type: len(occurrences) for error_type, occurrences in self.errors.items()}

    def _cleanup_old_errors(self):
        """Remove errors outside time window."""
        cutoff = datetime.now() - self.window
        for error_type in list(self.errors.keys()):
            self.errors[error_type] = [ts for ts in self.errors[error_type] if ts > cutoff]


class RetryWithBackoff:
    """Implement custom retry logic with backoff."""

    def __init__(self, client: APIClient):
        self.client = client

    def execute_with_retry(
        self, method: str, path: str, max_attempts: int = 3, backoff_factor: float = 2.0, **kwargs
    ) -> Response:
        """Execute request with exponential backoff retry."""
        last_exception = None
        base_delay = 1.0

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_attempts} for {method} {path}")
                response = getattr(self.client, method.lower())(path, **kwargs)

                if attempt > 1:
                    logger.info(f"Request succeeded after {attempt} attempts")

                return response

            except (NetworkError, ServerError) as e:
                last_exception = e

                if attempt < max_attempts:
                    delay = base_delay * (backoff_factor ** (attempt - 1))
                    logger.warning(
                        f"Request failed (attempt {attempt}): {e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_attempts} attempts failed")

        raise last_exception


class AuthTokenManager:
    """Manage authentication tokens with auto-refresh."""

    def __init__(self, client: APIClient, auth_endpoint: str):
        self.client = client
        self.auth_endpoint = auth_endpoint
        self.token = None
        self.token_expiry = None
        self.refresh_token = None

    def authenticate(self, username: str, password: str):
        """Initial authentication."""
        try:
            response = self.client.post(
                self.auth_endpoint, json={"username": username, "password": password}
            )

            self.token = response.data["access_token"]
            self.refresh_token = response.data.get("refresh_token")
            expires_in = response.data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

            # Update client headers
            self.client.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("Authentication successful")

        except APIError as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def ensure_authenticated(self):
        """Ensure token is valid, refresh if needed."""
        if not self.token:
            raise AuthenticationError("Not authenticated")

        if datetime.now() >= self.token_expiry:
            logger.info("Token expired, refreshing...")
            self.refresh_auth_token()

    def refresh_auth_token(self):
        """Refresh expired token."""
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available")

        try:
            response = self.client.post(
                f"{self.auth_endpoint}/refresh", json={"refresh_token": self.refresh_token}
            )

            self.token = response.data["access_token"]
            expires_in = response.data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

            # Update client headers
            self.client.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("Token refreshed successfully")

        except APIError as e:
            logger.error(f"Token refresh failed: {e}")
            raise AuthenticationError("Token refresh failed") from e


def handle_specific_errors():
    """Example of handling specific error scenarios."""
    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # Example 1: Handle 404 gracefully
    try:
        response = client.get("/users/999999")  # Non-existent user
        print(f"User found: {response.data}")
    except NotFoundError:
        print("User not found - creating default user")
        # Could create a default or guest user here

    # Example 2: Handle rate limiting
    try:
        # Simulate many rapid requests
        for i in range(100):
            client.get(f"/posts/{i}")
    except RateLimitError as e:
        print(f"Rate limited! Wait {e.retry_after} seconds")
        time.sleep(e.retry_after or 60)

    # Example 3: Handle server errors with retry
    retry_client = RetryWithBackoff(client)
    try:
        response = retry_client.execute_with_retry("GET", "/posts/1")
        print(f"Got response: {response.data}")
    except ServerError:
        print("Server is having issues, please try again later")


def main():
    """Demonstrate comprehensive error handling."""

    # Create resilient client
    resilient_client = ResilientAPIClient("https://jsonplaceholder.typicode.com")

    # Test various scenarios
    print("=" * 50)
    print("Testing Resilient API Client")
    print("=" * 50)

    # Successful request
    data = resilient_client.get_with_fallback("/posts/1")
    if data:
        print(f"✓ Got post: {data.get('title', 'No title')}")

    # Non-existent resource (404)
    data = resilient_client.get_with_fallback("/posts/999999")
    if data is None:
        print("✓ Handled 404 gracefully")

    # Simulate circuit breaker
    print("\nSimulating failures to trigger circuit breaker...")
    for i in range(6):
        # Force failures by using invalid endpoint
        data = resilient_client.get_with_fallback(f"/invalid/{i}")
        time.sleep(0.5)

    # Check error metrics
    print("\nError Metrics Summary:")
    metrics = resilient_client.error_metrics.get_error_summary()
    for error_type, count in metrics.items():
        print(f"  {error_type}: {count} occurrences")

    # Demonstrate specific error handling
    print("\n" + "=" * 50)
    print("Specific Error Handling Examples")
    print("=" * 50)
    handle_specific_errors()

    # Demonstrate auth token management
    print("\n" + "=" * 50)
    print("Authentication Token Management")
    print("=" * 50)

    auth_client = APIClient(base_url="https://api.example.com")
    auth_manager = AuthTokenManager(auth_client, "/auth/login")

    try:
        # This would fail with real API, just for demonstration
        auth_manager.authenticate("user", "pass")
    except Exception as e:
        print(f"Auth demo skipped (expected): {e}")


if __name__ == "__main__":
    main()
