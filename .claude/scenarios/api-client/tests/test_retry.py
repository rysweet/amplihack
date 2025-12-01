"""
Tests for retry logic with exponential backoff.

Tests the retry mechanism that handles transient failures with
exponential backoff, jitter, and maximum retry limits.

Coverage areas:
- Exponential backoff calculation
- Jitter application
- Retry on specific status codes
- Retry on specific exceptions
- Max retry limit enforcement
- Backoff ceiling enforcement
- Retry callback hooks
"""

import time
from unittest.mock import Mock, patch

import pytest


class TestRetryLogic:
    """Test core retry logic."""

    def test_retry_on_500_error(self) -> None:
        """Test retry on 500 Internal Server Error."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=3)

        with patch.object(client, "_make_request") as mock_request:
            # First two attempts fail with 500, third succeeds
            mock_request.side_effect = [
                Mock(status_code=500, ok=False),
                Mock(status_code=500, ok=False),
                Mock(status_code=200, ok=True, json=lambda: {"success": True}),
            ]

            response = client.get("/unstable")
            assert response.status_code == 200
            assert mock_request.call_count == 3

    def test_retry_on_502_bad_gateway(self) -> None:
        """Test retry on 502 Bad Gateway."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=502, ok=False),
                Mock(status_code=200, ok=True),
            ]

            response = client.get("/endpoint")
            assert response.status_code == 200
            assert mock_request.call_count == 2

    def test_retry_on_503_service_unavailable(self) -> None:
        """Test retry on 503 Service Unavailable."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=503, ok=False),
                Mock(status_code=200, ok=True),
            ]

            client.get("/endpoint")
            assert mock_request.call_count == 2

    def test_retry_on_504_gateway_timeout(self) -> None:
        """Test retry on 504 Gateway Timeout."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=504, ok=False),
                Mock(status_code=200, ok=True),
            ]

            client.get("/endpoint")
            assert mock_request.call_count == 2

    def test_no_retry_on_4xx_errors(self) -> None:
        """Test no retry on 4xx client errors."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import ResponseError

        client = RestClient(base_url="https://api.example.com", max_retries=3)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=400, ok=False)

            with pytest.raises(ResponseError):
                client.get("/bad-request")

            # Should only try once for 4xx errors
            assert mock_request.call_count == 1

    def test_no_retry_on_404_not_found(self) -> None:
        """Test no retry on 404 Not Found."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import NotFoundError

        client = RestClient(base_url="https://api.example.com", max_retries=3)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=404, ok=False)

            with pytest.raises(NotFoundError):
                client.get("/missing")

            assert mock_request.call_count == 1

    def test_retry_on_connection_error(self) -> None:
        """Test retry on connection errors."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=3)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                ConnectionError("Connection refused"),
                ConnectionError("Connection refused"),
                Mock(status_code=200, ok=True),
            ]

            response = client.get("/endpoint")
            assert response.status_code == 200
            assert mock_request.call_count == 3

    def test_retry_on_timeout_error(self) -> None:
        """Test retry on timeout errors."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                TimeoutError("Request timed out"),
                Mock(status_code=200, ok=True),
            ]

            client.get("/slow")
            assert mock_request.call_count == 2


class TestExponentialBackoff:
    """Test exponential backoff timing."""

    def test_exponential_backoff_calculation(self) -> None:
        """Test exponential backoff increases correctly."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(backoff_factor=1.0, jitter=False, backoff_max=60)

        # Exponential: 1, 2, 4, 8, 16, 32, 60 (capped)
        assert policy.calculate_backoff(1) == 1.0
        assert policy.calculate_backoff(2) == 2.0
        assert policy.calculate_backoff(3) == 4.0
        assert policy.calculate_backoff(4) == 8.0
        assert policy.calculate_backoff(5) == 16.0
        assert policy.calculate_backoff(6) == 32.0
        assert policy.calculate_backoff(7) <= 60.0  # Capped

    def test_backoff_factor_scaling(self) -> None:
        """Test backoff factor scales wait time."""
        from amplihack.api_client.models import RetryPolicy

        policy_slow = RetryPolicy(backoff_factor=2.0, jitter=False)
        policy_fast = RetryPolicy(backoff_factor=0.5, jitter=False)

        # Slower backoff
        assert policy_slow.calculate_backoff(1) == 2.0
        assert policy_slow.calculate_backoff(2) == 4.0

        # Faster backoff
        assert policy_fast.calculate_backoff(1) == 0.5
        assert policy_fast.calculate_backoff(2) == 1.0

    def test_backoff_max_ceiling(self) -> None:
        """Test backoff respects maximum ceiling."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(backoff_factor=1.0, backoff_max=10, jitter=False)

        # Should never exceed backoff_max
        for attempt in range(1, 20):
            backoff = policy.calculate_backoff(attempt)
            assert backoff <= 10.0

    def test_jitter_adds_randomness(self) -> None:
        """Test jitter adds randomness to backoff."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(backoff_factor=1.0, jitter=True)

        # Collect multiple samples
        samples = [policy.calculate_backoff(3) for _ in range(10)]

        # With jitter, not all samples should be identical
        unique_samples = set(samples)
        assert len(unique_samples) > 1  # At least some variation

        # All samples should be in valid range (50-150% of base)
        for sample in samples:
            assert 2.0 <= sample <= 6.0  # 4.0 * 0.5 to 4.0 * 1.5

    def test_actual_retry_delay_timing(self) -> None:
        """Test actual retry delays match backoff calculation."""
        from amplihack.api_client import RestClient

        client = RestClient(
            base_url="https://api.example.com",
            max_retries=3,
            retry_backoff_factor=0.1,  # Small for fast test
        )

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=500, ok=False),
                Mock(status_code=500, ok=False),
                Mock(status_code=200, ok=True),
            ]

            start = time.time()
            client.get("/endpoint")
            elapsed = time.time() - start

            # Should have waited at least for 2 retries with backoff
            # First retry: ~0.1s, second retry: ~0.2s, total ~0.3s minimum
            # With jitter (50-150%), minimum is ~0.15s
            assert elapsed >= 0.15


class TestMaxRetries:
    """Test maximum retry limits."""

    def test_max_retries_limit(self) -> None:
        """Test respects max_retries limit."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import RetryExhaustedError

        client = RestClient(base_url="https://api.example.com", max_retries=3)

        with patch.object(client, "_make_request") as mock_request:
            # Always fail
            mock_request.return_value = Mock(status_code=500, ok=False)

            with pytest.raises(RetryExhaustedError) as exc_info:
                client.get("/always-fails")

            # Should try initial + 3 retries = 4 total
            assert mock_request.call_count == 4
            assert exc_info.value.attempts == 4

    def test_zero_retries_disabled(self) -> None:
        """Test max_retries=0 disables retries."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import ServerError

        client = RestClient(base_url="https://api.example.com", max_retries=0)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=500, ok=False)

            with pytest.raises(ServerError):
                client.get("/endpoint")

            # Should only try once
            assert mock_request.call_count == 1

    def test_retry_exhausted_preserves_last_error(self) -> None:
        """Test RetryExhaustedError preserves last exception."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import RetryExhaustedError, ServerError

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=503, ok=False)

            with pytest.raises(RetryExhaustedError) as exc_info:
                client.get("/endpoint")

            error = exc_info.value
            assert isinstance(error.last_exception, ServerError)
            assert error.last_exception.status_code == 503


class TestRetryCallbacks:
    """Test retry callback hooks."""

    def test_on_retry_callback_invoked(self) -> None:
        """Test on_retry callback is called on each retry."""
        from amplihack.api_client import RestClient

        retry_calls = []

        def on_retry(attempt: int, exception: Exception, wait_time: float) -> None:
            retry_calls.append(
                {"attempt": attempt, "exception": str(exception), "wait_time": wait_time}
            )

        client = RestClient(base_url="https://api.example.com", max_retries=2, on_retry=on_retry)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=500, ok=False),
                Mock(status_code=500, ok=False),
                Mock(status_code=200, ok=True),
            ]

            client.get("/endpoint")

            # Should have called callback for each retry (2 times)
            assert len(retry_calls) == 2
            assert retry_calls[0]["attempt"] == 1
            assert retry_calls[1]["attempt"] == 2

    def test_retry_callback_receives_exception(self) -> None:
        """Test retry callback receives exception details."""
        from amplihack.api_client import RestClient

        exceptions_received = []

        def on_retry(attempt: int, exception: Exception, wait_time: float) -> None:
            exceptions_received.append(exception)

        client = RestClient(base_url="https://api.example.com", max_retries=2, on_retry=on_retry)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                ConnectionError("Connection refused"),
                Mock(status_code=200, ok=True),
            ]

            client.get("/endpoint")

            assert len(exceptions_received) == 1
            assert isinstance(exceptions_received[0], ConnectionError)


class TestCustomRetryPolicy:
    """Test custom retry policies."""

    def test_custom_retry_statuses(self) -> None:
        """Test custom list of retryable status codes."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(retry_on_statuses=[429, 503])  # Only retry these

        client = RestClient(base_url="https://api.example.com", retry_policy=policy)

        with patch.object(client, "_make_request") as mock_request:
            # 500 is not in retry list, should fail immediately
            mock_request.return_value = Mock(status_code=500, ok=False)

            with pytest.raises(Exception):  # noqa: B017
                client.get("/endpoint")

            assert mock_request.call_count == 1

    def test_custom_retry_exceptions(self) -> None:
        """Test custom list of retryable exceptions."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(retry_on_exceptions=[ConnectionError])  # Only this

        client = RestClient(base_url="https://api.example.com", retry_policy=policy)

        with patch.object(client, "_make_request") as mock_request:
            # TimeoutError not in list, should fail immediately
            mock_request.side_effect = TimeoutError("Timed out")

            with pytest.raises(TimeoutError):
                client.get("/endpoint")

            assert mock_request.call_count == 1

    def test_should_retry_custom_logic(self) -> None:
        """Test custom should_retry function."""
        from amplihack.api_client import RestClient

        def custom_should_retry(response, exception):
            """Only retry on specific conditions."""
            if exception:
                return isinstance(exception, ConnectionError)
            return response.status_code == 503

        client = RestClient(
            base_url="https://api.example.com", should_retry=custom_should_retry, max_retries=2
        )

        with patch.object(client, "_make_request") as mock_request:
            # 500 doesn't match custom logic
            mock_request.return_value = Mock(status_code=500, ok=False)

            with pytest.raises(Exception):  # noqa: B017
                client.get("/endpoint")

            # Should not retry
            assert mock_request.call_count == 1


class TestRetryIntegration:
    """Integration tests for retry behavior."""

    def test_retry_with_eventual_success(self) -> None:
        """Test complete retry cycle with eventual success."""
        from amplihack.api_client import RestClient

        client = RestClient(
            base_url="https://api.example.com", max_retries=5, retry_backoff_factor=0.1
        )

        attempt_count = {"count": 0}

        def make_request_side_effect(*args, **kwargs):
            attempt_count["count"] += 1
            if attempt_count["count"] < 4:
                return Mock(status_code=503, ok=False)
            return Mock(status_code=200, ok=True, json=lambda: {"success": True})

        with patch.object(client, "_make_request", side_effect=make_request_side_effect):
            response = client.get("/flaky-endpoint")

            assert response.status_code == 200
            assert attempt_count["count"] == 4  # Failed 3 times, succeeded on 4th

    def test_retry_preserves_request_data(self) -> None:
        """Test retry sends same request data on each attempt."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        requests_received = []

        def capture_request(*args, **kwargs):
            requests_received.append(kwargs.copy())
            if len(requests_received) < 2:
                return Mock(status_code=500, ok=False)
            return Mock(status_code=200, ok=True)

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.post("/endpoint", json={"data": "test"})

            # All retry attempts should have same data
            assert len(requests_received) == 2
            assert requests_received[0]["json"] == requests_received[1]["json"]
