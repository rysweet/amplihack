"""
Test suite for APIClient core functionality.

Tests basic GET/POST/PUT/DELETE operations, request/response dataclass usage,
error handling, and logging verification.

Testing Philosophy:
- Unit tests for core APIClient methods
- Mock HTTP responses using responses library
- Verify logging at appropriate levels
- Test error handling for various HTTP status codes
"""

import logging

import pytest
import responses

from amplihack.utils.api_client import (
    APIClient,
    APIRequest,
    APIResponse,
    HTTPError,
    RateLimitConfig,
    RequestError,
    RetryConfig,
)


class TestAPIClientBasicOperations:
    """Test basic HTTP operations (GET, POST, PUT, DELETE)"""

    @responses.activate
    def test_successful_get_request(self):
        """Test successful GET request returns proper APIResponse"""
        responses.add(
            responses.GET,
            "https://api.example.com/users/123",
            json={"id": 123, "name": "Alice"},
            status=200,
            headers={"Content-Type": "application/json"},
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users/123")

        # Verify APIResponse dataclass fields
        assert isinstance(response, APIResponse)
        assert response.status_code == 200
        assert response.data == {"id": 123, "name": "Alice"}
        assert response.headers["Content-Type"] == "application/json"
        assert isinstance(response.elapsed_time, float)
        assert response.elapsed_time > 0

    @responses.activate
    def test_get_with_query_parameters(self):
        """Test GET request with query parameters"""
        responses.add(
            responses.GET,
            "https://api.example.com/users?page=2&limit=50",
            json={"users": [], "total": 0},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users", params={"page": 2, "limit": 50})

        assert response.status_code == 200
        assert response.data == {"users": [], "total": 0}

    @responses.activate
    def test_get_with_custom_headers(self):
        """Test GET request with custom headers"""

        def request_callback(request):
            # Verify custom header was sent
            assert request.headers["Authorization"] == "Bearer token123"
            return (200, {}, '{"success": true}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/protected",
            callback=request_callback,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/protected", headers={"Authorization": "Bearer token123"})

        assert response.status_code == 200

    @responses.activate
    def test_successful_post_request_with_json(self):
        """Test successful POST request with JSON body"""
        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 456, "name": "Bob", "email": "bob@example.com"},
            status=201,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.post("/users", json={"name": "Bob", "email": "bob@example.com"})

        assert response.status_code == 201
        assert response.data["id"] == 456
        assert response.data["name"] == "Bob"

    @responses.activate
    def test_post_with_form_data(self):
        """Test POST request with form data"""

        def request_callback(request):
            # Verify form data was sent
            assert "name=Alice" in request.body
            return (200, {}, '{"success": true}')

        responses.add_callback(
            responses.POST,
            "https://api.example.com/users",
            callback=request_callback,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.post("/users", data={"name": "Alice", "email": "alice@example.com"})

        assert response.status_code == 200

    @responses.activate
    def test_successful_put_request(self):
        """Test successful PUT request"""
        responses.add(
            responses.PUT,
            "https://api.example.com/users/123",
            json={"id": 123, "name": "Alice Updated"},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.put("/users/123", json={"name": "Alice Updated"})

        assert response.status_code == 200
        assert response.data["name"] == "Alice Updated"

    @responses.activate
    def test_successful_delete_request(self):
        """Test successful DELETE request"""
        responses.add(
            responses.DELETE,
            "https://api.example.com/users/123",
            status=204,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.delete("/users/123")

        assert response.status_code == 204
        assert response.data is None  # No content on 204

    @responses.activate
    def test_delete_with_params(self):
        """Test DELETE request with query parameters"""
        responses.add(
            responses.DELETE,
            "https://api.example.com/users/123?confirm=true",
            status=204,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.delete("/users/123", params={"confirm": "true"})

        assert response.status_code == 204


class TestAPIRequestDataclass:
    """Test APIRequest dataclass usage"""

    @responses.activate
    def test_execute_with_api_request_dataclass(self):
        """Test executing request using APIRequest dataclass"""
        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 789, "name": "Charlie"},
            status=201,
        )

        client = APIClient(base_url="https://api.example.com")
        request = APIRequest(
            method="POST",
            url="/users",
            headers={"Authorization": "Bearer token123"},
            params={"notify": "true"},
            json={"name": "Charlie"},
        )

        response = client.execute(request)

        assert response.status_code == 201
        assert response.data["id"] == 789

    @responses.activate
    def test_api_request_with_all_fields(self):
        """Test APIRequest with all optional fields"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource?param=value",
            json={"result": "ok"},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        request = APIRequest(
            method="GET",
            url="/resource",
            headers={"X-Custom": "header-value"},
            params={"param": "value"},
            json=None,
            data=None,
        )

        response = client.execute(request)
        assert response.status_code == 200


class TestHTTPErrorHandling:
    """Test error handling for various HTTP status codes"""

    @responses.activate
    def test_404_raises_http_error(self):
        """Test 404 raises HTTPError with proper attributes"""
        responses.add(
            responses.GET,
            "https://api.example.com/notfound",
            json={"error": "Not Found"},
            status=404,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.get("/notfound")

        error = exc_info.value
        assert error.status_code == 404
        assert isinstance(error.message, str)
        assert error.response_data is not None

    @responses.activate
    def test_400_bad_request_error(self):
        """Test 400 Bad Request raises HTTPError"""
        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"error": "Invalid input"},
            status=400,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.post("/users", json={"invalid": "data"})

        assert exc_info.value.status_code == 400

    @responses.activate
    def test_401_unauthorized_error(self):
        """Test 401 Unauthorized raises HTTPError"""
        responses.add(
            responses.GET,
            "https://api.example.com/protected",
            json={"error": "Unauthorized"},
            status=401,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.get("/protected")

        assert exc_info.value.status_code == 401

    @responses.activate
    def test_403_forbidden_error(self):
        """Test 403 Forbidden raises HTTPError"""
        responses.add(
            responses.GET,
            "https://api.example.com/forbidden",
            json={"error": "Forbidden"},
            status=403,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.get("/forbidden")

        assert exc_info.value.status_code == 403

    @responses.activate
    def test_500_server_error(self):
        """Test 500 Internal Server Error raises HTTPError"""
        responses.add(
            responses.GET,
            "https://api.example.com/error",
            json={"error": "Internal Server Error"},
            status=500,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.get("/error")

        assert exc_info.value.status_code == 500

    @responses.activate
    def test_http_error_with_text_response(self):
        """Test HTTPError handles non-JSON error responses"""
        responses.add(
            responses.GET,
            "https://api.example.com/error",
            body="Plain text error message",
            status=500,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.get("/error")

        error = exc_info.value
        assert error.status_code == 500
        assert (
            "Plain text error message" in error.message
            or error.response_data == "Plain text error message"
        )


class TestNetworkErrorHandling:
    """Test handling of network and connection errors"""

    def test_connection_error_raises_request_error(self):
        """Test connection failures raise RequestError"""
        client = APIClient(base_url="https://invalid-domain-that-does-not-exist-12345.com")

        with pytest.raises(RequestError):
            client.get("/resource")

    def test_timeout_raises_request_error(self):
        """Test request timeout raises RequestError"""
        client = APIClient(
            base_url="https://httpbin.org",
            default_timeout=1.0,  # Very short timeout to trigger timeout
        )

        with pytest.raises(RequestError):
            client.get("/delay/10")  # Endpoint that delays 10 seconds

    @responses.activate
    def test_invalid_json_response_handled(self):
        """Test invalid JSON response is handled gracefully"""
        responses.add(
            responses.GET,
            "https://api.example.com/invalid",
            body="Not valid JSON {{{",
            status=200,
            headers={"Content-Type": "application/json"},
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/invalid")

        # Should return text when JSON parsing fails
        assert response.status_code == 200
        assert response.data is None or isinstance(response.data, str)
        assert response.text == "Not valid JSON {{{"


class TestClientConfiguration:
    """Test APIClient configuration options"""

    def test_client_with_default_headers(self):
        """Test client applies default headers to all requests"""

        def request_callback(request):
            assert request.headers["User-Agent"] == "MyApp/1.0"
            assert request.headers["X-API-Key"] == "secret123"
            return (200, {}, '{"success": true}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/resource",
            callback=request_callback,
        )

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={
                "User-Agent": "MyApp/1.0",
                "X-API-Key": "secret123",
            },
        )

        with responses.RequestsMock() as rsps:
            rsps.add_callback(
                responses.GET,
                "https://api.example.com/resource",
                callback=request_callback,
            )
            client.get("/resource")

    def test_client_with_custom_timeout(self):
        """Test client respects custom timeout setting"""
        client = APIClient(
            base_url="https://api.example.com",
            timeout=60.0,
        )

        # Verify timeout is stored
        assert client.timeout == 60.0

    def test_client_with_ssl_disabled(self):
        """Test client can disable SSL verification"""
        client = APIClient(
            base_url="https://api.example.com",
            verify_ssl=False,
        )

        # Verify SSL setting is stored
        assert client.verify_ssl is False

    def test_client_with_retry_config(self):
        """Test client accepts custom RetryConfig"""
        retry_config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=retry_config,
        )

        # Verify retry config is stored
        assert client.retry_config.max_retries == 5
        assert client.retry_config.base_delay == 2.0

    def test_client_with_rate_limit_config(self):
        """Test client accepts custom RateLimitConfig"""
        rate_limit_config = RateLimitConfig(
            max_wait_time=600.0,
            respect_retry_after=True,
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=rate_limit_config,
        )

        # Verify rate limit config is stored
        assert client.rate_limit_config.max_wait_time == 600.0
        assert client.rate_limit_config.respect_retry_after is True


class TestLogging:
    """Test logging functionality"""

    @responses.activate
    def test_request_logging_at_info_level(self, caplog):
        """Test requests are logged at INFO level"""
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": []},
            status=200,
        )

        with caplog.at_level(logging.INFO):
            client = APIClient(base_url="https://api.example.com")
            client.get("/users")

        # Verify request was logged
        log_messages = [record.message for record in caplog.records]
        assert any("GET" in msg and "/users" in msg for msg in log_messages)

    @responses.activate
    def test_response_logging_includes_status_code(self, caplog):
        """Test response logs include status code"""
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": []},
            status=200,
        )

        with caplog.at_level(logging.INFO):
            client = APIClient(base_url="https://api.example.com")
            client.get("/users")

        # Verify status code was logged
        log_messages = [record.message for record in caplog.records]
        assert any("200" in msg for msg in log_messages)

    @responses.activate
    def test_error_logging_at_error_level(self, caplog):
        """Test errors are logged at ERROR level"""
        responses.add(
            responses.GET,
            "https://api.example.com/error",
            json={"error": "Server error"},
            status=500,
        )

        with caplog.at_level(logging.ERROR):
            client = APIClient(base_url="https://api.example.com")
            try:
                client.get("/error")
            except HTTPError:
                pass

        # Verify error was logged at ERROR level
        error_logs = [record for record in caplog.records if record.levelno == logging.ERROR]
        assert len(error_logs) > 0

    @responses.activate
    def test_custom_logger(self, caplog):
        """Test client uses custom logger when provided"""
        custom_logger = logging.getLogger("custom_api_client")

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"data": "value"},
            status=200,
        )

        with caplog.at_level(logging.INFO, logger="custom_api_client"):
            client = APIClient(
                base_url="https://api.example.com",
                logger=custom_logger,
            )
            client.get("/resource")

        # Verify custom logger was used
        assert any(record.name == "custom_api_client" for record in caplog.records)

    @responses.activate
    def test_debug_logging_includes_headers(self, caplog):
        """Test DEBUG level includes request headers"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"data": "value"},
            status=200,
        )

        with caplog.at_level(logging.DEBUG):
            client = APIClient(
                base_url="https://api.example.com",
                default_headers={"X-Custom": "value"},
            )
            client.get("/resource")

        # Verify headers were logged at DEBUG level
        debug_logs = [record for record in caplog.records if record.levelno == logging.DEBUG]
        assert len(debug_logs) > 0


class TestResponseDataclass:
    """Test APIResponse dataclass attributes"""

    @responses.activate
    def test_api_response_all_fields_present(self):
        """Test APIResponse contains all required fields"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"key": "value"},
            status=200,
            headers={"X-Custom": "header"},
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/resource")

        # Verify all dataclass fields are present
        assert hasattr(response, "status_code")
        assert hasattr(response, "headers")
        assert hasattr(response, "data")
        assert hasattr(response, "text")
        assert hasattr(response, "elapsed_time")

        # Verify types
        assert isinstance(response.status_code, int)
        assert isinstance(response.headers, dict)
        assert isinstance(response.data, (dict, list, str, type(None)))
        assert isinstance(response.text, str)
        assert isinstance(response.elapsed_time, float)

    @responses.activate
    def test_response_text_field(self):
        """Test APIResponse.text contains raw response text"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            body='{"key": "value"}',
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/resource")

        assert response.text == '{"key": "value"}'
        assert response.data == {"key": "value"}

    @responses.activate
    def test_response_headers_dict(self):
        """Test APIResponse.headers is a dictionary"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"data": "value"},
            status=200,
            headers={
                "Content-Type": "application/json",
                "X-RateLimit-Remaining": "100",
            },
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/resource")

        assert isinstance(response.headers, dict)
        assert response.headers["Content-Type"] == "application/json"
        assert "X-RateLimit-Remaining" in response.headers


class TestBaseURLHandling:
    """Test base URL handling and path joining"""

    @responses.activate
    def test_base_url_without_trailing_slash(self):
        """Test base URL without trailing slash works correctly"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/resource")

        assert response.status_code == 200

    @responses.activate
    def test_base_url_with_trailing_slash(self):
        """Test base URL with trailing slash works correctly"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com/")
        response = client.get("resource")  # Path without leading slash

        assert response.status_code == 200

    @responses.activate
    def test_path_without_leading_slash(self):
        """Test path without leading slash works correctly"""
        responses.add(
            responses.GET,
            "https://api.example.com/api/v1/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com/api/v1")
        response = client.get("resource")

        assert response.status_code == 200
