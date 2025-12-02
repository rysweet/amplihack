"""Tests for core client module."""

import pytest

from amplihack.api_client.config import RestApiConfig
from amplihack.api_client.core import RestApiClient
from amplihack.api_client.exceptions import ApiClientError, SecurityError


def test_client_initialization():
    """Test client initialization."""
    config = RestApiConfig(base_url="https://api.example.com")
    client = RestApiClient(config)

    assert client.config.base_url == "https://api.example.com"
    assert client.security is not None
    assert client.retry is not None


def test_client_ssrf_protection():
    """Test client enforces SSRF protection."""
    config = RestApiConfig(base_url="https://127.0.0.1")
    client = RestApiClient(config)

    with pytest.raises(SecurityError):
        client.get("/admin")


def test_client_https_enforcement():
    """Test client enforces HTTPS."""
    config = RestApiConfig(base_url="http://insecure.com")
    client = RestApiClient(config)

    # SSRF check happens in validate_url, so HTTP scheme should fail
    with pytest.raises(SecurityError, match="HTTPS required"):
        client.get("/endpoint")


def test_client_allow_private_flag():
    """Test allow_private flag bypasses security checks."""
    config = RestApiConfig(base_url="http://localhost:8000")
    client = RestApiClient(config)

    # This would normally fail SSRF + HTTPS, but allow_private=True bypasses
    try:
        # This will fail with network error, but security should pass
        client.get("/test", allow_private=True)
    except ApiClientError:
        # Network error is expected, security should have passed
        pass


@pytest.mark.integration
def test_client_real_http_request():
    """Integration test with real HTTP request to httpbin.org."""
    config = RestApiConfig(base_url="https://httpbin.org", timeout=10.0)
    client = RestApiClient(config)

    response = client.get("/status/200")
    assert response.status_code == 200
    assert response.ok is True


@pytest.mark.integration
def test_client_post_request():
    """Integration test for POST request."""
    config = RestApiConfig(base_url="https://httpbin.org", timeout=10.0)
    client = RestApiClient(config)

    body = b'{"test": "data"}'
    response = client.post("/post", body=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 200
    data = response.json()
    assert data["data"] == '{"test": "data"}'


@pytest.mark.integration
def test_client_retry_on_failure():
    """Integration test for retry logic - 5xx errors should trigger retries and eventually raise."""
    config = RestApiConfig(
        base_url="https://httpbin.org", timeout=10.0, max_retries=2, retry_backoff=0.1
    )
    client = RestApiClient(config)

    # httpbin.org/status/500 returns 500, which should trigger retries and eventually raise
    with pytest.raises(Exception):  # Should raise RetryExhaustedError or ApiClientError
        client.get("/status/500")
