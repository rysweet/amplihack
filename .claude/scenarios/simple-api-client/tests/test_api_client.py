"""TDD Tests for simple-api-client.

These tests are written BEFORE the implementation exists.
All tests will fail initially - that's the point of TDD.

Testing Pyramid:
- 60% Unit tests (mocked requests) - Tests 1-7
- 30% Integration tests (real JSONPlaceholder) - Tests 8-9
- 10% E2E (full workflow) - Covered by integration tests
"""

from unittest.mock import Mock, patch

import pytest

# Import the module
from simple_api_client import DEFAULT_TIMEOUT, APIError, get, post

# =============================================================================
# Unit Tests (60%) - Mocked Requests
# =============================================================================


class TestGetFunction:
    """Unit tests for the get() function."""

    def test_get_returns_parsed_json(self):
        """GET request returns parsed JSON dict."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Test"}

        with patch("simple_api_client.requests.get", return_value=mock_response):
            result = get("https://example.com/api/posts/1")

        assert result == {"id": 1, "title": "Test"}

    def test_get_returns_list_json(self):
        """GET request returns parsed JSON list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]

        with patch("simple_api_client.requests.get", return_value=mock_response):
            result = get("https://example.com/api/posts")

        assert result == [{"id": 1}, {"id": 2}]

    def test_get_raises_on_network_error(self):
        """GET raises APIError on network failure."""
        import requests as req

        with patch(
            "simple_api_client.requests.get",
            side_effect=req.exceptions.ConnectionError("Network unreachable"),
        ):
            with pytest.raises(APIError) as exc_info:
                get("https://unreachable.invalid/api")

            assert "network" in exc_info.value.message.lower()
            assert exc_info.value.status_code is None

    def test_get_raises_on_http_error(self):
        """GET raises APIError on HTTP error status (404)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not Found")

        with patch("simple_api_client.requests.get", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                get("https://example.com/api/not-found")

            assert exc_info.value.status_code == 404

    def test_get_raises_on_invalid_json(self):
        """GET raises APIError when response is not valid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch("simple_api_client.requests.get", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                get("https://example.com/api/bad-json")

            assert "json" in exc_info.value.message.lower()

    def test_get_raises_on_timeout(self):
        """GET raises APIError on request timeout."""
        import requests as req

        with patch(
            "simple_api_client.requests.get",
            side_effect=req.exceptions.Timeout("Request timed out"),
        ):
            with pytest.raises(APIError) as exc_info:
                get("https://slow.example.com/api")

            assert "timed out" in exc_info.value.message.lower()
            assert exc_info.value.status_code is None

    def test_get_uses_default_timeout(self):
        """GET uses DEFAULT_TIMEOUT by default."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1}

        with patch("simple_api_client.requests.get", return_value=mock_response) as mock_get:
            get("https://example.com/api")
            mock_get.assert_called_once_with("https://example.com/api", timeout=DEFAULT_TIMEOUT)


class TestPostFunction:
    """Unit tests for the post() function."""

    def test_post_sends_json_body(self):
        """POST sends JSON Content-Type and body."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 101, "title": "New Post"}

        with patch("simple_api_client.requests.post", return_value=mock_response) as mock_post:
            data = {"title": "New Post", "body": "Content"}
            post("https://example.com/api/posts", data)

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs.get("json") == data

    def test_post_returns_parsed_response(self):
        """POST returns parsed JSON response."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 101, "title": "Created"}

        with patch("simple_api_client.requests.post", return_value=mock_response):
            result = post("https://example.com/api/posts", {"title": "Test"})

        assert result == {"id": 101, "title": "Created"}

    def test_post_raises_on_network_error(self):
        """POST raises APIError on network failure."""
        import requests as req

        with patch(
            "simple_api_client.requests.post",
            side_effect=req.exceptions.ConnectionError("Network down"),
        ):
            with pytest.raises(APIError) as exc_info:
                post("https://unreachable.invalid/api", {"data": "test"})

            assert exc_info.value.status_code is None

    def test_post_raises_on_http_error(self):
        """POST raises APIError on HTTP error status (500)."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")

        with patch("simple_api_client.requests.post", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                post("https://example.com/api/posts", {"title": "Test"})

            assert exc_info.value.status_code == 500

    def test_post_raises_on_timeout(self):
        """POST raises APIError on request timeout."""
        import requests as req

        with patch(
            "simple_api_client.requests.post",
            side_effect=req.exceptions.Timeout("Request timed out"),
        ):
            with pytest.raises(APIError) as exc_info:
                post("https://slow.example.com/api", {"data": "test"})

            assert "timed out" in exc_info.value.message.lower()
            assert exc_info.value.status_code is None


class TestAPIError:
    """Unit tests for the APIError exception."""

    def test_api_error_has_message_and_status(self):
        """APIError has message and status_code attributes."""
        error = APIError("Something went wrong", status_code=404)

        assert error.message == "Something went wrong"
        assert error.status_code == 404

    def test_api_error_with_none_status(self):
        """APIError can have None status_code for non-HTTP errors."""
        error = APIError("Network error", status_code=None)

        assert error.message == "Network error"
        assert error.status_code is None

    def test_api_error_is_exception(self):
        """APIError is a proper Exception and can be raised/caught."""
        with pytest.raises(APIError):
            raise APIError("Test error", status_code=500)

    def test_api_error_str_representation(self):
        """APIError has useful string representation."""
        error = APIError("Not found", status_code=404)
        error_str = str(error)

        assert "Not found" in error_str


# =============================================================================
# Integration Tests (30%) - Real API Calls
# =============================================================================


@pytest.mark.integration
class TestIntegrationWithJSONPlaceholder:
    """Integration tests using real JSONPlaceholder API.

    These tests make actual network calls to jsonplaceholder.typicode.com.
    Mark with @pytest.mark.integration for selective running.
    """

    def test_integration_get_single_post(self):
        """Real GET request to JSONPlaceholder returns expected structure."""
        result = get("https://jsonplaceholder.typicode.com/posts/1")

        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == 1
        assert "title" in result
        assert "body" in result
        assert "userId" in result

    def test_integration_get_post_list(self):
        """Real GET request for post list returns array."""
        result = get("https://jsonplaceholder.typicode.com/posts?_limit=5")

        assert isinstance(result, list)
        assert len(result) == 5
        assert all("id" in post for post in result)

    def test_integration_post_creates_resource(self):
        """Real POST request to JSONPlaceholder returns created resource."""
        data = {
            "title": "TDD Test Post",
            "body": "This is a test post created by TDD",
            "userId": 1,
        }

        result = post("https://jsonplaceholder.typicode.com/posts", data)

        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == 101  # JSONPlaceholder always returns 101 for new posts
        assert result["title"] == "TDD Test Post"

    def test_integration_get_nonexistent_raises(self):
        """Real GET request for non-existent resource raises APIError."""
        # JSONPlaceholder returns 404 for non-existent posts
        with pytest.raises(APIError) as exc_info:
            get("https://jsonplaceholder.typicode.com/posts/99999")

        assert exc_info.value.status_code == 404
