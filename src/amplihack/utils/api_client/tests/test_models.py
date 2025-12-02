"""Tests for APIRequest and APIResponse models.

Tests the request/response dataclasses using the actual implementation API:
- APIRequest(method, path, headers, params, json_body, timeout)
- APIResponse(status_code, headers, body, elapsed_ms, request_id)

Note: APIRequest does NOT have body (raw), text, or method normalization.
Note: APIResponse does NOT have request, body_bytes, body_string, or text (use body).

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
            json_body={"name": "John", "email": "john@example.com"},
            timeout=60.0,
        )

        assert request.method == "POST"
        assert request.path == "/users"
        assert request.headers == {"Content-Type": "application/json"}
        assert request.params == {"page": "1"}
        assert request.json_body == {"name": "John", "email": "john@example.com"}
        assert request.timeout == 60.0

    def test_request_is_frozen_immutable(self) -> None:
        """Test that request is immutable (frozen dataclass)."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(method="GET", path="/users")

        with pytest.raises((AttributeError, TypeError)):
            request.method = "POST"  # type: ignore

        with pytest.raises((AttributeError, TypeError)):
            request.path = "/other"  # type: ignore

    def test_request_default_values(self) -> None:
        """Test request default values for optional fields."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(method="GET", path="/test")

        # Default values should be empty collections or None
        assert request.headers == {}
        assert request.params == {}
        assert request.json_body is None
        assert request.timeout is None

    def test_request_with_list_json_body(self) -> None:
        """Test request with list as JSON body."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(
            method="POST",
            path="/items",
            json_body=[{"id": 1}, {"id": 2}],
        )

        assert request.json_body == [{"id": 1}, {"id": 2}]

    def test_request_with_various_param_types(self) -> None:
        """Test request with different parameter types."""
        from amplihack.utils.api_client.models import APIRequest

        request = APIRequest(
            method="GET",
            path="/search",
            params={"q": "test", "page": 1, "active": True, "limit": 10.5, "tag": None},
        )

        assert request.params["q"] == "test"
        assert request.params["page"] == 1
        assert request.params["active"] is True
        assert request.params["limit"] == 10.5
        assert request.params["tag"] is None


class TestAPIResponse:
    """Tests for APIResponse frozen dataclass."""

    def test_import_response_class(self) -> None:
        """Test that APIResponse can be imported."""
        from amplihack.utils.api_client.models import APIResponse

        assert APIResponse is not None

    def test_create_response_with_required_fields(self) -> None:
        """Test creating response with required fields."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={},
            body="",
            elapsed_ms=100.0,
        )

        assert response.status_code == 200
        assert response.headers == {}
        assert response.body == ""
        assert response.elapsed_ms == 100.0

    def test_create_response_with_all_fields(self) -> None:
        """Test creating response with all fields."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"users": []}',
            elapsed_ms=150.5,
            request_id="req-123",
        )

        assert response.status_code == 200
        assert response.headers == {"Content-Type": "application/json"}
        assert response.body == '{"users": []}'
        assert response.elapsed_ms == 150.5
        assert response.request_id == "req-123"

    def test_response_is_frozen_immutable(self) -> None:
        """Test that response is immutable (frozen dataclass)."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(status_code=200, headers={}, body="", elapsed_ms=100.0)

        with pytest.raises((AttributeError, TypeError)):
            response.status_code = 404  # type: ignore

        with pytest.raises((AttributeError, TypeError)):
            response.body = "new body"  # type: ignore

    def test_response_request_id_default(self) -> None:
        """Test response request_id defaults to None."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(status_code=200, headers={}, body="", elapsed_ms=100.0)
        assert response.request_id is None


class TestAPIResponseProperties:
    """Tests for APIResponse convenience properties."""

    def test_is_success_for_2xx_codes(self) -> None:
        """Test is_success returns True for 2xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [200, 201, 202, 204, 299]:
            response = APIResponse(status_code=status, headers={}, body="", elapsed_ms=100.0)
            assert response.is_success is True, f"Expected True for {status}"

    def test_is_success_false_for_non_2xx(self) -> None:
        """Test is_success returns False for non-2xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [100, 301, 400, 404, 500, 503]:
            response = APIResponse(status_code=status, headers={}, body="", elapsed_ms=100.0)
            assert response.is_success is False, f"Expected False for {status}"

    def test_is_client_error_for_4xx_codes(self) -> None:
        """Test is_client_error returns True for 4xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [400, 401, 403, 404, 429, 499]:
            response = APIResponse(status_code=status, headers={}, body="", elapsed_ms=100.0)
            assert response.is_client_error is True, f"Expected True for {status}"

    def test_is_server_error_for_5xx_codes(self) -> None:
        """Test is_server_error returns True for 5xx status codes."""
        from amplihack.utils.api_client.models import APIResponse

        for status in [500, 502, 503, 504, 599]:
            response = APIResponse(status_code=status, headers={}, body="", elapsed_ms=100.0)
            assert response.is_server_error is True, f"Expected True for {status}"

    def test_json_property_parses_json(self) -> None:
        """Test json property parses JSON body."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"name": "John", "age": 30}',
            elapsed_ms=100.0,
        )
        assert response.json == {"name": "John", "age": 30}

    def test_json_property_returns_none_for_empty_body(self) -> None:
        """Test json property returns None for empty body."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(status_code=204, headers={}, body="", elapsed_ms=100.0)
        assert response.json is None

    def test_json_property_raises_for_invalid_json(self) -> None:
        """Test json property raises ValueError for invalid JSON."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={},
            body="not valid json",
            elapsed_ms=100.0,
        )
        with pytest.raises(ValueError, match="JSON"):
            _ = response.json

    def test_json_property_with_array(self) -> None:
        """Test json property with JSON array."""
        from amplihack.utils.api_client.models import APIResponse

        response = APIResponse(
            status_code=200,
            headers={},
            body='[{"id": 1}, {"id": 2}]',
            elapsed_ms=100.0,
        )
        assert response.json == [{"id": 1}, {"id": 2}]


class TestAPIResponseEquality:
    """Tests for APIResponse equality."""

    def test_responses_with_same_values_are_equal(self) -> None:
        """Test that responses with same values are equal."""
        from amplihack.utils.api_client.models import APIResponse

        response1 = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"ok": true}',
            elapsed_ms=100.0,
        )
        response2 = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"ok": true}',
            elapsed_ms=100.0,
        )

        assert response1 == response2

    def test_responses_with_different_status_not_equal(self) -> None:
        """Test that responses with different status codes are not equal."""
        from amplihack.utils.api_client.models import APIResponse

        response1 = APIResponse(status_code=200, headers={}, body="", elapsed_ms=100.0)
        response2 = APIResponse(status_code=201, headers={}, body="", elapsed_ms=100.0)

        assert response1 != response2

    def test_responses_with_different_elapsed_ms_not_equal(self) -> None:
        """Test that responses with different elapsed_ms are not equal."""
        from amplihack.utils.api_client.models import APIResponse

        response1 = APIResponse(status_code=200, headers={}, body="", elapsed_ms=100.0)
        response2 = APIResponse(status_code=200, headers={}, body="", elapsed_ms=200.0)

        assert response1 != response2

    def test_responses_with_different_request_id_not_equal(self) -> None:
        """Test that responses with different request_id are not equal."""
        from amplihack.utils.api_client.models import APIResponse

        response1 = APIResponse(
            status_code=200, headers={}, body="", elapsed_ms=100.0, request_id="req-1"
        )
        response2 = APIResponse(
            status_code=200, headers={}, body="", elapsed_ms=100.0, request_id="req-2"
        )

        assert response1 != response2
