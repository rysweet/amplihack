"""
Test suite for retry logic with exponential backoff.

Tests retry behavior, exponential backoff timing, max retries enforcement,
status code handling, and RetryExhaustedError scenarios.

Testing Philosophy:
- Unit tests for retry handler logic
- Mock time.sleep to avoid slow tests
- Verify exponential backoff calculations
- Test retry on appropriate status codes only
"""

from unittest.mock import patch

import pytest
import responses

from amplihack.utils.api_client import (
    APIClient,
    HTTPError,
    RequestError,
    RetryConfig,
    RetryExhaustedError,
)


class TestRetryConfiguration:
    """Test RetryConfig dataclass and configuration"""

    def test_default_retry_config(self):
        """Test default retry configuration values"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.retry_on_status == [500, 502, 503, 504]

    def test_custom_retry_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            retry_on_status=[500, 503],
        )

        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.retry_on_status == [500, 503]

    def test_linear_backoff_config(self):
        """Test configuration for linear backoff (exponential_base=1.0)"""
        config = RetryConfig(
            max_retries=3,
            base_delay=5.0,
            exponential_base=1.0,  # Linear backoff
        )

        assert config.exponential_base == 1.0


class TestExponentialBackoff:
    """Test exponential backoff timing calculations"""

    @responses.activate
    def test_exponential_backoff_delays(self):
        """Test exponential backoff calculates correct delays"""
        # First request fails with 500
        # Retries should wait: 1s, 2s, 4s (exponential_base=2.0)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=1.0,
                exponential_base=2.0,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(RetryExhaustedError):
                client.get("/resource")

            # Verify sleep was called with exponential delays
            sleep_calls = [call_obj[0][0] for call_obj in mock_sleep.call_args_list]
            assert len(sleep_calls) == 3
            assert sleep_calls[0] == pytest.approx(1.0, abs=0.1)  # base_delay * 2^0
            assert sleep_calls[1] == pytest.approx(2.0, abs=0.1)  # base_delay * 2^1
            assert sleep_calls[2] == pytest.approx(4.0, abs=0.1)  # base_delay * 2^2

    @responses.activate
    def test_max_delay_enforced(self):
        """Test max_delay caps exponential backoff"""
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_retries=2,
                base_delay=10.0,
                max_delay=15.0,  # Cap at 15 seconds
                exponential_base=2.0,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(RetryExhaustedError):
                client.get("/resource")

            # Second delay would be 20s (10 * 2^1) but capped at 15s
            sleep_calls = [call_obj[0][0] for call_obj in mock_sleep.call_args_list]
            assert sleep_calls[0] == pytest.approx(10.0, abs=0.1)
            assert sleep_calls[1] == pytest.approx(15.0, abs=0.1)  # Capped

    @responses.activate
    def test_linear_backoff_timing(self):
        """Test linear backoff (exponential_base=1.0) maintains constant delay"""
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_retries=2,
                base_delay=5.0,
                exponential_base=1.0,  # Linear
            ),
        )

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(RetryExhaustedError):
                client.get("/resource")

            # All delays should be 5s (linear backoff)
            sleep_calls = [call_obj[0][0] for call_obj in mock_sleep.call_args_list]
            assert all(delay == pytest.approx(5.0, abs=0.1) for delay in sleep_calls)


class TestRetryOnServerErrors:
    """Test retry behavior for server errors (5xx)"""

    @responses.activate
    def test_retry_on_500_internal_server_error(self):
        """Test retry occurs on HTTP 500"""
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200
        assert len(responses.calls) == 3  # 2 failures + 1 success

    @responses.activate
    def test_retry_on_502_bad_gateway(self):
        """Test retry occurs on HTTP 502"""
        responses.add(responses.GET, "https://api.example.com/resource", status=502)
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200
        assert len(responses.calls) == 2  # 1 failure + 1 success

    @responses.activate
    def test_retry_on_503_service_unavailable(self):
        """Test retry occurs on HTTP 503"""
        responses.add(responses.GET, "https://api.example.com/resource", status=503)
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retry_on_504_gateway_timeout(self):
        """Test retry occurs on HTTP 504"""
        responses.add(responses.GET, "https://api.example.com/resource", status=504)
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200
        assert len(responses.calls) == 2


class TestNoRetryOnClientErrors:
    """Test that client errors (4xx) do NOT trigger retries"""

    @responses.activate
    def test_no_retry_on_400_bad_request(self):
        """Test 400 does NOT retry (client error)"""
        responses.add(responses.POST, "https://api.example.com/resource", status=400)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with pytest.raises(HTTPError) as exc_info:
            client.post("/resource", json={})

        assert exc_info.value.status_code == 400
        assert len(responses.calls) == 1  # No retries

    @responses.activate
    def test_no_retry_on_401_unauthorized(self):
        """Test 401 does NOT retry"""
        responses.add(responses.GET, "https://api.example.com/resource", status=401)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with pytest.raises(HTTPError) as exc_info:
            client.get("/resource")

        assert exc_info.value.status_code == 401
        assert len(responses.calls) == 1  # No retries

    @responses.activate
    def test_no_retry_on_403_forbidden(self):
        """Test 403 does NOT retry"""
        responses.add(responses.GET, "https://api.example.com/resource", status=403)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with pytest.raises(HTTPError) as exc_info:
            client.get("/resource")

        assert exc_info.value.status_code == 403
        assert len(responses.calls) == 1

    @responses.activate
    def test_no_retry_on_404_not_found(self):
        """Test 404 does NOT retry"""
        responses.add(responses.GET, "https://api.example.com/notfound", status=404)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with pytest.raises(HTTPError) as exc_info:
            client.get("/notfound")

        assert exc_info.value.status_code == 404
        assert len(responses.calls) == 1


class TestRetryExhaustedError:
    """Test RetryExhaustedError exception behavior"""

    @responses.activate
    def test_retry_exhausted_after_max_retries(self):
        """Test RetryExhaustedError raised after max retries"""
        # All requests fail
        for _ in range(4):  # Initial + 3 retries
            responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError) as exc_info:
                client.get("/resource")

        error = exc_info.value
        assert error.attempts == 3  # Number of retry attempts
        assert error.last_error is not None
        assert isinstance(error.last_error, HTTPError)

    @responses.activate
    def test_retry_exhausted_contains_last_error(self):
        """Test RetryExhaustedError contains the last error encountered"""
        for _ in range(4):
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"error": "Server Error"},
                status=500,
            )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError) as exc_info:
                client.get("/resource")

        assert isinstance(exc_info.value.last_error, HTTPError)
        assert exc_info.value.last_error.status_code == 500

    @responses.activate
    def test_retry_exhausted_with_network_error(self):
        """Test RetryExhaustedError with network errors"""
        client = APIClient(
            base_url="https://invalid-domain-12345.com",
            retry_config=RetryConfig(max_retries=2, base_delay=0.1),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError) as exc_info:
                client.get("/resource")

        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_error, RequestError)

    def test_retry_exhausted_attempts_count(self):
        """Test attempts count is accurate"""
        client = APIClient(
            base_url="https://invalid-domain-12345.com",
            retry_config=RetryConfig(max_retries=5, base_delay=0.1),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError) as exc_info:
                client.get("/resource")

        assert exc_info.value.attempts == 5


class TestMaxRetriesEnforcement:
    """Test max retries is properly enforced"""

    @responses.activate
    def test_max_retries_1(self):
        """Test max_retries=1 allows exactly 1 retry"""
        responses.add(responses.GET, "https://api.example.com/resource", status=500)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=1, base_delay=0.1),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError):
                client.get("/resource")

        assert len(responses.calls) == 2  # Initial + 1 retry

    @responses.activate
    def test_max_retries_0_no_retry(self):
        """Test max_retries=0 disables retry"""
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=0, base_delay=0.1),
        )

        with pytest.raises(HTTPError):
            client.get("/resource")

        assert len(responses.calls) == 1  # No retries

    @responses.activate
    def test_max_retries_5(self):
        """Test max_retries=5 allows exactly 5 retries"""
        for _ in range(6):  # Initial + 5 retries
            responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=5, base_delay=0.1),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError):
                client.get("/resource")

        assert len(responses.calls) == 6  # Initial + 5 retries


class TestRetryOnNetworkErrors:
    """Test retry behavior for network errors"""

    def test_retry_on_connection_error(self):
        """Test retry occurs on connection errors"""
        client = APIClient(
            base_url="https://invalid-domain-12345.com",
            retry_config=RetryConfig(max_retries=2, base_delay=0.1),
        )

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(RetryExhaustedError):
                client.get("/resource")

        # Verify retries occurred
        assert mock_sleep.call_count == 2

    def test_retry_on_timeout(self):
        """Test retry occurs on timeout errors"""
        client = APIClient(
            base_url="https://httpbin.org",
            default_timeout=1.0,  # Very short timeout
            retry_config=RetryConfig(max_retries=2, base_delay=0.1),
        )

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(RetryExhaustedError):
                client.get("/delay/10")

        # Verify retries occurred
        assert mock_sleep.call_count == 2


class TestCustomRetryStatusCodes:
    """Test custom retry_on_status configuration"""

    @responses.activate
    def test_custom_retry_status_codes(self):
        """Test retry only on custom status codes"""
        responses.add(responses.GET, "https://api.example.com/resource", status=503)
        responses.add(responses.GET, "https://api.example.com/resource", status=503)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=0.1,
                retry_on_status=[503],  # Only retry 503
            ),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError):
                client.get("/resource")

        assert len(responses.calls) == 4  # Initial + 3 retries

    @responses.activate
    def test_no_retry_on_status_not_in_list(self):
        """Test no retry if status code not in retry_on_status"""
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=0.1,
                retry_on_status=[503],  # Only retry 503, not 500
            ),
        )

        with pytest.raises(HTTPError):
            client.get("/resource")

        assert len(responses.calls) == 1  # No retries


class TestSuccessfulRequestNoRetry:
    """Test successful requests do not trigger retries"""

    @responses.activate
    def test_200_success_no_retry(self):
        """Test 200 success does not retry"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        response = client.get("/resource")

        assert response.status_code == 200
        assert len(responses.calls) == 1  # No retries

    @responses.activate
    def test_201_created_no_retry(self):
        """Test 201 created does not retry"""
        responses.add(
            responses.POST,
            "https://api.example.com/resource",
            json={"id": 123},
            status=201,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        response = client.post("/resource", json={})

        assert response.status_code == 201
        assert len(responses.calls) == 1

    @responses.activate
    def test_204_no_content_no_retry(self):
        """Test 204 no content does not retry"""
        responses.add(
            responses.DELETE,
            "https://api.example.com/resource/123",
            status=204,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        response = client.delete("/resource/123")

        assert response.status_code == 204
        assert len(responses.calls) == 1
