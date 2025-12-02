"""Tests for Request/Response dataclass models.

TDD tests - these will FAIL until models.py is implemented.

Testing:
- Request dataclass creation and validation
- Response dataclass creation and immutability
- Field validation and type checking
- Serialization/deserialization
"""

from dataclasses import FrozenInstanceError

import pytest


class TestRequestModel:
    """Unit tests for Request dataclass."""

    def test_create_request_with_required_fields(self):
        """Request can be created with method and url."""
        from api_client.models import Request

        request = Request(method="GET", url="https://api.example.com/users")

        assert request.method == "GET"
        assert request.url == "https://api.example.com/users"

    def test_create_request_with_all_fields(self):
        """Request can be created with all optional fields."""
        from api_client.models import Request

        request = Request(
            method="POST",
            url="https://api.example.com/users",
            headers={"Content-Type": "application/json"},
            body={"name": "Test User"},
            params={"page": "1"},
            timeout=30,
        )

        assert request.method == "POST"
        assert request.url == "https://api.example.com/users"
        assert request.headers == {"Content-Type": "application/json"}
        assert request.body == {"name": "Test User"}
        assert request.params == {"page": "1"}
        assert request.timeout == 30

    def test_request_default_values(self):
        """Request has sensible defaults for optional fields."""
        from api_client.models import Request

        request = Request(method="GET", url="https://api.example.com/")

        assert request.headers is None or request.headers == {}
        assert request.body is None
        assert request.params is None or request.params == {}
        assert request.timeout is None or request.timeout > 0

    def test_request_is_frozen(self):
        """Request dataclass is immutable (frozen)."""
        from api_client.models import Request

        request = Request(method="GET", url="https://api.example.com/")

        with pytest.raises(FrozenInstanceError):
            request.method = "POST"

    def test_request_validates_method(self):
        """Request validates HTTP method is valid."""
        from api_client.models import Request

        # Valid methods should work
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            request = Request(method=method, url="https://api.example.com/")
            assert request.method == method

    def test_request_rejects_invalid_method(self):
        """Request rejects invalid HTTP methods."""
        from api_client.models import Request

        with pytest.raises(ValueError, match="Invalid HTTP method"):
            Request(method="INVALID", url="https://api.example.com/")

    def test_request_validates_url_not_empty(self):
        """Request validates URL is not empty."""
        from api_client.models import Request

        with pytest.raises(ValueError, match="URL cannot be empty"):
            Request(method="GET", url="")

    def test_request_validates_timeout_positive(self):
        """Request validates timeout is positive if provided."""
        from api_client.models import Request

        with pytest.raises(ValueError, match="Timeout must be positive"):
            Request(method="GET", url="https://api.example.com/", timeout=-1)

    def test_request_equality(self):
        """Two requests with same values are equal."""
        from api_client.models import Request

        request1 = Request(method="GET", url="https://api.example.com/users")
        request2 = Request(method="GET", url="https://api.example.com/users")

        assert request1 == request2

    def test_request_hashable(self):
        """Request can be used as dict key or in set."""
        from api_client.models import Request

        request = Request(method="GET", url="https://api.example.com/users")

        # Should be hashable
        request_set = {request}
        assert request in request_set

        request_dict = {request: "value"}
        assert request_dict[request] == "value"


class TestResponseModel:
    """Unit tests for Response dataclass."""

    def test_create_response_with_required_fields(self):
        """Response can be created with status_code and body."""
        from api_client.models import Response

        response = Response(status_code=200, body={"data": "test"})

        assert response.status_code == 200
        assert response.body == {"data": "test"}

    def test_create_response_with_all_fields(self):
        """Response can be created with all fields."""
        from api_client.models import Response

        response = Response(
            status_code=200,
            body={"data": "test"},
            headers={"Content-Type": "application/json"},
            elapsed_ms=150.5,
            request_id="req-123",
        )

        assert response.status_code == 200
        assert response.body == {"data": "test"}
        assert response.headers == {"Content-Type": "application/json"}
        assert response.elapsed_ms == 150.5
        assert response.request_id == "req-123"

    def test_response_is_frozen(self):
        """Response dataclass is immutable (frozen)."""
        from api_client.models import Response

        response = Response(status_code=200, body={})

        with pytest.raises(FrozenInstanceError):
            response.status_code = 404

    def test_response_is_success_2xx(self):
        """Response.is_success returns True for 2xx status codes."""
        from api_client.models import Response

        for status in [200, 201, 202, 204, 299]:
            response = Response(status_code=status, body={})
            assert response.is_success is True, f"Status {status} should be success"

    def test_response_is_success_non_2xx(self):
        """Response.is_success returns False for non-2xx status codes."""
        from api_client.models import Response

        for status in [100, 301, 400, 404, 500, 503]:
            response = Response(status_code=status, body={})
            assert response.is_success is False, f"Status {status} should not be success"

    def test_response_is_client_error(self):
        """Response.is_client_error returns True for 4xx status codes."""
        from api_client.models import Response

        for status in [400, 401, 403, 404, 422, 499]:
            response = Response(status_code=status, body={})
            assert response.is_client_error is True

        for status in [200, 301, 500]:
            response = Response(status_code=status, body={})
            assert response.is_client_error is False

    def test_response_is_server_error(self):
        """Response.is_server_error returns True for 5xx status codes."""
        from api_client.models import Response

        for status in [500, 502, 503, 504, 599]:
            response = Response(status_code=status, body={})
            assert response.is_server_error is True

        for status in [200, 404]:
            response = Response(status_code=status, body={})
            assert response.is_server_error is False

    def test_response_is_rate_limited(self):
        """Response.is_rate_limited returns True for 429 status code."""
        from api_client.models import Response

        response_429 = Response(status_code=429, body={})
        assert response_429.is_rate_limited is True

        response_200 = Response(status_code=200, body={})
        assert response_200.is_rate_limited is False

    def test_response_json_body(self):
        """Response.json returns body as dict when body is JSON."""
        from api_client.models import Response

        response = Response(status_code=200, body={"key": "value"})
        assert response.json() == {"key": "value"}

    def test_response_text_body(self):
        """Response.text returns body as string."""
        from api_client.models import Response

        response = Response(status_code=200, body="Plain text response")
        assert response.text == "Plain text response"

    def test_response_validates_status_code_range(self):
        """Response validates status_code is in valid HTTP range."""
        from api_client.models import Response

        # Valid status codes
        Response(status_code=100, body={})
        Response(status_code=599, body={})

        # Invalid status codes
        with pytest.raises(ValueError, match="Invalid status code"):
            Response(status_code=99, body={})

        with pytest.raises(ValueError, match="Invalid status code"):
            Response(status_code=600, body={})

    def test_response_equality(self):
        """Two responses with same values are equal."""
        from api_client.models import Response

        response1 = Response(status_code=200, body={"data": "test"})
        response2 = Response(status_code=200, body={"data": "test"})

        assert response1 == response2

    def test_response_retry_after_from_headers(self):
        """Response.retry_after extracts value from Retry-After header."""
        from api_client.models import Response

        response = Response(
            status_code=429,
            body={},
            headers={"Retry-After": "60"},
        )
        assert response.retry_after == 60

    def test_response_retry_after_missing(self):
        """Response.retry_after returns None when header missing."""
        from api_client.models import Response

        response = Response(status_code=429, body={})
        assert response.retry_after is None


class TestModelSerialization:
    """Tests for model serialization and deserialization."""

    def test_request_to_dict(self):
        """Request can be converted to dictionary."""
        from api_client.models import Request

        request = Request(
            method="POST",
            url="https://api.example.com/users",
            headers={"Content-Type": "application/json"},
            body={"name": "Test"},
        )

        request_dict = request.to_dict()

        assert request_dict["method"] == "POST"
        assert request_dict["url"] == "https://api.example.com/users"
        assert request_dict["headers"] == {"Content-Type": "application/json"}
        assert request_dict["body"] == {"name": "Test"}

    def test_response_to_dict(self):
        """Response can be converted to dictionary."""
        from api_client.models import Response

        response = Response(
            status_code=200,
            body={"data": "test"},
            headers={"Content-Type": "application/json"},
            elapsed_ms=100.0,
        )

        response_dict = response.to_dict()

        assert response_dict["status_code"] == 200
        assert response_dict["body"] == {"data": "test"}
        assert response_dict["headers"] == {"Content-Type": "application/json"}
        assert response_dict["elapsed_ms"] == 100.0

    def test_request_from_dict(self):
        """Request can be created from dictionary."""
        from api_client.models import Request

        data = {
            "method": "GET",
            "url": "https://api.example.com/users",
            "headers": {"Accept": "application/json"},
        }

        request = Request.from_dict(data)

        assert request.method == "GET"
        assert request.url == "https://api.example.com/users"
        assert request.headers == {"Accept": "application/json"}

    def test_response_from_dict(self):
        """Response can be created from dictionary."""
        from api_client.models import Response

        data = {
            "status_code": 201,
            "body": {"id": 1},
            "headers": {"Location": "/users/1"},
        }

        response = Response.from_dict(data)

        assert response.status_code == 201
        assert response.body == {"id": 1}
        assert response.headers == {"Location": "/users/1"}
