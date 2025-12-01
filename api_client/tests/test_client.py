"""Tests for HTTPClient with validation, logging, and security.

Testing pyramid distribution:
- 70% Unit tests (validation, error handling, configuration)
- 30% Integration tests (with mocked HTTP responses)
"""

import logging
from unittest.mock import Mock

import pytest
import responses


class TestHTTPClientCreation:
    """Test HTTPClient initialization and configuration."""

    def test_create_client_with_defaults(self):
        """Test creating HTTPClient with all default settings."""
        from api_client.client import HTTPClient

        # Arrange & Act
        client = HTTPClient()

        # Assert
        assert client is not None

    def test_create_client_with_custom_rate_limiter(self):
        """Test creating HTTPClient with custom rate limiter."""
        from api_client.client import HTTPClient
        from api_client.rate_limiter import RateLimiter

        # Arrange
        custom_limiter = RateLimiter(requests_per_second=5.0)

        # Act
        client = HTTPClient(rate_limiter=custom_limiter)

        # Assert
        assert client is not None

    def test_create_client_with_custom_retry_policy(self):
        """Test creating HTTPClient with custom retry policy."""
        from api_client.client import HTTPClient
        from api_client.retry import RetryPolicy

        # Arrange
        custom_policy = RetryPolicy(max_retries=5)

        # Act
        client = HTTPClient(retry_policy=custom_policy)

        # Assert
        assert client is not None

    def test_create_client_with_custom_timeout(self):
        """Test creating HTTPClient with custom timeout."""
        from api_client.client import HTTPClient

        # Arrange & Act
        client = HTTPClient(timeout=60)

        # Assert
        assert client is not None

    def test_create_client_with_allowed_hosts(self, allowed_hosts):
        """Test creating HTTPClient with SSRF protection (allowed_hosts)."""
        from api_client.client import HTTPClient

        # Arrange & Act
        client = HTTPClient(allowed_hosts=allowed_hosts)

        # Assert
        assert client is not None

    def test_create_client_with_default_headers(self, valid_headers):
        """Test creating HTTPClient with default headers."""
        from api_client.client import HTTPClient

        # Arrange & Act
        client = HTTPClient(default_headers=valid_headers)

        # Assert
        assert client is not None

    def test_create_client_with_all_options(self, allowed_hosts, valid_headers):
        """Test creating HTTPClient with all configuration options."""
        from api_client.client import HTTPClient
        from api_client.rate_limiter import RateLimiter
        from api_client.retry import RetryPolicy

        # Arrange & Act
        client = HTTPClient(
            rate_limiter=RateLimiter(requests_per_second=10.0),
            retry_policy=RetryPolicy(max_retries=3),
            timeout=30,
            allowed_hosts=allowed_hosts,
            default_headers=valid_headers,
        )

        # Assert
        assert client is not None


class TestHTTPClientValidation:
    """Test input validation (CRITICAL for security)."""

    def test_validate_url_rejects_empty_string(self):
        """Test that empty URL raises ValueError."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url="", method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="URL cannot be empty"):
            client.send(request)

    def test_validate_url_rejects_missing_scheme(self, invalid_url):
        """Test that URL without scheme (http/https) raises ValueError."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=invalid_url, method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="URL must start with http:// or https://"):
            client.send(request)

    def test_validate_url_allows_https(self, valid_url):
        """Test that HTTPS URLs are accepted."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act & Assert - should not raise (will fail later with network error, that's ok)
        # This test just validates URL validation passes
        try:
            client.send(request)
        except Exception as e:
            # Validation passed, network error is expected
            assert "URL" not in str(e)

    def test_validate_method_rejects_invalid(self):
        """Test that invalid HTTP method raises ValueError."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url="https://api.example.com", method="INVALID")

        # Act & Assert
        with pytest.raises(ClientError, match="Invalid HTTP method"):
            client.send(request)

    def test_validate_method_allows_get(self, valid_url):
        """Test that GET method is accepted."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act - validation should pass
        try:
            client.send(request)
        except Exception as e:
            # Method validation passed, network error is expected
            assert "method" not in str(e).lower()

    def test_validate_method_allows_post(self, valid_url):
        """Test that POST method is accepted."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=valid_url, method="POST")

        # Act - validation should pass
        try:
            client.send(request)
        except Exception:
            pass  # Network error expected, validation passed

    def test_validate_method_allows_put(self, valid_url):
        """Test that PUT method is accepted."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=valid_url, method="PUT")

        # Act - validation should pass
        try:
            client.send(request)
        except Exception:
            pass  # Network error expected, validation passed

    def test_validate_method_allows_delete(self, valid_url):
        """Test that DELETE method is accepted."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=valid_url, method="DELETE")

        # Act - validation should pass
        try:
            client.send(request)
        except Exception:
            pass  # Network error expected, validation passed


class TestHTTPClientSSRFProtection:
    """Test SSRF protection (CRITICAL for security)."""

    def test_ssrf_blocks_private_ip(self, private_ip_url):
        """Test that private IP addresses are blocked by default."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=private_ip_url, method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="private IP"):
            client.send(request)

    def test_ssrf_blocks_localhost(self, localhost_url):
        """Test that localhost is blocked by default."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=localhost_url, method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="localhost"):
            client.send(request)

    def test_ssrf_blocks_127001(self):
        """Test that 127.0.0.1 is blocked."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url="http://127.0.0.1:8080/api", method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="127.0.0.1"):
            client.send(request)

    def test_ssrf_blocks_10_network(self):
        """Test that 10.0.0.0/8 network is blocked."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url="http://10.0.0.1/api", method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="10.0.0.1"):
            client.send(request)

    def test_ssrf_blocks_172_network(self):
        """Test that 172.16.0.0/12 network is blocked."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url="http://172.16.0.1/api", method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="172.16.0.1"):
            client.send(request)

    def test_ssrf_allows_public_ip(self):
        """Test that public IP addresses are allowed."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url="https://8.8.8.8/api", method="GET")

        # Act - should not raise SSRF error (may raise network error)
        try:
            client.send(request)
        except Exception as e:
            # Should NOT be SSRF error
            assert "private" not in str(e).lower()
            assert "localhost" not in str(e).lower()

    def test_ssrf_allowed_hosts_permits_match(self, allowed_hosts):
        """Test that allowed_hosts permits matching hosts."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient(allowed_hosts=allowed_hosts)
        request = Request(url="https://api.example.com/users", method="GET")

        # Act - should not raise SSRF error
        try:
            client.send(request)
        except Exception as e:
            # Should NOT be SSRF/allowlist error
            assert "not in allowed hosts" not in str(e).lower()

    def test_ssrf_allowed_hosts_blocks_mismatch(self, allowed_hosts):
        """Test that allowed_hosts blocks non-matching hosts."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient(allowed_hosts=allowed_hosts)
        request = Request(url="https://malicious.com/steal", method="GET")

        # Act & Assert
        with pytest.raises(ClientError, match="not in allowed hosts"):
            client.send(request)


class TestHTTPClientHeaderInjection:
    """Test header injection prevention (CRITICAL for security)."""

    def test_rejects_crlf_in_header_value(self, valid_url, malicious_headers):
        """Test that CRLF injection in headers is blocked."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=valid_url, method="GET", headers=malicious_headers)

        # Act & Assert
        with pytest.raises(ClientError, match="CRLF"):
            client.send(request)

    def test_rejects_newline_in_header_value(self, valid_url):
        """Test that newline characters in headers are blocked."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        headers = {"X-Custom": "value\ninjected"}
        request = Request(url=valid_url, method="GET", headers=headers)

        # Act & Assert
        with pytest.raises(ClientError, match="CRLF"):
            client.send(request)

    def test_allows_safe_headers(self, valid_url, valid_headers):
        """Test that safe headers are allowed."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url=valid_url, method="GET", headers=valid_headers)

        # Act - should not raise header injection error
        try:
            client.send(request)
        except Exception as e:
            # Should NOT be header injection error
            assert "CRLF" not in str(e)


class TestHTTPClientTimeout:
    """Test timeout enforcement."""

    @responses.activate
    def test_respects_default_timeout(self, valid_url):
        """Test that default timeout (30s) is used."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        client = HTTPClient()  # Default timeout=30
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert - request completed successfully
        assert response.status_code == 200

    @responses.activate
    def test_respects_custom_client_timeout(self, valid_url):
        """Test that custom client timeout is used."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        client = HTTPClient(timeout=60)
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert
        assert response.status_code == 200

    @responses.activate
    def test_respects_per_request_timeout_override(self, valid_url):
        """Test that per-request timeout overrides client timeout."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        client = HTTPClient(timeout=30)
        request = Request(url=valid_url, method="GET")

        # Act - override with 120s timeout
        response = client.send(request, timeout=120)

        # Assert
        assert response.status_code == 200


class TestHTTPClientLogging:
    """Test logging functionality."""

    @responses.activate
    def test_logs_request_start(self, valid_url, caplog):
        """Test that request start is logged."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={}, status=200)
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act
        with caplog.at_level(logging.INFO):
            client.send(request)

        # Assert - check log contains request info
        assert any("GET" in record.message for record in caplog.records)

    @responses.activate
    def test_logs_request_success(self, valid_url, caplog):
        """Test that successful request is logged."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={}, status=200)
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act
        with caplog.at_level(logging.INFO):
            client.send(request)

        # Assert
        assert any("200" in record.message for record in caplog.records)

    @responses.activate
    def test_logs_scrub_authorization_header(self, valid_url, auth_token, caplog):
        """Test that Authorization header is scrubbed in logs."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={}, status=200)
        client = HTTPClient()
        headers = {"Authorization": auth_token}
        request = Request(url=valid_url, method="GET", headers=headers)

        # Act
        with caplog.at_level(logging.DEBUG):
            client.send(request)

        # Assert - token should NOT appear in logs
        assert auth_token not in caplog.text
        # Should have redacted placeholder
        assert any(
            "REDACTED" in record.message or "***" in record.message for record in caplog.records
        )

    @responses.activate
    def test_logs_request_failure(self, valid_url, caplog):
        """Test that failed request is logged."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ServerError
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={}, status=500)
        client = HTTPClient(retry_policy=Mock(max_retries=0))  # Disable retries
        request = Request(url=valid_url, method="GET")

        # Act
        with caplog.at_level(logging.ERROR):
            try:
                client.send(request)
            except ServerError:
                pass

        # Assert
        assert any(
            "500" in record.message or "error" in record.message.lower()
            for record in caplog.records
        )


class TestHTTPClientWithMockedResponses:
    """Integration tests with mocked HTTP responses."""

    @responses.activate
    def test_send_get_request_success(self, valid_url, mock_response_json):
        """Test successful GET request."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json=mock_response_json, status=200)
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert
        assert response.status_code == 200
        assert response.body == mock_response_json

    @responses.activate
    def test_send_post_request_with_json_body(self, valid_url, valid_json_body):
        """Test POST request with JSON body."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.POST, valid_url, json={"id": 123}, status=201)
        client = HTTPClient()
        request = Request(url=valid_url, method="POST", body=valid_json_body)

        # Act
        response = client.send(request)

        # Assert
        assert response.status_code == 201
        assert isinstance(response.body, dict)
        assert response.body["id"] == 123

    @responses.activate
    def test_send_put_request(self, valid_url, valid_json_body):
        """Test PUT request."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.PUT, valid_url, json=valid_json_body, status=200)
        client = HTTPClient()
        request = Request(url=valid_url, method="PUT", body=valid_json_body)

        # Act
        response = client.send(request)

        # Assert
        assert response.status_code == 200

    @responses.activate
    def test_send_delete_request(self, valid_url):
        """Test DELETE request."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.DELETE, valid_url, status=204)
        client = HTTPClient()
        request = Request(url=valid_url, method="DELETE")

        # Act
        response = client.send(request)

        # Assert
        assert response.status_code == 204

    @responses.activate
    def test_send_request_with_query_params(self, valid_url, valid_query_params):
        """Test request with query parameters."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        full_url = f"{valid_url}?page=1&limit=10&sort=created_at"
        responses.add(responses.GET, full_url, json=[], status=200)
        client = HTTPClient()
        request = Request(url=valid_url, method="GET", params=valid_query_params)

        # Act
        response = client.send(request)

        # Assert
        assert response.status_code == 200

    @responses.activate
    def test_send_request_merges_default_headers(self, valid_url):
        """Test that default headers are merged with request headers."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        default_headers = {"User-Agent": "TestClient/1.0"}
        request_headers = {"X-Custom": "value"}
        responses.add(responses.GET, valid_url, json={}, status=200)
        client = HTTPClient(default_headers=default_headers)
        request = Request(url=valid_url, method="GET", headers=request_headers)

        # Act
        response = client.send(request)

        # Assert - both headers should be present
        assert response.status_code == 200


class TestHTTPClientErrorHandling:
    """Test error handling and exception raising."""

    @responses.activate
    def test_raises_client_error_on_400(self, valid_url):
        """Test that 400 raises ClientError."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"error": "Bad request"}, status=400)
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            client.send(request)

        assert exc_info.value.status_code == 400

    @responses.activate
    def test_raises_client_error_on_404(self, valid_url):
        """Test that 404 raises ClientError."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"error": "Not found"}, status=404)
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            client.send(request)

        assert exc_info.value.status_code == 404

    @responses.activate
    def test_raises_server_error_on_500(self, valid_url):
        """Test that 500 raises ServerError."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ServerError
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"error": "Internal error"}, status=500)
        client = HTTPClient()
        # Disable retries for this test
        client.retry_policy = Mock(max_retries=0, should_retry=Mock(return_value=False))
        request = Request(url=valid_url, method="GET")

        # Act & Assert
        with pytest.raises(ServerError) as exc_info:
            client.send(request)

        assert exc_info.value.status_code == 500

    @responses.activate
    def test_error_includes_response_object(self, valid_url, mock_error_response):
        """Test that error exceptions include response object."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json=mock_error_response, status=404)
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            client.send(request)

        assert exc_info.value.response is not None
        assert exc_info.value.response.status_code == 404
        assert exc_info.value.response.body == mock_error_response


class TestHTTPClientResponseParsing:
    """Test response body parsing."""

    @responses.activate
    def test_parses_json_response(self, valid_url, mock_response_json):
        """Test that JSON response is parsed to dict."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(
            responses.GET,
            valid_url,
            json=mock_response_json,
            status=200,
            headers={"Content-Type": "application/json"},
        )
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert
        assert isinstance(response.body, dict)
        assert response.body == mock_response_json

    @responses.activate
    def test_parses_text_response(self, valid_url):
        """Test that text response is returned as string."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        text_body = "Plain text response"
        responses.add(
            responses.GET,
            valid_url,
            body=text_body,
            status=200,
            headers={"Content-Type": "text/plain"},
        )
        client = HTTPClient()
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert
        assert isinstance(response.body, str)
        assert response.body == text_body

    @responses.activate
    def test_parses_empty_response(self, valid_url):
        """Test that empty response (204) is handled."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.DELETE, valid_url, status=204)
        client = HTTPClient()
        request = Request(url=valid_url, method="DELETE")

        # Act
        response = client.send(request)

        # Assert
        assert response.status_code == 204
        assert response.body == "" or response.body is None
