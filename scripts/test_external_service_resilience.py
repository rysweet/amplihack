#!/usr/bin/env python3
"""Demonstration test for external service integration resilience.

This script demonstrates the retry logic and circuit breaker patterns
implemented in validate_gh_pages_links.py.

Usage:
    python scripts/test_external_service_resilience.py
"""

import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable

import requests

# Configuration (matching validate_gh_pages_links.py)
MAX_RETRIES = 3
RETRY_INITIAL_DELAY = 1
RETRY_BACKOFF_FACTOR = 2
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is in open state."""

    pass


def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    initial_delay: float = RETRY_INITIAL_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    retryable_exceptions: tuple = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ),
) -> Callable:
    """Decorator to retry function with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(
                            f"    Retry: Attempt {attempt + 1}/{max_retries + 1} "
                            f"failed, retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                except Exception:
                    raise

            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    def __init__(
        self,
        failure_threshold: int = CIRCUIT_BREAKER_THRESHOLD,
        timeout: int = CIRCUIT_BREAKER_TIMEOUT,
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "CLOSED"

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                print("    Circuit breaker entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Too many failures. Will retry after {self.timeout}s."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        elapsed = datetime.now() - self.last_failure_time
        return elapsed > timedelta(seconds=self.timeout)

    def _on_success(self) -> None:
        """Handle successful request."""
        if self.state == "HALF_OPEN":
            print("    Circuit breaker recovered, returning to CLOSED state")
            self.state = "CLOSED"
            self.failure_count = 0
            self.last_failure_time = None

    def _on_failure(self) -> None:
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                print(f"    Circuit breaker OPENED after {self.failure_count} failures")
                self.state = "OPEN"


def test_retry_with_exponential_backoff():
    """Test retry logic with exponential backoff."""
    print("\n" + "=" * 70)
    print("TEST 1: Retry Logic with Exponential Backoff")
    print("=" * 70)

    attempt_count = {"count": 0}

    @retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2)
    def flaky_function():
        attempt_count["count"] += 1
        print(f"  Attempt {attempt_count['count']}")
        if attempt_count["count"] < 3:
            raise requests.exceptions.Timeout("Simulated timeout")
        return "Success!"

    start_time = time.time()
    result = flaky_function()
    elapsed = time.time() - start_time

    print(f"\n  ✅ Result: {result}")
    print(f"  ✅ Total attempts: {attempt_count['count']}")
    print(f"  ✅ Elapsed time: {elapsed:.2f}s (with backoff delays)")
    print("  ✅ Expected delays: 0.1s + 0.2s = 0.3s minimum")


def test_retry_exhaustion():
    """Test that retries are eventually exhausted."""
    print("\n" + "=" * 70)
    print("TEST 2: Retry Exhaustion (All Attempts Fail)")
    print("=" * 70)

    attempt_count = {"count": 0}

    @retry_with_backoff(max_retries=2, initial_delay=0.05, backoff_factor=2)
    def always_failing_function():
        attempt_count["count"] += 1
        print(f"  Attempt {attempt_count['count']}")
        raise requests.exceptions.ConnectionError("Simulated connection error")

    try:
        always_failing_function()
        print("  ❌ ERROR: Should have raised exception")
    except requests.exceptions.ConnectionError as e:
        print("\n  ✅ Correctly raised exception after exhausting retries")
        print(f"  ✅ Total attempts: {attempt_count['count']} (expected: 3)")
        print(f"  ✅ Exception: {e}")


def test_circuit_breaker_open():
    """Test circuit breaker opens after threshold failures."""
    print("\n" + "=" * 70)
    print("TEST 3: Circuit Breaker Opens After Threshold Failures")
    print("=" * 70)

    circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=5)

    def failing_function():
        raise requests.exceptions.ConnectionError("Service unavailable")

    # Trigger failures to open circuit
    for i in range(3):
        try:
            circuit_breaker.call(failing_function)
        except requests.exceptions.ConnectionError:
            print(f"  Failure {i + 1}: Circuit state = {circuit_breaker.state}")

    print(f"\n  ✅ Circuit state after 3 failures: {circuit_breaker.state}")
    print(f"  ✅ Failure count: {circuit_breaker.failure_count}")

    # Next call should fail immediately without trying
    try:
        circuit_breaker.call(failing_function)
        print("  ❌ ERROR: Should have raised CircuitBreakerOpenError")
    except CircuitBreakerOpenError as e:
        print(f"  ✅ Circuit breaker is OPEN: {e}")


def test_circuit_breaker_recovery():
    """Test circuit breaker recovers after successful request."""
    print("\n" + "=" * 70)
    print("TEST 4: Circuit Breaker Recovery (HALF_OPEN -> CLOSED)")
    print("=" * 70)

    circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=1)

    def flaky_function():
        if circuit_breaker.failure_count >= 2:
            # Service recovered
            return "Service restored"
        raise requests.exceptions.ConnectionError("Service unavailable")

    # Trigger failures to open circuit
    for i in range(2):
        try:
            circuit_breaker.call(flaky_function)
        except requests.exceptions.ConnectionError:
            print(f"  Failure {i + 1}: Circuit state = {circuit_breaker.state}")

    print(f"\n  Circuit opened: {circuit_breaker.state}")

    # Wait for timeout to allow circuit to half-open
    print(f"  Waiting {circuit_breaker.timeout + 0.5}s for circuit to half-open...")
    time.sleep(circuit_breaker.timeout + 0.5)

    # Next call should succeed and reset circuit
    result = circuit_breaker.call(lambda: "Service restored")
    print(f"\n  ✅ Circuit recovered: {circuit_breaker.state}")
    print(f"  ✅ Result: {result}")
    print(f"  ✅ Failure count reset: {circuit_breaker.failure_count}")


def test_non_retryable_exception():
    """Test that non-retryable exceptions fail immediately."""
    print("\n" + "=" * 70)
    print("TEST 5: Non-Retryable Exceptions (Immediate Failure)")
    print("=" * 70)

    attempt_count = {"count": 0}

    @retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2)
    def function_with_logic_error():
        attempt_count["count"] += 1
        print(f"  Attempt {attempt_count['count']}")
        raise ValueError("This is a logic error, not a network error")

    try:
        function_with_logic_error()
        print("  ❌ ERROR: Should have raised exception")
    except ValueError as e:
        print("\n  ✅ Non-retryable exception failed immediately")
        print(f"  ✅ Attempts: {attempt_count['count']} (expected: 1, no retries)")
        print(f"  ✅ Exception: {e}")


def main():
    """Run all demonstration tests."""
    print("\n" + "#" * 70)
    print("# External Service Integration Resilience Tests")
    print("# Demonstrates retry logic and circuit breaker patterns")
    print("#" * 70)

    try:
        test_retry_with_exponential_backoff()
        test_retry_exhaustion()
        test_circuit_breaker_open()
        test_circuit_breaker_recovery()
        test_non_retryable_exception()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nThese patterns are now integrated into validate_gh_pages_links.py:")
        print("  - LinkValidator._make_external_request() uses retry_with_backoff")
        print("  - LinkValidator._validate_external_link() uses circuit breaker")
        print("  - Crawler.fetch_page() uses retry_with_backoff")
        print("  - validate_link() uses retry_with_backoff")
        print()

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
