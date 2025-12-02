"""Unit tests for Request and Response models.

Testing pyramid: 60% unit tests (these tests)
"""

import pytest

from api_client.models import Request, Response


class TestRequest:
    """Tests for Request data model."""

    def test_create_minimal_request(self):
        """Test creating request with minimal parameters."""
        request = Request(method="GET", endpoint="/users")
        assert request.method == "GET"
        assert request.endpoint == "/users"
        assert request.data is None
        assert request.params is None
        assert request.headers is None
        assert request.timeout == 30.0

    def test_create_full_request(self):
        """Test creating request with all parameters."""
        request = Request(
            method="POST",
            endpoint="/users",
            data={"name": "Alice"},
            params={"filter": "active"},
            headers={"Authorization": "Bearer token"},
            timeout=60.0,
        )
        assert request.method == "POST"
        assert request.data == {"name": "Alice"}
        assert request.params == {"filter": "active"}
        assert request.headers == {"Authorization": "Bearer token"}
        assert request.timeout == 60.0

    def test_immutable(self):
        """Test that Request is immutable."""
        request = Request(method="GET", endpoint="/users")
        with pytest.raises(AttributeError):  # Frozen dataclass raises AttributeError
            request.method = "POST"  # type: ignore

    def test_validate_empty_method(self):
        """Test that empty method raises ValueError."""
        with pytest.raises(ValueError, match="HTTP method cannot be empty"):
            Request(method="", endpoint="/users")

    def test_validate_negative_timeout(self):
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            Request(method="GET", endpoint="/users", timeout=-1.0)

    def test_validate_zero_timeout(self):
        """Test that zero timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            Request(method="GET", endpoint="/users", timeout=0.0)

    def test_with_headers(self):
        """Test adding headers to request."""
        request = Request(
            method="GET",
            endpoint="/users",
            headers={"Authorization": "Bearer token"},
        )
        new_request = request.with_headers({"X-Custom": "value"})

        # Original unchanged
        assert "X-Custom" not in (request.headers or {})

        # New request has both headers
        assert new_request.headers == {
            "Authorization": "Bearer token",
            "X-Custom": "value",
        }

    def test_with_headers_override(self):
        """Test that with_headers overrides existing headers."""
        request = Request(
            method="GET",
            endpoint="/users",
            headers={"Authorization": "Bearer old"},
        )
        new_request = request.with_headers({"Authorization": "Bearer new"})
        assert new_request.headers == {"Authorization": "Bearer new"}


class TestResponse:
    """Tests for Response data model."""

    def test_create_minimal_response(self):
        """Test creating response with minimal parameters."""
        response = Response(status_code=200, data=None, raw_text="")
        assert response.status_code == 200
        assert response.data is None
        assert response.raw_text == ""
        assert response.headers == {}
        assert response.elapsed_seconds == 0.0

    def test_create_full_response(self):
        """Test creating response with all parameters."""
        response = Response(
            status_code=200,
            data={"id": 123},
            raw_text='{"id": 123}',
            headers={"Content-Type": "application/json"},
            elapsed_seconds=0.5,
        )
        assert response.status_code == 200
        assert response.data == {"id": 123}
        assert response.raw_text == '{"id": 123}'
        assert response.headers == {"Content-Type": "application/json"}
        assert response.elapsed_seconds == 0.5

    def test_immutable(self):
        """Test that Response is immutable."""
        response = Response(status_code=200, data=None, raw_text="")
        with pytest.raises(AttributeError):  # Frozen dataclass raises AttributeError
            response.status_code = 404  # type: ignore

    def test_validate_invalid_status_code_low(self):
        """Test that status code < 100 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid HTTP status code"):
            Response(status_code=99, data=None, raw_text="")

    def test_validate_invalid_status_code_high(self):
        """Test that status code >= 600 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid HTTP status code"):
            Response(status_code=600, data=None, raw_text="")

    def test_is_success_2xx(self):
        """Test is_success for 2xx status codes."""
        assert Response(status_code=200, data=None, raw_text="").is_success
        assert Response(status_code=201, data=None, raw_text="").is_success
        assert Response(status_code=299, data=None, raw_text="").is_success

    def test_is_success_not_2xx(self):
        """Test is_success for non-2xx status codes."""
        assert not Response(status_code=199, data=None, raw_text="").is_success
        assert not Response(status_code=300, data=None, raw_text="").is_success
        assert not Response(status_code=404, data=None, raw_text="").is_success
        assert not Response(status_code=500, data=None, raw_text="").is_success

    def test_is_client_error(self):
        """Test is_client_error for 4xx status codes."""
        assert Response(status_code=400, data=None, raw_text="").is_client_error
        assert Response(status_code=404, data=None, raw_text="").is_client_error
        assert Response(status_code=499, data=None, raw_text="").is_client_error
        assert not Response(status_code=200, data=None, raw_text="").is_client_error
        assert not Response(status_code=500, data=None, raw_text="").is_client_error

    def test_is_server_error(self):
        """Test is_server_error for 5xx status codes."""
        assert Response(status_code=500, data=None, raw_text="").is_server_error
        assert Response(status_code=503, data=None, raw_text="").is_server_error
        assert Response(status_code=599, data=None, raw_text="").is_server_error
        assert not Response(status_code=200, data=None, raw_text="").is_server_error
        assert not Response(status_code=404, data=None, raw_text="").is_server_error
