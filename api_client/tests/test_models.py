"""Tests for data models (Request and Response dataclasses).

TDD: These tests define the EXPECTED behavior of data models.
All tests should FAIL until api_client/models.py is implemented.

Testing pyramid: Unit tests (60% of total)
"""

import json
from dataclasses import FrozenInstanceError

import pytest  # type: ignore[import-not-found]


class TestRequestDataclass:
    """Test the Request dataclass."""

    def test_request_is_frozen(self):
        """Request should be immutable (frozen dataclass)."""
        from api_client.models import Request

        request = Request(
            method="GET", url="https://api.example.com/users", headers={"Accept": "*/*"}
        )

        with pytest.raises(FrozenInstanceError):
            request.method = "POST"  # type: ignore[misc]

    def test_request_required_fields(self):
        """Request requires method, url, and headers."""
        from api_client.models import Request

        request = Request(
            method="POST",
            url="https://api.example.com/data",
            headers={"Content-Type": "application/json"},
        )

        assert request.method == "POST"
        assert request.url == "https://api.example.com/data"
        assert request.headers == {"Content-Type": "application/json"}

    def test_request_params_optional(self):
        """Request params should be optional and default to None."""
        from api_client.models import Request

        request = Request(method="GET", url="/test", headers={})

        assert request.params is None

    def test_request_params_with_value(self):
        """Request params can be set to a dictionary."""
        from api_client.models import Request

        request = Request(
            method="GET",
            url="/search",
            headers={},
            params={"q": "test", "page": 1},
        )

        assert request.params == {"q": "test", "page": 1}

    def test_request_json_data_optional(self):
        """Request json_data should be optional and default to None."""
        from api_client.models import Request

        request = Request(method="POST", url="/test", headers={})

        assert request.json_data is None

    def test_request_json_data_with_value(self):
        """Request json_data can be set to a dictionary."""
        from api_client.models import Request

        request = Request(
            method="POST",
            url="/users",
            headers={"Content-Type": "application/json"},
            json_data={"name": "Test User", "email": "test@example.com"},
        )

        assert request.json_data == {"name": "Test User", "email": "test@example.com"}

    def test_request_data_optional(self):
        """Request data (raw bytes) should be optional and default to None."""
        from api_client.models import Request

        request = Request(method="POST", url="/upload", headers={})

        assert request.data is None

    def test_request_data_with_bytes(self):
        """Request data can be set to raw bytes."""
        from api_client.models import Request

        raw_data = b"binary content here"
        request = Request(
            method="POST",
            url="/upload",
            headers={"Content-Type": "application/octet-stream"},
            data=raw_data,
        )

        assert request.data == raw_data


class TestResponseDataclass:
    """Test the Response dataclass."""

    def test_response_is_frozen(self):
        """Response should be immutable (frozen dataclass)."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"ok": true}',
            elapsed_ms=150.5,
            request=request,
        )

        with pytest.raises(FrozenInstanceError):
            response.status_code = 404  # type: ignore[misc]

    def test_response_required_fields(self):
        """Response requires status_code, headers, body, elapsed_ms, and request."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/api/data", headers={})
        response = Response(
            status_code=200,
            headers={"Content-Type": "text/plain"},
            body=b"Hello, World!",
            elapsed_ms=42.5,
            request=request,
        )

        assert response.status_code == 200
        assert response.headers == {"Content-Type": "text/plain"}
        assert response.body == b"Hello, World!"
        assert response.elapsed_ms == 42.5
        assert response.request is request


class TestResponseJsonProperty:
    """Test Response.json_data property."""

    def test_json_data_parses_valid_json(self):
        """json_data should parse valid JSON body."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        json_body = {"users": [{"id": 1, "name": "Alice"}], "total": 1}
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(json_body).encode("utf-8"),
            elapsed_ms=100.0,
            request=request,
        )

        assert response.json_data == json_body

    def test_json_data_returns_none_for_non_json(self):
        """json_data should return None for non-JSON body."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=200,
            headers={"Content-Type": "text/html"},
            body=b"<html><body>Hello</body></html>",
            elapsed_ms=50.0,
            request=request,
        )

        assert response.json_data is None

    def test_json_data_returns_none_for_invalid_json(self):
        """json_data should return None for invalid JSON."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b"not valid json {",
            elapsed_ms=30.0,
            request=request,
        )

        assert response.json_data is None

    def test_json_data_returns_none_for_empty_body(self):
        """json_data should return None for empty body."""
        from api_client.models import Request, Response

        request = Request(method="DELETE", url="/resource/1", headers={})
        response = Response(
            status_code=204,
            headers={},
            body=b"",
            elapsed_ms=20.0,
            request=request,
        )

        assert response.json_data is None


class TestResponseTextProperty:
    """Test Response.text property."""

    def test_text_decodes_utf8(self):
        """text should decode body as UTF-8."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=200,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body="Hello, World! Emoji: \U0001f600".encode(),
            elapsed_ms=25.0,
            request=request,
        )

        assert response.text == "Hello, World! Emoji: \U0001f600"

    def test_text_handles_unicode(self):
        """text should handle various unicode characters."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        unicode_text = "Japanese: \u3053\u3093\u306b\u3061\u306f, Chinese: \u4f60\u597d"
        response = Response(
            status_code=200,
            headers={},
            body=unicode_text.encode("utf-8"),
            elapsed_ms=10.0,
            request=request,
        )

        assert response.text == unicode_text

    def test_text_returns_empty_string_for_empty_body(self):
        """text should return empty string for empty body."""
        from api_client.models import Request, Response

        request = Request(method="HEAD", url="/test", headers={})
        response = Response(
            status_code=200,
            headers={},
            body=b"",
            elapsed_ms=5.0,
            request=request,
        )

        assert response.text == ""

    def test_text_handles_invalid_utf8_with_replacement(self):
        """text should replace invalid UTF-8 bytes with replacement character."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        # Invalid UTF-8 sequence: 0xFF is not valid in UTF-8
        invalid_utf8 = b"Hello \xff World"
        response = Response(
            status_code=200,
            headers={},
            body=invalid_utf8,
            elapsed_ms=10.0,
            request=request,
        )

        # The invalid byte should be replaced with the Unicode replacement character
        result = response.text
        assert "Hello" in result
        assert "World" in result
        assert "\ufffd" in result  # Unicode replacement character


class TestResponseOkProperty:
    """Test Response.ok property."""

    def test_ok_returns_true_for_200(self):
        """ok should return True for 200 status."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=200,
            headers={},
            body=b"OK",
            elapsed_ms=10.0,
            request=request,
        )

        assert response.ok is True

    def test_ok_returns_true_for_201(self):
        """ok should return True for 201 Created."""
        from api_client.models import Request, Response

        request = Request(method="POST", url="/users", headers={})
        response = Response(
            status_code=201,
            headers={},
            body=b'{"id": 1}',
            elapsed_ms=50.0,
            request=request,
        )

        assert response.ok is True

    def test_ok_returns_true_for_204(self):
        """ok should return True for 204 No Content."""
        from api_client.models import Request, Response

        request = Request(method="DELETE", url="/users/1", headers={})
        response = Response(
            status_code=204,
            headers={},
            body=b"",
            elapsed_ms=30.0,
            request=request,
        )

        assert response.ok is True

    def test_ok_returns_true_for_299(self):
        """ok should return True for any 2xx status (boundary: 299)."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=299,
            headers={},
            body=b"",
            elapsed_ms=10.0,
            request=request,
        )

        assert response.ok is True

    def test_ok_returns_false_for_300(self):
        """ok should return False for 300 (redirect)."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=300,
            headers={"Location": "/new-location"},
            body=b"",
            elapsed_ms=10.0,
            request=request,
        )

        assert response.ok is False

    def test_ok_returns_false_for_400(self):
        """ok should return False for 400 Bad Request."""
        from api_client.models import Request, Response

        request = Request(method="POST", url="/test", headers={})
        response = Response(
            status_code=400,
            headers={},
            body=b'{"error": "Bad Request"}',
            elapsed_ms=15.0,
            request=request,
        )

        assert response.ok is False

    def test_ok_returns_false_for_404(self):
        """ok should return False for 404 Not Found."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/nonexistent", headers={})
        response = Response(
            status_code=404,
            headers={},
            body=b"Not Found",
            elapsed_ms=20.0,
            request=request,
        )

        assert response.ok is False

    def test_ok_returns_false_for_500(self):
        """ok should return False for 500 Internal Server Error."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/broken", headers={})
        response = Response(
            status_code=500,
            headers={},
            body=b"Internal Server Error",
            elapsed_ms=100.0,
            request=request,
        )

        assert response.ok is False

    def test_ok_returns_false_for_199(self):
        """ok should return False for status codes below 200."""
        from api_client.models import Request, Response

        request = Request(method="GET", url="/test", headers={})
        response = Response(
            status_code=199,
            headers={},
            body=b"",
            elapsed_ms=10.0,
            request=request,
        )

        assert response.ok is False


class TestModelsExport:
    """Test that models are properly exported."""

    def test_request_is_importable(self):
        """Request should be importable from models."""
        from api_client.models import Request  # noqa: F401

        assert True

    def test_response_is_importable(self):
        """Response should be importable from models."""
        from api_client.models import Response  # noqa: F401

        assert True
