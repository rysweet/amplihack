"""Unit tests for API data models.

Tests APIRequest and APIResponse dataclasses following TDD methodology.
These tests will FAIL until the models are implemented.

Testing Pyramid: Unit tests (60%)
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock


class TestAPIRequest:
    """Test APIRequest dataclass."""

    def test_api_request_creation(self):
        """APIRequest should be created with required fields."""
        from amplihack.api.models import APIRequest

        request = APIRequest(method="GET", endpoint="/users")
        assert request.method == "GET"
        assert request.endpoint == "/users"
        assert request.params is None
        assert request.json_data is None
        assert request.headers is None

    def test_api_request_with_all_fields(self):
        """APIRequest should accept all optional fields."""
        from amplihack.api.models import APIRequest

        request = APIRequest(
            method="POST",
            endpoint="/users",
            params={"page": 1},
            json_data={"name": "Blackbeard"},
            headers={"Authorization": "Bearer token123"},
        )
        assert request.method == "POST"
        assert request.endpoint == "/users"
        assert request.params == {"page": 1}
        assert request.json_data == {"name": "Blackbeard"}
        assert request.headers == {"Authorization": "Bearer token123"}

    def test_api_request_to_dict(self):
        """APIRequest should convert to dictionary."""
        from amplihack.api.models import APIRequest

        request = APIRequest(
            method="GET",
            endpoint="/data",
            params={"limit": 10},
            headers={"User-Agent": "TestClient"},
        )
        request_dict = request.to_dict()

        assert isinstance(request_dict, dict)
        assert request_dict["method"] == "GET"
        assert request_dict["endpoint"] == "/data"
        assert request_dict["params"] == {"limit": 10}
        assert request_dict["headers"] == {"User-Agent": "TestClient"}

    def test_api_request_to_json(self):
        """APIRequest should convert to JSON string."""
        from amplihack.api.models import APIRequest

        request = APIRequest(method="POST", endpoint="/create", json_data={"value": 42})
        json_str = request.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["method"] == "POST"
        assert parsed["endpoint"] == "/create"
        assert parsed["json_data"] == {"value": 42}

    def test_api_request_json_is_formatted(self):
        """APIRequest JSON should be human-readable (indented)."""
        from amplihack.api.models import APIRequest

        request = APIRequest(method="GET", endpoint="/test")
        json_str = request.to_json()

        # Should contain newlines (indented)
        assert "\n" in json_str

    def test_api_request_with_none_values(self):
        """APIRequest should handle None values correctly."""
        from amplihack.api.models import APIRequest

        request = APIRequest(method="DELETE", endpoint="/resource", params=None, json_data=None)
        request_dict = request.to_dict()

        assert request_dict["params"] is None
        assert request_dict["json_data"] is None


class TestAPIResponse:
    """Test APIResponse dataclass."""

    def test_api_response_creation(self):
        """APIResponse should be created with required fields."""
        from amplihack.api.models import APIResponse

        response = APIResponse(status_code=200, headers={"Content-Type": "text/plain"})
        assert response.status_code == 200
        assert response.headers == {"Content-Type": "text/plain"}
        assert response.body is None
        assert response.elapsed_ms == 0

    def test_api_response_with_all_fields(self):
        """APIResponse should accept all fields."""
        from amplihack.api.models import APIResponse

        response = APIResponse(
            status_code=201,
            headers={"Location": "/users/123"},
            body={"id": 123, "name": "Anne Bonny"},
            elapsed_ms=234,
        )
        assert response.status_code == 201
        assert response.headers == {"Location": "/users/123"}
        assert response.body == {"id": 123, "name": "Anne Bonny"}
        assert response.elapsed_ms == 234

    def test_api_response_from_requests_response_json(self):
        """APIResponse should convert from requests.Response with JSON body."""
        from amplihack.api.models import APIResponse

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"users": [1, 2, 3]}
        mock_response.text = '{"users": [1, 2, 3]}'
        mock_response.elapsed = timedelta(milliseconds=543)

        response = APIResponse.from_requests_response(mock_response)

        assert response.status_code == 200
        assert response.headers == {"Content-Type": "application/json"}
        assert response.body == {"users": [1, 2, 3]}
        assert response.elapsed_ms == 543

    def test_api_response_from_requests_response_text(self):
        """APIResponse should handle non-JSON text response."""
        from amplihack.api.models import APIResponse

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Plain text response"
        mock_response.elapsed = timedelta(milliseconds=123)

        response = APIResponse.from_requests_response(mock_response)

        assert response.status_code == 200
        assert response.body == "Plain text response"
        assert response.elapsed_ms == 123

    def test_api_response_from_requests_response_empty(self):
        """APIResponse should handle empty response body."""
        from amplihack.api.models import APIResponse

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.json.side_effect = ValueError("No content")
        mock_response.text = ""
        mock_response.elapsed = timedelta(milliseconds=50)

        response = APIResponse.from_requests_response(mock_response)

        assert response.status_code == 204
        assert response.body is None
        assert response.elapsed_ms == 50

    def test_api_response_to_dict(self):
        """APIResponse should convert to dictionary."""
        from amplihack.api.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"data": "value"},
            elapsed_ms=100,
        )
        response_dict = response.to_dict()

        assert isinstance(response_dict, dict)
        assert response_dict["status_code"] == 200
        assert response_dict["body"] == {"data": "value"}
        assert response_dict["elapsed_ms"] == 100

    def test_api_response_to_json(self):
        """APIResponse should convert to JSON string."""
        from amplihack.api.models import APIResponse

        response = APIResponse(
            status_code=404, headers={"Content-Type": "text/plain"}, body="Not found"
        )
        json_str = response.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["status_code"] == 404
        assert parsed["body"] == "Not found"

    def test_api_response_is_success(self):
        """is_success() should return True for 2xx status codes."""
        from amplihack.api.models import APIResponse

        response_200 = APIResponse(status_code=200, headers={})
        response_201 = APIResponse(status_code=201, headers={})
        response_204 = APIResponse(status_code=204, headers={})
        response_299 = APIResponse(status_code=299, headers={})

        assert response_200.is_success() is True
        assert response_201.is_success() is True
        assert response_204.is_success() is True
        assert response_299.is_success() is True

    def test_api_response_is_success_false_for_non_2xx(self):
        """is_success() should return False for non-2xx status codes."""
        from amplihack.api.models import APIResponse

        response_199 = APIResponse(status_code=199, headers={})
        response_300 = APIResponse(status_code=300, headers={})
        response_400 = APIResponse(status_code=400, headers={})
        response_500 = APIResponse(status_code=500, headers={})

        assert response_199.is_success() is False
        assert response_300.is_success() is False
        assert response_400.is_success() is False
        assert response_500.is_success() is False

    def test_api_response_is_client_error(self):
        """is_client_error() should return True for 4xx status codes."""
        from amplihack.api.models import APIResponse

        response_400 = APIResponse(status_code=400, headers={})
        response_401 = APIResponse(status_code=401, headers={})
        response_404 = APIResponse(status_code=404, headers={})
        response_429 = APIResponse(status_code=429, headers={})
        response_499 = APIResponse(status_code=499, headers={})

        assert response_400.is_client_error() is True
        assert response_401.is_client_error() is True
        assert response_404.is_client_error() is True
        assert response_429.is_client_error() is True
        assert response_499.is_client_error() is True

    def test_api_response_is_client_error_false_for_non_4xx(self):
        """is_client_error() should return False for non-4xx status codes."""
        from amplihack.api.models import APIResponse

        response_200 = APIResponse(status_code=200, headers={})
        response_399 = APIResponse(status_code=399, headers={})
        response_500 = APIResponse(status_code=500, headers={})

        assert response_200.is_client_error() is False
        assert response_399.is_client_error() is False
        assert response_500.is_client_error() is False

    def test_api_response_is_server_error(self):
        """is_server_error() should return True for 5xx status codes."""
        from amplihack.api.models import APIResponse

        response_500 = APIResponse(status_code=500, headers={})
        response_502 = APIResponse(status_code=502, headers={})
        response_503 = APIResponse(status_code=503, headers={})
        response_504 = APIResponse(status_code=504, headers={})
        response_599 = APIResponse(status_code=599, headers={})

        assert response_500.is_server_error() is True
        assert response_502.is_server_error() is True
        assert response_503.is_server_error() is True
        assert response_504.is_server_error() is True
        assert response_599.is_server_error() is True

    def test_api_response_is_server_error_false_for_non_5xx(self):
        """is_server_error() should return False for non-5xx status codes."""
        from amplihack.api.models import APIResponse

        response_200 = APIResponse(status_code=200, headers={})
        response_400 = APIResponse(status_code=400, headers={})
        response_499 = APIResponse(status_code=499, headers={})
        response_600 = APIResponse(status_code=600, headers={})

        assert response_200.is_server_error() is False
        assert response_400.is_server_error() is False
        assert response_499.is_server_error() is False
        assert response_600.is_server_error() is False

    def test_api_response_convenience_methods_boundaries(self):
        """Test boundary conditions for convenience methods."""
        from amplihack.api.models import APIResponse

        # Boundary: 199/200
        response_199 = APIResponse(status_code=199, headers={})
        response_200 = APIResponse(status_code=200, headers={})
        assert response_199.is_success() is False
        assert response_200.is_success() is True

        # Boundary: 299/300
        response_299 = APIResponse(status_code=299, headers={})
        response_300 = APIResponse(status_code=300, headers={})
        assert response_299.is_success() is True
        assert response_300.is_success() is False

        # Boundary: 399/400
        response_399 = APIResponse(status_code=399, headers={})
        response_400 = APIResponse(status_code=400, headers={})
        assert response_399.is_client_error() is False
        assert response_400.is_client_error() is True

        # Boundary: 499/500
        response_499 = APIResponse(status_code=499, headers={})
        response_500 = APIResponse(status_code=500, headers={})
        assert response_499.is_server_error() is False
        assert response_500.is_server_error() is True


class TestDataModelSerialization:
    """Test serialization of data models."""

    def test_request_json_roundtrip(self):
        """APIRequest should serialize and deserialize correctly."""
        from amplihack.api.models import APIRequest

        original = APIRequest(
            method="POST",
            endpoint="/api/data",
            params={"key": "value"},
            json_data={"nested": {"data": 123}},
        )

        # Serialize to JSON
        json_str = original.to_json()

        # Deserialize from JSON
        data = json.loads(json_str)
        restored = APIRequest(**{k: v for k, v in data.items() if k != "headers"})

        assert restored.method == original.method
        assert restored.endpoint == original.endpoint
        assert restored.params == original.params
        assert restored.json_data == original.json_data

    def test_response_json_roundtrip(self):
        """APIResponse should serialize and deserialize correctly."""
        from amplihack.api.models import APIResponse

        original = APIResponse(
            status_code=200,
            headers={"X-Custom": "value"},
            body={"result": "success"},
            elapsed_ms=456,
        )

        # Serialize to JSON
        json_str = original.to_json()

        # Deserialize from JSON
        data = json.loads(json_str)
        restored = APIResponse(**data)

        assert restored.status_code == original.status_code
        assert restored.headers == original.headers
        assert restored.body == original.body
        assert restored.elapsed_ms == original.elapsed_ms

    def test_response_json_with_non_serializable_handles_gracefully(self):
        """APIResponse should handle non-serializable objects in to_json()."""
        from amplihack.api.models import APIResponse

        # datetime is not JSON serializable by default
        response = APIResponse(status_code=200, headers={"Date": datetime.now()}, body="test")

        # Should use default=str fallback
        json_str = response.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["status_code"] == 200


class TestDataModelEdgeCases:
    """Test edge cases and error conditions."""

    def test_api_request_empty_strings(self):
        """APIRequest should handle empty strings."""
        from amplihack.api.models import APIRequest

        request = APIRequest(method="", endpoint="")
        assert request.method == ""
        assert request.endpoint == ""

    def test_api_response_zero_elapsed_time(self):
        """APIResponse should handle zero elapsed time."""
        from amplihack.api.models import APIResponse

        response = APIResponse(status_code=200, headers={}, elapsed_ms=0)
        assert response.elapsed_ms == 0

    def test_api_response_large_elapsed_time(self):
        """APIResponse should handle large elapsed times."""
        from amplihack.api.models import APIResponse

        response = APIResponse(status_code=200, headers={}, elapsed_ms=300000)  # 5 min
        assert response.elapsed_ms == 300000

    def test_api_response_headers_dict_conversion(self):
        """APIResponse should convert headers to dict."""
        from amplihack.api.models import APIResponse

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json", "X-Custom": "val"}
        mock_response.json.side_effect = ValueError
        mock_response.text = ""
        mock_response.elapsed = timedelta(milliseconds=100)

        response = APIResponse.from_requests_response(mock_response)

        assert isinstance(response.headers, dict)
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["X-Custom"] == "val"

    def test_api_response_body_types(self):
        """APIResponse should support multiple body types."""
        from amplihack.api.models import APIResponse

        # Dict body (JSON)
        response_json = APIResponse(status_code=200, headers={}, body={"key": "value"})
        assert isinstance(response_json.body, dict)

        # String body (text)
        response_text = APIResponse(status_code=200, headers={}, body="plain text")
        assert isinstance(response_text.body, str)

        # None body (empty)
        response_empty = APIResponse(status_code=204, headers={}, body=None)
        assert response_empty.body is None
