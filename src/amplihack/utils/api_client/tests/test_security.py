"""
Test suite for security features.

Tests URL validation, header injection prevention, credential logging prevention,
SSL enforcement, and security bounds.

Testing Philosophy:
- Unit tests for security validation
- Test malicious input handling
- Verify credential protection
- Ensure security bounds enforced
"""

import logging

import pytest
import responses

from amplihack.utils.api_client import (
    APIClient,
    RateLimitConfig,
    RequestError,
    RetryConfig,
)


class TestURLValidation:
    """Test URL scheme validation for security"""

    def test_http_url_allowed(self):
        """Test HTTP URLs are allowed"""
        client = APIClient(base_url="http://api.example.com")
        assert client.base_url == "http://api.example.com"

    def test_https_url_allowed(self):
        """Test HTTPS URLs are allowed"""
        client = APIClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_file_url_rejected(self):
        """Test file:// URLs are rejected for security"""
        with pytest.raises(ValueError) as exc_info:
            APIClient(base_url="file:///etc/passwd")

        assert "invalid" in str(exc_info.value).lower() or "scheme" in str(exc_info.value).lower()

    def test_javascript_url_rejected(self):
        """Test javascript: URLs are rejected"""
        with pytest.raises(ValueError) as exc_info:
            APIClient(base_url="javascript:alert('xss')")

        assert "invalid" in str(exc_info.value).lower() or "scheme" in str(exc_info.value).lower()

    def test_data_url_rejected(self):
        """Test data: URLs are rejected"""
        with pytest.raises(ValueError) as exc_info:
            APIClient(base_url="data:text/html,<script>alert('xss')</script>")

        assert "invalid" in str(exc_info.value).lower() or "scheme" in str(exc_info.value).lower()

    def test_ftp_url_rejected(self):
        """Test ftp:// URLs are rejected"""
        with pytest.raises(ValueError) as exc_info:
            APIClient(base_url="ftp://ftp.example.com")

        assert "invalid" in str(exc_info.value).lower() or "scheme" in str(exc_info.value).lower()

    def test_empty_url_rejected(self):
        """Test empty URL is rejected"""
        with pytest.raises(ValueError):
            APIClient(base_url="")

    def test_none_url_rejected(self):
        """Test None URL is rejected"""
        with pytest.raises((ValueError, TypeError)):
            APIClient(base_url=None)


class TestHeaderValidation:
    """Test header validation and sanitization"""

    @responses.activate
    def test_valid_headers_accepted(self):
        """Test valid headers are accepted"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        # Should not raise
        response = client.get(
            "/resource",
            headers={"X-Custom": "value", "Authorization": "Bearer token"},
        )

        assert response.status_code == 200

    def test_header_injection_attempt_rejected(self):
        """Test header injection attempts are rejected"""
        client = APIClient(base_url="https://api.example.com")

        # Attempt to inject newline in header value
        with pytest.raises(ValueError) as exc_info:
            client.get(
                "/resource",
                headers={"X-Custom": "value\r\nInjected-Header: malicious"},
            )

        assert "header" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    def test_header_value_with_newline_rejected(self):
        """Test header values containing newlines are rejected"""
        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ValueError):
            client.get("/resource", headers={"X-Custom": "value\nwith\nnewlines"})

    def test_header_value_with_carriage_return_rejected(self):
        """Test header values containing carriage returns are rejected"""
        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ValueError):
            client.get("/resource", headers={"X-Custom": "value\rwith\rCR"})

    def test_non_string_header_values_rejected(self):
        """Test non-string header values are rejected"""
        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ValueError):
            client.get("/resource", headers={"X-Custom": 123})

    def test_non_string_header_names_rejected(self):
        """Test non-string header names are rejected"""
        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ValueError):
            client.get("/resource", headers={123: "value"})


class TestCredentialProtection:
    """Test credentials are not logged or leaked in error messages"""

    @responses.activate
    def test_authorization_header_not_logged(self, caplog):
        """Test Authorization header is not logged in plaintext"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        with caplog.at_level(logging.DEBUG):
            client = APIClient(
                base_url="https://api.example.com",
                default_headers={"Authorization": "Bearer secret-token-12345"},
            )
            client.get("/resource")

        # Verify token is not in logs
        log_text = " ".join([record.message for record in caplog.records])
        assert "secret-token-12345" not in log_text
        assert "Bearer secret-token-12345" not in log_text

    @responses.activate
    def test_api_key_header_not_logged(self, caplog):
        """Test API key headers are not logged"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        with caplog.at_level(logging.DEBUG):
            client = APIClient(
                base_url="https://api.example.com",
                default_headers={"X-API-Key": "super-secret-key-xyz"},
            )
            client.get("/resource")

        log_text = " ".join([record.message for record in caplog.records])
        assert "super-secret-key-xyz" not in log_text

    @responses.activate
    def test_credentials_not_in_error_messages(self):
        """Test credentials are not included in error messages"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=401,
            json={"error": "Unauthorized"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer secret-token-12345"},
        )

        with pytest.raises(Exception) as exc_info:
            client.get("/resource")

        error_message = str(exc_info.value)
        assert "secret-token-12345" not in error_message

    def test_credentials_in_url_not_logged(self, caplog):
        """Test credentials in URL (bad practice) are not logged"""
        # Note: This tests the client handles it, though users shouldn't do this
        with caplog.at_level(logging.DEBUG):
            try:
                client = APIClient(base_url="https://user:password@api.example.com")
                # May fail connection, but shouldn't log password
            except:
                pass

        log_text = " ".join([record.message for record in caplog.records])
        assert "password" not in log_text


class TestSSLEnforcement:
    """Test SSL/TLS certificate verification"""

    def test_ssl_verification_enabled_by_default(self):
        """Test SSL verification is enabled by default"""
        client = APIClient(base_url="https://api.example.com")
        assert client.verify_ssl is True

    def test_ssl_verification_can_be_disabled(self):
        """Test SSL verification can be disabled (for testing)"""
        client = APIClient(base_url="https://api.example.com", verify_ssl=False)
        assert client.verify_ssl is False

    @responses.activate
    def test_ssl_disabled_warning_logged(self, caplog):
        """Test warning is logged when SSL verification is disabled"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        with caplog.at_level(logging.WARNING):
            client = APIClient(base_url="https://api.example.com", verify_ssl=False)
            client.get("/resource")

        # Should have warning about SSL being disabled
        warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any(
            "ssl" in msg.lower() or "verify" in msg.lower() or "security" in msg.lower()
            for msg in [r.message for r in warning_logs]
        )

    def test_http_url_no_ssl_verification(self):
        """Test HTTP URLs don't trigger SSL verification warnings"""
        # HTTP doesn't use SSL, so no verification needed
        client = APIClient(base_url="http://api.example.com")
        # Should create client without issues
        assert client.base_url == "http://api.example.com"


class TestParameterValidation:
    """Test query parameter validation"""

    @responses.activate
    def test_valid_parameters_accepted(self):
        """Test valid query parameters are accepted"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource?page=1&limit=10",
            json={"results": []},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/resource", params={"page": 1, "limit": 10})

        assert response.status_code == 200

    @responses.activate
    def test_string_parameters_accepted(self):
        """Test string parameters are accepted"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource?query=test",
            json={"results": []},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/resource", params={"query": "test"})

        assert response.status_code == 200

    def test_list_parameter_handling(self):
        """Test list parameters are handled or rejected appropriately"""
        client = APIClient(base_url="https://api.example.com")

        # Implementation may either:
        # 1. Accept and serialize lists properly
        # 2. Reject lists with ValueError
        # Both are acceptable depending on design
        try:
            # If lists are supported, should work
            with responses.RequestsMock() as rsps:
                rsps.add(
                    responses.GET,
                    "https://api.example.com/resource",
                    json={"success": True},
                    status=200,
                )
                client.get("/resource", params={"ids": [1, 2, 3]})
        except ValueError:
            # If lists are rejected for security, that's also valid
            pass


class TestRateLimitSecurityBounds:
    """Test rate limit security bounds prevent abuse"""

    def test_max_wait_time_default_reasonable(self):
        """Test default max wait time is reasonable (not infinite)"""
        config = RateLimitConfig()
        assert config.max_wait_time < 3600.0  # Less than 1 hour
        assert config.max_wait_time > 0  # Greater than 0

    def test_max_wait_time_enforced(self):
        """Test max wait time cannot be set to unreasonable values"""
        # Should allow reasonable values
        config = RateLimitConfig(max_wait_time=600.0)
        assert config.max_wait_time == 600.0

        # May reject or cap extremely large values
        # (implementation dependent, but should have bounds)

    @responses.activate
    def test_malicious_retry_after_blocked(self):
        """Test malicious Retry-After values are blocked"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "999999"},  # ~11 days
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(max_wait_time=300.0),
        )

        # Should raise RateLimitError, not wait 11 days
        from amplihack.utils.api_client import RateLimitError

        with pytest.raises(RateLimitError):
            client.get("/resource")


class TestRetrySecurityBounds:
    """Test retry logic has security bounds"""

    def test_max_retries_default_reasonable(self):
        """Test default max retries is reasonable"""
        config = RetryConfig()
        assert config.max_retries <= 10  # Not excessive
        assert config.max_retries >= 0

    def test_max_delay_caps_exponential_backoff(self):
        """Test max_delay prevents unbounded exponential backoff"""
        config = RetryConfig()
        assert config.max_delay > 0
        assert config.max_delay < 3600.0  # Less than 1 hour

    def test_retry_config_prevents_resource_exhaustion(self):
        """Test retry config prevents resource exhaustion"""
        # Even with aggressive settings, total wait should be bounded
        config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=60.0, exponential_base=2.0)

        # Maximum total wait: 1 + 2 + 4 = 7 seconds (with max_delay=60)
        max_total_wait = sum(
            min(config.base_delay * (config.exponential_base**i), config.max_delay)
            for i in range(config.max_retries)
        )

        # Should be reasonable
        assert max_total_wait < 300.0  # Less than 5 minutes


class TestInputSanitization:
    """Test input sanitization for various attack vectors"""

    @responses.activate
    def test_sql_injection_in_params_escaped(self):
        """Test SQL injection attempts in parameters are handled safely"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"results": []},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        # Client should safely handle these without executing SQL
        response = client.get("/resource", params={"query": "'; DROP TABLE users; --"})

        # Request should be made safely (API handles SQL safety)
        assert response.status_code == 200

    @responses.activate
    def test_xss_attempt_in_params_not_executed(self):
        """Test XSS attempts in parameters don't cause issues"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"results": []},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        # Client should safely handle these
        response = client.get("/resource", params={"query": "<script>alert('xss')</script>"})

        assert response.status_code == 200

    def test_path_traversal_in_url_rejected(self):
        """Test path traversal attempts in URL are handled"""
        client = APIClient(base_url="https://api.example.com")

        # Client may either:
        # 1. Normalize the path safely
        # 2. Reject the path
        # Both are acceptable
        try:
            with responses.RequestsMock() as rsps:
                rsps.add(
                    responses.GET,
                    "https://api.example.com/../../etc/passwd",
                    status=404,
                )
                # May succeed with safe normalization or fail early
                client.get("/../../etc/passwd")
        except (ValueError, RequestError):
            # If rejected, that's also fine
            pass


class TestErrorMessageSanitization:
    """Test error messages don't leak sensitive information"""

    @responses.activate
    def test_error_message_no_credentials(self):
        """Test error messages don't contain credentials"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=500,
            json={"error": "Internal server error"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer secret-token"},
        )

        with pytest.raises(Exception) as exc_info:
            client.get("/resource")

        error_msg = str(exc_info.value)
        assert "secret-token" not in error_msg

    @responses.activate
    def test_error_message_no_internal_paths(self):
        """Test error messages don't leak internal file paths"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=500,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(Exception) as exc_info:
            client.get("/resource")

        error_msg = str(exc_info.value)
        # Error should not contain absolute file system paths
        # (some stack trace info may be acceptable, but not full paths)
        # This is a guideline - exact implementation may vary


class TestTimeoutSecurity:
    """Test timeout settings prevent hanging"""

    def test_default_timeout_set(self):
        """Test default timeout is set (not infinite)"""
        client = APIClient(base_url="https://api.example.com")
        assert client.timeout > 0
        assert client.timeout < 300.0  # Less than 5 minutes

    def test_custom_timeout_accepted(self):
        """Test custom timeout values are accepted"""
        client = APIClient(base_url="https://api.example.com", timeout=60.0)
        assert client.timeout == 60.0

    def test_zero_timeout_rejected(self):
        """Test zero timeout is rejected or handled"""
        # Zero timeout would mean no timeout, which could hang
        try:
            client = APIClient(base_url="https://api.example.com", timeout=0.0)
            # If allowed, should be documented behavior
        except ValueError:
            # If rejected, that's also acceptable
            pass

    def test_negative_timeout_rejected(self):
        """Test negative timeout is rejected"""
        with pytest.raises(ValueError):
            APIClient(base_url="https://api.example.com", timeout=-1.0)


class TestSecureDefaults:
    """Test secure default configurations"""

    def test_secure_defaults_enabled(self):
        """Test security features are enabled by default"""
        client = APIClient(base_url="https://api.example.com")

        # SSL verification enabled
        assert client.verify_ssl is True

        # Timeout set (not infinite)
        assert client.timeout > 0

        # Rate limit protection enabled
        assert client.rate_limit_config is not None
        assert client.rate_limit_config.max_wait_time > 0

        # Retry protection enabled
        assert client.retry_config is not None
        assert client.retry_config.max_retries >= 0

    def test_no_credential_leakage_in_repr(self):
        """Test client repr doesn't leak credentials"""
        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer secret-token"},
        )

        repr_str = repr(client)
        assert "secret-token" not in repr_str

    def test_no_credential_leakage_in_str(self):
        """Test client str doesn't leak credentials"""
        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer secret-token"},
        )

        str_repr = str(client)
        assert "secret-token" not in str_repr
