"""Unit tests for APIClient class - main client functionality.

Testing pyramid: 60% unit tests (this file)
Focus: Core HTTP methods, headers, SSL, request/response handling
"""

import logging
import ssl
import threading
import time
from unittest.mock import Mock, patch

import pytest

# These imports will fail initially (TDD approach)
from rest_api_client.client import APIClient
from rest_api_client.exceptions import (
    APIClientError,
    InvalidResponseError,
)
from rest_api_client.models import Request, Response


class TestAPIClientInitialization:
    """Test APIClient initialization and configuration."""

    def test_init_with_base_url(self):
        """Test APIClient initializes with base URL."""
        client = APIClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_init_with_headers(self):
        """Test APIClient initializes with custom headers."""
        headers = {"Authorization": "Bearer token", "User-Agent": "TestClient"}
        client = APIClient(base_url="https://api.example.com", headers=headers)
        assert client.headers == headers

    def test_init_with_timeout(self):
        """Test APIClient initializes with timeout settings."""
        client = APIClient(base_url="https://api.example.com", timeout=30, connection_timeout=10)
        assert client.timeout == 30
        assert client.connection_timeout == 10

    def test_init_with_ssl_verify(self):
        """Test APIClient SSL verification settings."""
        client = APIClient(base_url="https://api.example.com", verify_ssl=False)
        assert client.verify_ssl is False

        client_with_context = APIClient(
            base_url="https://api.example.com", ssl_context=ssl.create_default_context()
        )
        assert client_with_context.ssl_context is not None

    def test_init_with_retry_config(self):
        """Test APIClient retry configuration."""
        client = APIClient(
            base_url="https://api.example.com",
            max_retries=5,
            retry_backoff_factor=2.0,
            retry_on_status=[500, 502, 503, 504],
        )
        assert client.max_retries == 5
        assert client.retry_backoff_factor == 2.0
        assert 503 in client.retry_on_status

    def test_init_with_rate_limit_config(self):
        """Test APIClient rate limit configuration."""
        client = APIClient(
            base_url="https://api.example.com", rate_limit_calls=100, rate_limit_period=60
        )
        assert client.rate_limit_calls == 100
        assert client.rate_limit_period == 60

    def test_init_with_logger(self):
        """Test APIClient with custom logger."""
        logger = logging.getLogger("test_logger")
        client = APIClient(base_url="https://api.example.com", logger=logger)
        assert client.logger == logger

    def test_init_validates_base_url(self):
        """Test APIClient validates base URL format."""
        with pytest.raises(ValueError, match="Invalid base URL"):
            APIClient(base_url="not-a-url")

        with pytest.raises(ValueError, match="Base URL must use https"):
            APIClient(base_url="http://api.example.com", enforce_https=True)


class TestAPIClientGET:
    """Test GET method functionality."""

    @patch("rest_api_client.transport.HTTPTransport.request")
    def test_get_basic(self, mock_request):
        """Test basic GET request."""
        # Mock transport response
        mock_request.return_value = (
            200,  # status_code
            {"Content-Type": "application/json"},  # headers
            b'{"result": "success"}',  # body
            0.1,  # elapsed_time
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")

        assert response.status_code == 200
        assert response.json() == {"result": "success"}
        mock_request.assert_called_once()

    @patch("rest_api_client.client.requests.get")
    def test_get_with_params(self, mock_get):
        """Test GET request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": []}
        mock_get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users", params={"page": 1, "limit": 10})

        mock_get.assert_called_with(
            "https://api.example.com/users",
            params={"page": 1, "limit": 10},
            headers=client.headers,
            timeout=(client.connection_timeout, client.timeout),
            verify=client.verify_ssl,
        )

    @patch("rest_api_client.client.requests.get")
    def test_get_with_custom_headers(self, mock_get):
        """Test GET request with custom headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com", headers={"Authorization": "Bearer token"}
        )
        response = client.get("/users", headers={"X-Custom-Header": "value"})

        expected_headers = {"Authorization": "Bearer token", "X-Custom-Header": "value"}
        args, kwargs = mock_get.call_args
        assert kwargs["headers"] == expected_headers

    def test_get_returns_response_object(self):
        """Test GET returns proper Response object."""
        with patch("rest_api_client.client.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.headers = {}
            mock_get.return_value.content = b'{"test": true}'

            client = APIClient(base_url="https://api.example.com")
            response = client.get("/test")

            assert isinstance(response, Response)
            assert hasattr(response, "status_code")
            assert hasattr(response, "headers")
            assert hasattr(response, "body")
            assert hasattr(response, "json")


class TestAPIClientPOST:
    """Test POST method functionality."""

    @patch("rest_api_client.client.requests.post")
    def test_post_with_json(self, mock_post):
        """Test POST request with JSON data."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_post.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        data = {"name": "Test User", "email": "test@example.com"}
        response = client.post("/users", json=data)

        assert response.status_code == 201
        mock_post.assert_called_with(
            "https://api.example.com/users",
            json=data,
            headers=client.headers,
            timeout=(client.connection_timeout, client.timeout),
            verify=client.verify_ssl,
        )

    @patch("rest_api_client.client.requests.post")
    def test_post_with_data(self, mock_post):
        """Test POST request with form data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        response = client.post("/form", data={"field1": "value1", "field2": "value2"})

        mock_post.assert_called_with(
            "https://api.example.com/form",
            data={"field1": "value1", "field2": "value2"},
            headers=client.headers,
            timeout=(client.connection_timeout, client.timeout),
            verify=client.verify_ssl,
        )

    @patch("rest_api_client.client.requests.post")
    def test_post_with_files(self, mock_post):
        """Test POST request with file upload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        files = {"file": ("test.txt", b"file content", "text/plain")}
        response = client.post("/upload", files=files)

        mock_post.assert_called_with(
            "https://api.example.com/upload",
            files=files,
            headers=client.headers,
            timeout=(client.connection_timeout, client.timeout),
            verify=client.verify_ssl,
        )


class TestAPIClientPUT:
    """Test PUT method functionality."""

    @patch("rest_api_client.client.requests.put")
    def test_put_with_json(self, mock_put):
        """Test PUT request with JSON data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_put.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        data = {"name": "Updated Name"}
        response = client.put("/users/123", json=data)

        assert response.status_code == 200
        mock_put.assert_called_once()


class TestAPIClientDELETE:
    """Test DELETE method functionality."""

    @patch("rest_api_client.client.requests.delete")
    def test_delete_basic(self, mock_delete):
        """Test basic DELETE request."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""
        mock_delete.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        response = client.delete("/users/123")

        assert response.status_code == 204
        mock_delete.assert_called_with(
            "https://api.example.com/users/123",
            headers=client.headers,
            timeout=(client.connection_timeout, client.timeout),
            verify=client.verify_ssl,
        )


class TestAPIClientPATCH:
    """Test PATCH method functionality."""

    @patch("rest_api_client.client.requests.patch")
    def test_patch_with_json(self, mock_patch):
        """Test PATCH request with JSON data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"patched": True}
        mock_patch.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        data = {"status": "active"}
        response = client.patch("/users/123", json=data)

        assert response.status_code == 200
        mock_patch.assert_called_once()


class TestHeaderValidation:
    """Test header validation functionality."""

    def test_validate_headers_accepts_valid(self):
        """Test header validation accepts valid headers."""
        client = APIClient(base_url="https://api.example.com")

        valid_headers = {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
            "X-Custom-Header": "value123",
        }

        # Should not raise
        client._validate_headers(valid_headers)

    def test_validate_headers_rejects_invalid(self):
        """Test header validation rejects invalid headers."""
        client = APIClient(base_url="https://api.example.com")

        # Invalid header name (contains newline)
        with pytest.raises(ValueError, match="Invalid header name"):
            client._validate_headers({"Invalid\nHeader": "value"})

        # Invalid header value (contains carriage return)
        with pytest.raises(ValueError, match="Invalid header value"):
            client._validate_headers({"Header": "value\rinjection"})

    def test_validate_headers_size_limit(self):
        """Test header validation enforces size limits."""
        client = APIClient(base_url="https://api.example.com")

        # Header value too long (> 8KB)
        large_value = "x" * 9000
        with pytest.raises(ValueError, match="Header value too large"):
            client._validate_headers({"Large-Header": large_value})

        # Too many headers (> 100)
        many_headers = {f"Header-{i}": f"value-{i}" for i in range(101)}
        with pytest.raises(ValueError, match="Too many headers"):
            client._validate_headers(many_headers)


class TestThreadSafety:
    """Test thread safety of APIClient."""

    def test_concurrent_requests(self):
        """Test APIClient handles concurrent requests safely."""
        client = APIClient(base_url="https://api.example.com")
        results = []
        errors = []

        def make_request(endpoint):
            try:
                with patch("rest_api_client.client.requests.get") as mock_get:
                    mock_get.return_value.status_code = 200
                    mock_get.return_value.json.return_value = {"endpoint": endpoint}
                    response = client.get(endpoint)
                    results.append(response.json())
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(f"/endpoint{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(results) == 10

    def test_thread_local_storage(self):
        """Test thread-local storage for request context."""
        client = APIClient(base_url="https://api.example.com")

        # Verify client uses thread-local storage for request state
        assert hasattr(client, "_thread_local")

        def check_isolation():
            client._thread_local.request_id = threading.current_thread().name
            time.sleep(0.01)  # Allow context switch
            assert client._thread_local.request_id == threading.current_thread().name

        threads = []
        for i in range(5):
            thread = threading.Thread(target=check_isolation, name=f"Thread-{i}")
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


class TestLogging:
    """Test logging functionality."""

    def test_logs_request_details(self, mock_logger):
        """Test client logs request details."""
        with patch("rest_api_client.client.requests.get") as mock_get:
            mock_get.return_value.status_code = 200

            client = APIClient(base_url="https://api.example.com", logger=mock_logger)
            client.get("/users")

            mock_logger.debug.assert_called()
            # Check if request details were logged
            log_calls = mock_logger.debug.call_args_list
            assert any("GET" in str(call) for call in log_calls)
            assert any("/users" in str(call) for call in log_calls)

    def test_logs_response_details(self, mock_logger):
        """Test client logs response details."""
        with patch("rest_api_client.client.requests.get") as mock_get:
            mock_get.return_value.status_code = 200

            client = APIClient(base_url="https://api.example.com", logger=mock_logger)
            client.get("/users")

            # Check if response details were logged
            log_calls = mock_logger.debug.call_args_list
            assert any("200" in str(call) for call in log_calls)

    def test_logs_errors(self, mock_logger):
        """Test client logs errors appropriately."""
        with patch("rest_api_client.client.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            client = APIClient(base_url="https://api.example.com", logger=mock_logger)

            with pytest.raises(APIClientError):
                client.get("/users")

            mock_logger.error.assert_called()


class TestRequestResponseModels:
    """Test Request and Response dataclass models."""

    def test_request_dataclass(self):
        """Test Request dataclass functionality."""
        request = Request(
            method="GET",
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer token"},
            params={"page": 1},
            body=None,
        )

        assert request.method == "GET"
        assert request.url == "https://api.example.com/users"
        assert request.headers["Authorization"] == "Bearer token"
        assert request.params["page"] == 1

    def test_response_dataclass(self):
        """Test Response dataclass functionality."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"result": "success"}',
            elapsed_time=0.123,
            request=None,
        )

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.json() == {"result": "success"}
        assert response.elapsed_time == 0.123

    def test_response_json_parsing(self):
        """Test Response JSON parsing."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"key": "value"}',
            elapsed_time=0.1,
            request=None,
        )

        assert response.json() == {"key": "value"}

        # Test invalid JSON
        response_invalid = Response(
            status_code=200, headers={}, body=b"not json", elapsed_time=0.1, request=None
        )

        with pytest.raises(InvalidResponseError):
            response_invalid.json()


class TestContextManager:
    """Test APIClient as context manager."""

    def test_context_manager_usage(self):
        """Test APIClient can be used as context manager."""
        with APIClient(base_url="https://api.example.com") as client:
            assert client is not None
            assert hasattr(client, "get")
            assert hasattr(client, "post")

    def test_context_manager_cleanup(self):
        """Test context manager properly cleans up resources."""
        with patch("rest_api_client.client.APIClient.close") as mock_close:
            with APIClient(base_url="https://api.example.com") as client:
                pass

            mock_close.assert_called_once()

    def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly."""
        with patch("rest_api_client.client.APIClient.close") as mock_close:
            try:
                with APIClient(base_url="https://api.example.com") as client:
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Ensure cleanup still happens
            mock_close.assert_called_once()
