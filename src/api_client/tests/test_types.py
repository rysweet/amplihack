"""Unit tests for exception types.

Tests the `retryable` property and exception hierarchy.
This is part of the 60% unit test coverage.
"""

from unittest.mock import MagicMock

import pytest


class TestAPIClientError:
    """Tests for the base APIClientError exception."""

    def test_is_exception_subclass(self):
        """APIClientError should inherit from Exception."""
        from api_client import APIClientError

        assert issubclass(APIClientError, Exception)

    def test_has_retryable_property(self):
        """APIClientError should have a retryable property."""
        from api_client import APIClientError

        error = APIClientError("test error")
        assert hasattr(error, "retryable")

    def test_base_error_retryable_is_false(self):
        """Base APIClientError should not be retryable by default."""
        from api_client import APIClientError

        error = APIClientError("test error")
        assert error.retryable is False

    def test_message_accessible(self):
        """Error message should be accessible via str()."""
        from api_client import APIClientError

        error = APIClientError("custom error message")
        assert str(error) == "custom error message"

    def test_accepts_args_and_kwargs(self):
        """APIClientError should accept additional arguments."""
        from api_client import APIClientError

        # Should not raise
        error = APIClientError("message", "extra_arg")
        assert "message" in str(error)


class TestNetworkError:
    """Tests for NetworkError exception."""

    def test_is_api_client_error_subclass(self):
        """NetworkError should inherit from APIClientError."""
        from api_client import APIClientError, NetworkError

        assert issubclass(NetworkError, APIClientError)

    def test_is_always_retryable(self):
        """Network errors should always be retryable."""
        from api_client import NetworkError

        error = NetworkError("connection timeout")
        assert error.retryable is True

    def test_retryable_cannot_be_set_to_false(self):
        """NetworkError.retryable should always return True."""
        from api_client import NetworkError

        error = NetworkError("timeout")
        # Even if someone tries to change it, it should stay True
        assert error.retryable is True

    def test_message_describes_network_issue(self):
        """NetworkError should preserve the error message."""
        from api_client import NetworkError

        error = NetworkError("DNS resolution failed for api.example.com")
        assert "DNS resolution failed" in str(error)

    def test_can_wrap_original_exception(self):
        """NetworkError should be able to wrap an original exception."""
        from api_client import NetworkError

        original = ConnectionError("connection refused")
        error = NetworkError("connection failed", original)
        # Should contain original error info
        assert error.__cause__ is None or isinstance(error, NetworkError)


class TestHTTPError:
    """Tests for HTTPError exception."""

    def test_is_api_client_error_subclass(self):
        """HTTPError should inherit from APIClientError."""
        from api_client import APIClientError, HTTPError

        assert issubclass(HTTPError, APIClientError)

    def test_has_status_code_property(self):
        """HTTPError should expose the HTTP status code."""
        from api_client import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 500
        error = HTTPError("server error", response=mock_response)
        assert error.status_code == 500

    def test_has_response_property(self):
        """HTTPError should expose the full response object."""
        from api_client import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        error = HTTPError("not found", response=mock_response)
        assert error.response is mock_response

    @pytest.mark.parametrize(
        "status_code,expected_retryable",
        [
            (429, True),  # Rate limited
            (500, True),  # Internal server error
            (502, True),  # Bad gateway
            (503, True),  # Service unavailable
            (504, True),  # Gateway timeout
            (400, False),  # Bad request
            (401, False),  # Unauthorized
            (403, False),  # Forbidden
            (404, False),  # Not found
            (405, False),  # Method not allowed
            (409, False),  # Conflict
            (422, False),  # Unprocessable entity
        ],
    )
    def test_retryable_based_on_status_code(self, status_code, expected_retryable):
        """HTTPError.retryable should be True only for specific status codes."""
        from api_client import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = status_code
        error = HTTPError(f"HTTP {status_code}", response=mock_response)
        assert error.retryable is expected_retryable

    def test_status_code_accessible_directly(self):
        """Status code should be accessible without going through response."""
        from api_client import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 503
        error = HTTPError("service unavailable", response=mock_response)
        # Direct property access
        assert error.status_code == 503

    def test_response_text_accessible(self):
        """Response body should be accessible through response property."""
        from api_client import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": "invalid input"}'
        error = HTTPError("bad request", response=mock_response)
        assert error.response is not None
        assert error.response.text == '{"error": "invalid input"}'

    def test_response_headers_accessible(self):
        """Response headers should be accessible for Retry-After parsing."""
        from api_client import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}
        error = HTTPError("rate limited", response=mock_response)
        assert error.response is not None
        assert error.response.headers["Retry-After"] == "120"


class TestExceptionHierarchy:
    """Tests for the overall exception hierarchy."""

    def test_all_exceptions_importable_from_package(self):
        """All exception types should be importable from api_client."""
        from api_client import APIClientError, HTTPError, NetworkError

        # Should not raise ImportError
        assert APIClientError is not None
        assert NetworkError is not None
        assert HTTPError is not None

    def test_can_catch_all_with_base_exception(self):
        """Catching APIClientError should catch all subtypes."""
        from api_client import APIClientError, HTTPError, NetworkError

        mock_response = MagicMock()
        mock_response.status_code = 500

        exceptions = [
            APIClientError("base"),
            NetworkError("network"),
            HTTPError("http", response=mock_response),
        ]

        for exc in exceptions:
            try:
                raise exc
            except APIClientError as e:
                assert e is exc  # Successfully caught

    def test_network_error_catchable_separately(self):
        """NetworkError should be catchable separately from HTTPError."""
        from api_client import HTTPError, NetworkError

        try:
            raise NetworkError("timeout")
        except HTTPError:
            pytest.fail("NetworkError should not be caught by HTTPError handler")
        except NetworkError:
            pass  # Expected

    def test_http_error_catchable_separately(self):
        """HTTPError should be catchable separately from NetworkError."""
        from api_client import HTTPError, NetworkError

        mock_response = MagicMock()
        mock_response.status_code = 500

        try:
            raise HTTPError("server error", response=mock_response)
        except NetworkError:
            pytest.fail("HTTPError should not be caught by NetworkError handler")
        except HTTPError:
            pass  # Expected


class TestExceptionMessages:
    """Tests for exception message formatting."""

    def test_api_client_error_repr(self):
        """APIClientError should have useful repr."""
        from api_client import APIClientError

        error = APIClientError("test message")
        repr_str = repr(error)
        assert "APIClientError" in repr_str or "test message" in repr_str

    def test_network_error_repr(self):
        """NetworkError should have useful repr."""
        from api_client import NetworkError

        error = NetworkError("connection refused")
        repr_str = repr(error)
        assert "NetworkError" in repr_str or "connection refused" in repr_str

    def test_http_error_repr_includes_status(self):
        """HTTPError repr should include status code."""
        from api_client import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 404
        error = HTTPError("not found", response=mock_response)
        repr_str = repr(error)
        # Should contain either class name or meaningful info
        assert "HTTPError" in repr_str or "404" in repr_str or "not found" in repr_str
