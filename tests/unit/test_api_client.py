"""Unit tests for REST API Client (60% of testing pyramid).

These tests verify individual components in isolation using mocks.
Tests are designed to fail initially (TDD approach).
"""

import json
import logging
import threading
from unittest.mock import Mock, patch

import pytest

# Import the API client components (will fail initially)
from amplihack.utils.api_client import (
    APIClient,
    APIError,
    APIRequest,
    APIResponse,
    RateLimitError,
    ValidationError,
)


class TestAPIClientConstruction:
    """Test APIClient initialization and configuration."""

    def test_default_initialization(self):
        """Test client with default configuration."""
        client = APIClient()

        assert client.base_url == ""
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert client.backoff_factor == 1.0

    def test_custom_initialization(self):
        """Test client with custom configuration."""
        client = APIClient(
            base_url="https://api.example.com", timeout=10.0, max_retries=5, backoff_factor=2.0
        )

        assert client.base_url == "https://api.example.com"
        assert client.timeout == 10.0
        assert client.max_retries == 5
        assert client.backoff_factor == 2.0

    def test_invalid_timeout(self):
        """Test that negative timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIClient(timeout=-1)

        assert "timeout must be positive" in str(exc_info.value).lower()

    def test_invalid_max_retries(self):
        """Test that negative max_retries raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIClient(max_retries=-1)

        assert "max_retries must be non-negative" in str(exc_info.value).lower()

    def test_invalid_backoff_factor(self):
        """Test that negative backoff_factor raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIClient(backoff_factor=-1)

        assert "backoff_factor must be positive" in str(exc_info.value).lower()


class TestAPIRequestDataclass:
    """Test APIRequest dataclass structure and validation."""

    def test_minimal_request(self):
        """Test creating request with minimal required fields."""
        request = APIRequest(method="GET", endpoint="/users")

        assert request.method == "GET"
        assert request.endpoint == "/users"
        assert request.data is None
        assert request.headers == {}

    def test_full_request(self):
        """Test creating request with all fields."""
        headers = {"Authorization": "Bearer token"}
        data = {"name": "test"}

        request = APIRequest(method="POST", endpoint="/users", data=data, headers=headers)

        assert request.method == "POST"
        assert request.endpoint == "/users"
        assert request.data == data
        assert request.headers == headers

    def test_invalid_method(self):
        """Test that invalid HTTP method raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest(method="INVALID", endpoint="/test")

        assert "invalid http method" in str(exc_info.value).lower()

    def test_empty_endpoint(self):
        """Test that empty endpoint raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest(method="GET", endpoint="")

        assert "endpoint cannot be empty" in str(exc_info.value).lower()


class TestAPIResponseDataclass:
    """Test APIResponse dataclass structure."""

    def test_minimal_response(self):
        """Test creating response with minimal fields."""
        response = APIResponse(status_code=200, data=None, headers={})

        assert response.status_code == 200
        assert response.data is None
        assert response.headers == {}

    def test_full_response(self):
        """Test creating response with all fields."""
        data = {"id": 123, "name": "test"}
        headers = {"Content-Type": "application/json"}

        response = APIResponse(status_code=201, data=data, headers=headers)

        assert response.status_code == 201
        assert response.data == data
        assert response.headers == headers


class TestExponentialBackoff:
    """Test exponential backoff calculation with jitter."""

    def test_backoff_calculation_no_jitter(self):
        """Test exponential backoff without jitter."""
        client = APIClient(backoff_factor=1.0)

        # Mock random to return 0 (no jitter)
        with patch("random.uniform", return_value=0):
            assert client._calculate_backoff(0) == 1  # 1 * 2^0 = 1
            assert client._calculate_backoff(1) == 2  # 1 * 2^1 = 2
            assert client._calculate_backoff(2) == 4  # 1 * 2^2 = 4
            assert client._calculate_backoff(3) == 8  # 1 * 2^3 = 8
            assert client._calculate_backoff(4) == 16  # 1 * 2^4 = 16

    def test_backoff_with_custom_factor(self):
        """Test backoff with custom factor."""
        client = APIClient(backoff_factor=2.0)

        with patch("random.uniform", return_value=0):
            assert client._calculate_backoff(0) == 2  # 2 * 2^0 = 2
            assert client._calculate_backoff(1) == 4  # 2 * 2^1 = 4
            assert client._calculate_backoff(2) == 8  # 2 * 2^2 = 8

    def test_backoff_with_jitter(self):
        """Test that jitter adds randomness to backoff."""
        client = APIClient(backoff_factor=1.0)

        # Mock random to return 0.5 (50% jitter)
        with patch("random.uniform", return_value=0.5):
            # Base backoff is 4, jitter adds 0-4, so 0.5 * 4 = 2
            assert client._calculate_backoff(2) == 6  # 4 + 2

    def test_backoff_max_limit(self):
        """Test that backoff has a maximum limit."""
        client = APIClient(backoff_factor=1.0)

        with patch("random.uniform", return_value=0):
            # Should cap at some reasonable maximum (e.g., 60 seconds)
            assert client._calculate_backoff(10) <= 60


class TestExecuteMethod:
    """Test the main execute method."""

    @patch("requests.request")
    def test_successful_request(self, mock_request):
        """Test successful request without retries."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="GET", endpoint="/test")

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data == {"success": True}
        assert response.headers["Content-Type"] == "application/json"

        # Verify request was made correctly
        mock_request.assert_called_once_with(
            method="GET",
            url="https://api.test.com/test",
            json=None,
            headers={},
            timeout=30.0,
            verify=True,
        )

    @patch("requests.request")
    def test_request_with_data_and_headers(self, mock_request):
        """Test request with data and custom headers."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(
            method="POST",
            endpoint="/users",
            data={"name": "test"},
            headers={"Authorization": "Bearer token"},
        )

        response = client.execute(request)

        assert response.status_code == 201
        assert response.data == {"id": 123}

        mock_request.assert_called_once_with(
            method="POST",
            url="https://api.test.com/users",
            json={"name": "test"},
            headers={"Authorization": "Bearer token"},
            timeout=30.0,
            verify=True,
        )

    @patch("requests.request")
    def test_request_timeout(self, mock_request):
        """Test that timeout is passed correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(timeout=5.0)
        request = APIRequest(method="GET", endpoint="/test")

        client.execute(request)

        mock_request.assert_called_once_with(
            method="GET", url="/test", json=None, headers={}, timeout=5.0, verify=True
        )


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @patch("time.sleep")
    @patch("requests.request")
    def test_retry_on_500_error(self, mock_request, mock_sleep):
        """Test that 500 errors trigger retries."""
        # First two calls return 500, third succeeds
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.text = "Internal Server Error"
        mock_response_500.headers = {}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}
        mock_response_200.headers = {}

        mock_request.side_effect = [mock_response_500, mock_response_500, mock_response_200]

        client = APIClient(max_retries=3)
        request = APIRequest(method="GET", endpoint="/test")

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data == {"success": True}

        # Verify 3 requests were made
        assert mock_request.call_count == 3

        # Verify sleep was called for backoff (2 times)
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    @patch("requests.request")
    def test_max_retries_exceeded(self, mock_request, mock_sleep):
        """Test that max retries limit is respected."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(max_retries=2)
        request = APIRequest(method="GET", endpoint="/test")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert "max retries exceeded" in str(exc_info.value).lower()

        # Initial request + 2 retries = 3 total
        assert mock_request.call_count == 3

    @patch("time.sleep")
    @patch("requests.request")
    def test_no_retry_on_4xx_errors(self, mock_request, mock_sleep):
        """Test that 4xx errors don't trigger retries."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(max_retries=3)
        request = APIRequest(method="GET", endpoint="/test")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert exc_info.value.status_code == 404

        # Only one request, no retries
        assert mock_request.call_count == 1
        assert mock_sleep.call_count == 0


class TestRateLimiting:
    """Test rate limit handling (429 responses)."""

    @patch("time.sleep")
    @patch("requests.request")
    def test_rate_limit_with_retry_after(self, mock_request, mock_sleep):
        """Test handling 429 with Retry-After header."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "5"}
        mock_response_429.text = "Rate limited"

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}
        mock_response_200.headers = {}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        client = APIClient(max_retries=3)
        request = APIRequest(method="GET", endpoint="/test")

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data == {"success": True}

        # Verify sleep was called with Retry-After value
        mock_sleep.assert_called_with(5.0)

    @patch("time.sleep")
    @patch("requests.request")
    def test_rate_limit_without_retry_after(self, mock_request, mock_sleep):
        """Test handling 429 without Retry-After header."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {}
        mock_response_429.text = "Rate limited"

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}
        mock_response_200.headers = {}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        client = APIClient(max_retries=3)
        request = APIRequest(method="GET", endpoint="/test")

        response = client.execute(request)

        assert response.status_code == 200

        # Should use exponential backoff instead
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    @patch("requests.request")
    def test_rate_limit_error_raised(self, mock_request, mock_sleep):
        """Test that RateLimitError is raised after max retries."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Rate limited"
        mock_request.return_value = mock_response

        client = APIClient(max_retries=2)
        request = APIRequest(method="GET", endpoint="/test")

        with pytest.raises(RateLimitError) as exc_info:
            client.execute(request)

        assert "rate limit exceeded" in str(exc_info.value).lower()
        assert exc_info.value.retry_after == 60


class TestErrorHandling:
    """Test various error scenarios."""

    @patch("requests.request")
    def test_connection_error(self, mock_request):
        """Test handling of connection errors."""
        import requests

        mock_request.side_effect = requests.ConnectionError("Connection failed")

        client = APIClient(max_retries=0)
        request = APIRequest(method="GET", endpoint="/test")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert "connection" in str(exc_info.value).lower()

    @patch("requests.request")
    def test_timeout_error(self, mock_request):
        """Test handling of timeout errors."""
        import requests

        mock_request.side_effect = requests.Timeout("Request timed out")

        client = APIClient(max_retries=0)
        request = APIRequest(method="GET", endpoint="/test")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert "timeout" in str(exc_info.value).lower()

    @patch("requests.request")
    def test_json_decode_error(self, mock_request):
        """Test handling of invalid JSON responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        mock_response.text = "Not JSON"
        mock_response.headers = {"Content-Type": "application/json"}
        mock_request.return_value = mock_response

        client = APIClient()
        request = APIRequest(method="GET", endpoint="/test")

        response = client.execute(request)

        # Should return response with text but no data
        assert response.status_code == 200
        assert response.data is None
        assert "Not JSON" in str(response)


class TestThreadSafety:
    """Test thread safety of the API client."""

    @patch("requests.request")
    def test_concurrent_requests(self, mock_request):
        """Test that multiple threads can use the client concurrently."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"thread_safe": True}
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient()
        results = []
        errors = []

        def make_request(thread_id):
            try:
                request = APIRequest(method="GET", endpoint=f"/test/{thread_id}")
                response = client.execute(request)
                results.append((thread_id, response.status_code))
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 10

        # All requests should succeed
        for thread_id, status in results:
            assert status == 200

    @pytest.mark.skip(reason="Thread-local state was simplified - testing internal implementation")
    def test_thread_local_state(self):
        """Test that client maintains thread-local state if needed."""
        # This test was testing internal implementation details (_get_thread_state)
        # which has been removed as part of simplification. The client now uses
        # a simpler single session approach which is sufficient for most use cases.


class TestLogging:
    """Test logging output."""

    @patch("requests.request")
    def test_request_logging(self, mock_request, caplog):
        """Test that requests are logged."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_request.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = APIClient()
            request = APIRequest(method="GET", endpoint="/test")
            client.execute(request)

        # Check for request log
        assert any("GET /test" in record.message for record in caplog.records)
        assert any("200" in record.message for record in caplog.records)

    @patch("time.sleep")
    @patch("requests.request")
    def test_retry_logging(self, mock_request, mock_sleep, caplog):
        """Test that retries are logged."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        with caplog.at_level(logging.INFO):
            client = APIClient(max_retries=1)
            request = APIRequest(method="GET", endpoint="/test")

            with pytest.raises(APIError):
                client.execute(request)

        # Check for retry log
        assert any("retry" in record.message.lower() for record in caplog.records)

    @patch("time.sleep")
    @patch("requests.request")
    def test_rate_limit_logging(self, mock_request, mock_sleep, caplog):
        """Test that rate limits are logged."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "5"}
        mock_response.text = "Rate limited"
        mock_request.return_value = mock_response

        with caplog.at_level(logging.WARNING):
            client = APIClient(max_retries=0)
            request = APIRequest(method="GET", endpoint="/test")

            with pytest.raises(RateLimitError):
                client.execute(request)

        # Check for rate limit log
        assert any("rate limit" in record.message.lower() for record in caplog.records)


class TestTypeValidation:
    """Test type validation for inputs."""

    def test_invalid_method_type(self):
        """Test that invalid method type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest(method=123, endpoint="/test")

        assert "method must be a string" in str(exc_info.value).lower()

    def test_invalid_endpoint_type(self):
        """Test that invalid endpoint type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest(method="GET", endpoint=None)

        assert "endpoint must be a string" in str(exc_info.value).lower()

    def test_invalid_headers_type(self):
        """Test that invalid headers type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest(method="GET", endpoint="/test", headers="invalid")

        assert "headers must be a dictionary" in str(exc_info.value).lower()

    def test_invalid_data_type(self):
        """Test that data can be dict or None."""
        # Dict should work
        request = APIRequest(method="POST", endpoint="/test", data={"key": "value"})
        assert request.data == {"key": "value"}

        # None should work
        request = APIRequest(method="GET", endpoint="/test", data=None)
        assert request.data is None

        # List should work for JSON arrays
        request = APIRequest(method="POST", endpoint="/test", data=[1, 2, 3])
        assert request.data == [1, 2, 3]


class TestExceptionHierarchy:
    """Test the exception hierarchy."""

    def test_api_error_base_class(self):
        """Test that APIError is the base for all API exceptions."""
        error = APIError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_rate_limit_error_inheritance(self):
        """Test that RateLimitError inherits from APIError."""
        error = RateLimitError("Rate limited", retry_after=60)
        assert isinstance(error, APIError)
        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60

    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from APIError."""
        error = ValidationError("Invalid input")
        assert isinstance(error, APIError)
        assert isinstance(error, ValidationError)

    def test_error_with_details(self):
        """Test that errors can include additional details."""
        error = APIError(
            "Request failed", status_code=500, response_body="Internal error", request_id="req-123"
        )

        assert str(error) == "Request failed"
        assert error.status_code == 500
        assert error.response_body == "Internal error"
        assert error.request_id == "req-123"
