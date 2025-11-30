"""Unit tests for request/response models."""

from dataclasses import FrozenInstanceError

import pytest

# These imports will fail initially (TDD)
from rest_api_client.models import APIError, Request, RequestMethod, Response


class TestRequestModel:
    """Test Request dataclass."""

    def test_create_request_minimal(self):
        """Test creating request with minimal parameters."""
        request = Request(method=RequestMethod.GET, url="/users")
        assert request.method == RequestMethod.GET
        assert request.url == "/users"
        assert request.headers == {}
        assert request.params == {}
        assert request.json is None
        assert request.data is None
        assert request.timeout == 30

    def test_create_request_full(self):
        """Test creating request with all parameters."""
        headers = {"Authorization": "Bearer token"}
        params = {"page": 1, "limit": 10}
        json_data = {"name": "John"}

        request = Request(
            method=RequestMethod.POST,
            url="/users",
            headers=headers,
            params=params,
            json=json_data,
            timeout=60,
        )
        assert request.method == RequestMethod.POST
        assert request.headers == headers
        assert request.params == params
        assert request.json == json_data
        assert request.timeout == 60

    def test_request_immutable(self):
        """Test that Request is immutable (frozen)."""
        request = Request(method=RequestMethod.GET, url="/test")
        with pytest.raises(FrozenInstanceError):
            request.url = "/new-url"

    def test_request_method_enum(self):
        """Test RequestMethod enum values."""
        assert RequestMethod.GET.value == "GET"
        assert RequestMethod.POST.value == "POST"
        assert RequestMethod.PUT.value == "PUT"
        assert RequestMethod.DELETE.value == "DELETE"
        assert RequestMethod.PATCH.value == "PATCH"

    def test_request_validation(self):
        """Test request validation."""
        # Empty URL should raise
        with pytest.raises(ValueError, match="URL cannot be empty"):
            Request(method=RequestMethod.GET, url="")

        # Invalid timeout should raise
        with pytest.raises(ValueError, match="Timeout must be positive"):
            Request(method=RequestMethod.GET, url="/test", timeout=-1)


class TestResponseModel:
    """Test Response dataclass."""

    def test_create_response(self):
        """Test creating response."""
        headers = {"Content-Type": "application/json"}
        json_data = {"id": 1, "name": "Test"}

        response = Response(
            status_code=200,
            headers=headers,
            json=json_data,
            text='{"id": 1, "name": "Test"}',
            elapsed=0.5,
            url="https://api.example.com/users/1",
        )

        assert response.status_code == 200
        assert response.headers == headers
        assert response.json == json_data
        assert response.elapsed == 0.5
        assert response.url == "https://api.example.com/users/1"

    def test_response_is_success(self):
        """Test is_success property."""
        success_response = Response(
            status_code=200,
            headers={},
            json={},
            text="",
            elapsed=0.1,
            url="https://api.example.com",
        )
        assert success_response.is_success is True

        error_response = Response(
            status_code=404,
            headers={},
            json={},
            text="",
            elapsed=0.1,
            url="https://api.example.com",
        )
        assert error_response.is_success is False

    def test_response_is_error(self):
        """Test is_error property."""
        success_response = Response(
            status_code=200,
            headers={},
            json={},
            text="",
            elapsed=0.1,
            url="https://api.example.com",
        )
        assert success_response.is_error is False

        error_response = Response(
            status_code=500,
            headers={},
            json={},
            text="",
            elapsed=0.1,
            url="https://api.example.com",
        )
        assert error_response.is_error is True

    def test_response_immutable(self):
        """Test that Response is immutable."""
        response = Response(
            status_code=200,
            headers={},
            json={},
            text="",
            elapsed=0.1,
            url="https://api.example.com",
        )
        with pytest.raises(FrozenInstanceError):
            response.status_code = 404


class TestAPIError:
    """Test APIError dataclass."""

    def test_create_api_error(self):
        """Test creating APIError."""
        error = APIError(
            message="Not found",
            status_code=404,
            response_data={"error": "Resource not found"},
            request_url="/users/999",
        )

        assert error.message == "Not found"
        assert error.status_code == 404
        assert error.response_data == {"error": "Resource not found"}
        assert error.request_url == "/users/999"

    def test_api_error_str(self):
        """Test APIError string representation."""
        error = APIError(
            message="Server error", status_code=500, response_data=None, request_url="/api/endpoint"
        )

        error_str = str(error)
        assert "500" in error_str
        assert "Server error" in error_str
        assert "/api/endpoint" in error_str

    def test_api_error_without_response_data(self):
        """Test APIError without response data."""
        error = APIError(
            message="Timeout", status_code=None, response_data=None, request_url="/slow-endpoint"
        )

        assert error.message == "Timeout"
        assert error.status_code is None
        assert error.response_data is None
