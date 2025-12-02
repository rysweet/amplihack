"""Tests for APIRequest and APIResponse models.

Tests the request/response dataclasses using the actual implementation API:
- APIRequest(method, path, headers, params, body, json_body)
- APIResponse(status_code, headers, body, text, request)

Testing pyramid target: 60% unit tests
"""

import pytest


class TestAPIRequest:
    """Tests for APIRequest frozen dataclass."""

    def test_import_request_class(self) -> None:
        """Test that APIRequest can be imported."""
        from amplihack.utils.api_client.models import APIRequest

        assert APIRequest is not None

    def test_create_request_with_required_fields(self) -> None:
        """Test creating request with only required fields."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(
            method="GET",
            path="/users",
        )

        assert request.method == "GET"
        assert request.path == "/users"

    def test_create_request_with_all_fields(self) -> None:
        """Test creating request with all optional fields."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(
            method="POST",
            path="/users",
            headers={"Content-Type": "application/json"},
            params={"page": "1"},
            body=None,
            json_body={"name": "John", "email": "john@example.com"},
        )

        assert request.method == "POST"
        assert request.path == "/users"
        assert request.headers == {"Content-Type": "application/json"}
        assert request.params == {"page": "1"}
        assert request.json_body == {"name": "John", "email": "john@example.com"}

    def test_request_is_frozen_immutable(self) -> None:
        """Test that request is immutable (frozen dataclass)."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(method="GET", path="/users")

        with pytest.raises((AttributeError, TypeError)):
            request.method = "POST"  # type: ignore

        with pytest.raises((AttributeError, TypeError)):
            request.path = "/other"  # type: ignore

    def test_request_body_bytes(self) -> None:
        """Test request with raw bytes body."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(
            method="POST",
            path="/upload",
            body=b"binary content here",
        )

        assert request.body == b"binary content here"

    def test_request_body_string(self) -> None:
        """Test request with string body."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(
            method="POST",
            path="/data",
            body="plain text content",
        )

        assert request.body == "plain text content"


class TestAPIRequestValidation:
    """Tests for APIRequest validation."""

    def test_empty_method_raises_error(self) -> None:
        """Test that empty method raises ValueError."""
        from amplihack.utils.api_client.models import APIRequest

        with pytest.raises(ValueError, match="method"):
            APIRequest(method="", path="/users")

    def test_invalid_method_raises_error(self) -> None:
        """Test that invalid HTTP method raises ValueError."""
        from amplihack.utils.api_client.models import APIRequest

        with pytest.raises(ValueError, match="[Mm]ethod"):
            APIRequest(method="INVALID", path="/users")

    def test_valid_methods_accepted(self) -> None:
        """Test that all valid HTTP methods are accepted."""
        from amplihack.utils.api_client.models import APIRequest

        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

        for method in valid_methods:
            request = APIRequest(method=method, path="/test")
            assert request.method.upper() == method

    def test_method_case_normalized(self) -> None:
        """Test that method is normalized to uppercase."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(method="get", path="/users")
        assert request.method == "GET"

        request = APIRequest(method="Post", path="/users")
        assert request.method == "POST"

    def test_empty_path_raises_error(self) -> None:
        """Test that empty path raises ValueError."""
        from amplihack.utils.api_client.models import APIRequest

        with pytest.raises(ValueError, match="path"):
            APIRequest(method="GET", path="")

    def test_path_without_leading_slash_is_normalized(self) -> None:
        """Test that path without leading slash gets one added."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(method="GET", path="users")
        assert request.path == "/users"


class TestAPIResponse:
    """Tests for APIResponse frozen dataclass."""

    def test_import_response_class(self) -> None:
        """Test that APIResponse can be imported."""
        from amplihack.utils.api_client.models import APIResponse

        assert APIResponse is not None

    def test_create_response_with_required_fields(self) -> None:
        """Test creating response with only required fields."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={},
            body="",
        )

        assert response.status_code == 200
        assert response.headers == {}
        assert response.body == ""

    def test_create_response_with_all_fields(self) -> None:
        """Test creating response with all fields."""
        from amplihack.utils.api_client.models import APIRequest, APIResponse

        request = APIRequest(method="GET", path="/users")
        response = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"users": []}',
            request=request,
        )

        assert response.status_code == 200
        assert response.headers == {"Content-Type": "application/json"}
        assert response.body == '{"users": []}'
        assert response.request is request

    def test_response_is_frozen_immutable(self) -> None:
        """Test that response is immutable (frozen dataclass)."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(status_code=200, headers={}, body="")

        with pytest.raises((AttributeError, TypeError)):
            response.status_code = 404  # type: ignore

        with pytest.raises((AttributeError, TypeError)):
            response.body = "new body"  # type: ignore


class TestAPIResponseProperties:
    """Tests for APIResponse convenience properties."""

    def test_is_success_for_2xx_codes(self) -> None:
        """Test is_success returns True for 2xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [200, 201, 202, 204, 299]:
            response = APIResponse(status_code=status, headers={}, body="")
            assert response.is_success is True, f"Expected True for {status}"

    def test_is_success_false_for_non_2xx(self) -> None:
        """Test is_success returns False for non-2xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [100, 301, 400, 404, 500, 503]:
            response = APIResponse(status_code=status, headers={}, body="")
            assert response.is_success is False, f"Expected False for {status}"

    def test_is_client_error_for_4xx_codes(self) -> None:
        """Test is_client_error returns True for 4xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [400, 401, 403, 404, 429, 499]:
            response = APIResponse(status_code=status, headers={}, body="")
            assert response.is_client_error is True, f"Expected True for {status}"

    def test_is_server_error_for_5xx_codes(self) -> None:
        """Test is_server_error returns True for 5xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [500, 502, 503, 504, 599]:
            response = APIResponse(status_code=status, headers={}, body="")
            assert response.is_server_error is True, f"Expected True for {status}"

    def test_text_property(self) -> None:
        """Test text property returns body."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={},
            body="Hello, World!",
        )
        assert response.text == "Hello, World!"

    def test_text_property_handles_empty_body(self) -> None:
        """Test text property handles empty body."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(status_code=204, headers={}, body="")
        assert response.text == ""

    def test_json_property_parses_json(self) -> None:
        """Test json property parses JSON body."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"name": "John", "age": 30}',
        )
        assert response.json == {"name": "John", "age": 30}

    def test_json_property_returns_none_for_empty_body(self) -> None:
        """Test json property returns None for empty body."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(status_code=204, headers={}, body="")
        assert response.json is None

    def test_json_property_raises_for_invalid_json(self) -> None:
        """Test json property raises ValueError for invalid JSON."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={},
            body="not valid json",
        )
        with pytest.raises(ValueError, match="JSON"):
            _ = response.json


class TestAPIResponseNoneHandling:
    """Tests for None handling in APIResponse."""

    def test_none_request_allowed(self) -> None:
        """Test that request can be None."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={},
            body="",
            request=None,
        )
        assert response.request is None


class TestAPIResponseEquality:
    """Tests for APIResponse equality."""

    def test_responses_with_same_values_are_equal(self) -> None:
        """Test that responses with same values are equal."""
        from amplihack.utils.api_client.models import APIResponse

        response1 = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"ok": true}',
        )
        response2 = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"ok": true}',
        )

        assert response1 == response2

    def test_responses_with_different_status_not_equal(self) -> None:
        """Test that responses with different status codes are not equal."""
        from amplihack.utils.api_client.models import APIResponse

        response1 = APIResponse(status_code=200, headers={}, body="")
        response2 = APIResponse(status_code=201, headers={}, body="")

        assert response1 != response2
