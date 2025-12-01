"""Tests for Request and Response dataclasses.

Testing pyramid distribution:
- 100% Unit tests (dataclasses are pure, no dependencies)
"""

import pytest


class TestRequestDataclass:
    """Test Request dataclass creation and immutability."""

    def test_create_minimal_request(self, valid_url):
        """Test creating request with only required fields."""
        # Import will fail until implementation exists
        from api_client.models import Request

        # Arrange & Act
        request = Request(url=valid_url, method="GET")

        # Assert
        assert request.url == valid_url
        assert request.method == "GET"
        assert request.headers is None
        assert request.body is None
        assert request.params is None

    def test_create_request_with_all_fields(
        self, valid_url, valid_headers, valid_json_body, valid_query_params
    ):
        """Test creating request with all optional fields."""
        from api_client.models import Request

        # Arrange & Act
        request = Request(
            url=valid_url,
            method="POST",
            headers=valid_headers,
            body=valid_json_body,
            params=valid_query_params,
        )

        # Assert
        assert request.url == valid_url
        assert request.method == "POST"
        assert request.headers == valid_headers
        assert request.body == valid_json_body
        assert request.params == valid_query_params

    def test_request_is_frozen(self, valid_url):
        """Test that Request is immutable (frozen dataclass)."""
        from api_client.models import Request

        # Arrange
        request = Request(url=valid_url, method="GET")

        # Act & Assert
        with pytest.raises(AttributeError):
            request.url = "https://different.com"  # type: ignore[misc]

    def test_request_with_get_method(self, valid_url):
        """Test GET request creation."""
        from api_client.models import Request

        # Arrange & Act
        request = Request(url=valid_url, method="GET")

        # Assert
        assert request.method == "GET"

    def test_request_with_post_method(self, valid_url, valid_json_body):
        """Test POST request creation with body."""
        from api_client.models import Request

        # Arrange & Act
        request = Request(url=valid_url, method="POST", body=valid_json_body)

        # Assert
        assert request.method == "POST"
        assert request.body == valid_json_body

    def test_request_with_put_method(self, valid_url, valid_json_body):
        """Test PUT request creation with body."""
        from api_client.models import Request

        # Arrange & Act
        request = Request(url=valid_url, method="PUT", body=valid_json_body)

        # Assert
        assert request.method == "PUT"
        assert request.body == valid_json_body

    def test_request_with_delete_method(self, valid_url):
        """Test DELETE request creation."""
        from api_client.models import Request

        # Arrange & Act
        request = Request(url=valid_url, method="DELETE")

        # Assert
        assert request.method == "DELETE"

    def test_request_with_string_body(self, valid_url):
        """Test request with string body (not JSON)."""
        from api_client.models import Request

        # Arrange
        text_body = "Plain text content"

        # Act
        request = Request(url=valid_url, method="POST", body=text_body)

        # Assert
        assert request.body == text_body
        assert isinstance(request.body, str)

    def test_request_with_bytes_body(self, valid_url):
        """Test request with bytes body (binary data)."""
        from api_client.models import Request

        # Arrange
        binary_body = b"\x00\x01\x02\x03"

        # Act
        request = Request(url=valid_url, method="POST", body=binary_body)

        # Assert
        assert request.body == binary_body
        assert isinstance(request.body, bytes)

    def test_request_with_empty_headers(self, valid_url):
        """Test request with empty headers dict."""
        from api_client.models import Request

        # Arrange & Act
        request = Request(url=valid_url, method="GET", headers={})

        # Assert
        assert request.headers == {}

    def test_request_with_empty_params(self, valid_url):
        """Test request with empty params dict."""
        from api_client.models import Request

        # Arrange & Act
        request = Request(url=valid_url, method="GET", params={})

        # Assert
        assert request.params == {}

    def test_request_equality(self, valid_url):
        """Test that two requests with same data are equal."""
        from api_client.models import Request

        # Arrange
        request1 = Request(url=valid_url, method="GET")
        request2 = Request(url=valid_url, method="GET")

        # Act & Assert
        assert request1 == request2

    def test_request_inequality(self, valid_url):
        """Test that requests with different data are not equal."""
        from api_client.models import Request

        # Arrange
        request1 = Request(url=valid_url, method="GET")
        request2 = Request(url=valid_url, method="POST")

        # Act & Assert
        assert request1 != request2

    def test_request_repr(self, valid_url):
        """Test request string representation."""
        from api_client.models import Request

        # Arrange
        request = Request(url=valid_url, method="GET")

        # Act
        repr_str = repr(request)

        # Assert
        assert "Request" in repr_str
        assert valid_url in repr_str
        assert "GET" in repr_str


class TestResponseDataclass:
    """Test Response dataclass creation and immutability."""

    def test_create_minimal_response(self, valid_url):
        """Test creating response with required fields."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")

        # Act
        response = Response(status_code=200, headers={}, body="", request=request)

        # Assert
        assert response.status_code == 200
        assert response.headers == {}
        assert response.body == ""
        assert response.request == request

    def test_create_response_with_json_body(self, valid_url, mock_response_json):
        """Test creating response with JSON body."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        headers = {"Content-Type": "application/json"}

        # Act
        response = Response(
            status_code=200, headers=headers, body=mock_response_json, request=request
        )

        # Assert
        assert response.status_code == 200
        assert response.body == mock_response_json
        assert isinstance(response.body, dict)

    def test_response_is_frozen(self, valid_url):
        """Test that Response is immutable (frozen dataclass)."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        response = Response(status_code=200, headers={}, body="", request=request)

        # Act & Assert
        with pytest.raises(AttributeError):
            response.status_code = 404  # type: ignore[misc]

    def test_response_preserves_original_request(self, valid_url, valid_headers):
        """Test that response contains reference to original request."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="POST", headers=valid_headers)

        # Act
        response = Response(status_code=201, headers={}, body={"id": 123}, request=request)

        # Assert
        assert response.request == request
        assert response.request.url == valid_url
        assert response.request.method == "POST"
        assert response.request.headers == valid_headers

    def test_response_with_2xx_status(self, valid_url):
        """Test response with successful 2xx status codes."""
        from api_client.models import Request, Response

        request = Request(url=valid_url, method="GET")

        for status_code in [200, 201, 202, 204]:
            # Act
            response = Response(status_code=status_code, headers={}, body="", request=request)

            # Assert
            assert response.status_code == status_code

    def test_response_with_4xx_status(self, valid_url):
        """Test response with client error 4xx status codes."""
        from api_client.models import Request, Response

        request = Request(url=valid_url, method="GET")

        for status_code in [400, 401, 403, 404, 429]:
            # Act
            response = Response(status_code=status_code, headers={}, body="", request=request)

            # Assert
            assert response.status_code == status_code

    def test_response_with_5xx_status(self, valid_url):
        """Test response with server error 5xx status codes."""
        from api_client.models import Request, Response

        request = Request(url=valid_url, method="GET")

        for status_code in [500, 502, 503, 504]:
            # Act
            response = Response(status_code=status_code, headers={}, body="", request=request)

            # Assert
            assert response.status_code == status_code

    def test_response_with_string_body(self, valid_url):
        """Test response with string body."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        text_body = "Plain text response"

        # Act
        response = Response(
            status_code=200, headers={"Content-Type": "text/plain"}, body=text_body, request=request
        )

        # Assert
        assert response.body == text_body
        assert isinstance(response.body, str)

    def test_response_with_bytes_body(self, valid_url):
        """Test response with bytes body (binary data)."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        binary_body = b"\x89PNG\r\n\x1a\n"  # PNG header

        # Act
        response = Response(
            status_code=200,
            headers={"Content-Type": "image/png"},
            body=binary_body,
            request=request,
        )

        # Assert
        assert response.body == binary_body
        assert isinstance(response.body, bytes)

    def test_response_with_empty_headers(self, valid_url):
        """Test response with no headers."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")

        # Act
        response = Response(status_code=200, headers={}, body="", request=request)

        # Assert
        assert response.headers == {}

    def test_response_with_multiple_headers(self, valid_url):
        """Test response with multiple headers."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Request-ID": "abc123",
        }

        # Act
        response = Response(status_code=200, headers=headers, body={}, request=request)

        # Assert
        assert response.headers == headers
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["X-Request-ID"] == "abc123"

    def test_response_equality(self, valid_url):
        """Test that two responses with same data are equal."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        response1 = Response(status_code=200, headers={}, body="", request=request)
        response2 = Response(status_code=200, headers={}, body="", request=request)

        # Act & Assert
        assert response1 == response2

    def test_response_inequality(self, valid_url):
        """Test that responses with different data are not equal."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        response1 = Response(status_code=200, headers={}, body="", request=request)
        response2 = Response(status_code=404, headers={}, body="", request=request)

        # Act & Assert
        assert response1 != response2

    def test_response_repr(self, valid_url):
        """Test response string representation."""
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        response = Response(status_code=200, headers={}, body="", request=request)

        # Act
        repr_str = repr(response)

        # Assert
        assert "Response" in repr_str
        assert "200" in repr_str
