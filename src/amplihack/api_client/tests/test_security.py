"""Tests for security module."""

import pytest

from amplihack.api_client.exceptions import SecurityError
from amplihack.api_client.security import SecurityValidator


def test_ssrf_protection_loopback():
    """Test SSRF protection blocks loopback addresses."""
    with pytest.raises(SecurityError, match="Private IP blocked"):
        SecurityValidator.validate_url("https://127.0.0.1/admin")


def test_ssrf_protection_private_class_a():
    """Test SSRF protection blocks private Class A."""
    with pytest.raises(SecurityError, match="Private IP blocked"):
        SecurityValidator.validate_url("https://10.0.0.1/internal")


def test_ssrf_protection_private_class_b():
    """Test SSRF protection blocks private Class B."""
    with pytest.raises(SecurityError, match="Private IP blocked"):
        SecurityValidator.validate_url("https://172.16.0.1/internal")


def test_ssrf_protection_private_class_c():
    """Test SSRF protection blocks private Class C."""
    with pytest.raises(SecurityError, match="Private IP blocked"):
        SecurityValidator.validate_url("https://192.168.1.1/internal")


def test_ssrf_protection_link_local():
    """Test SSRF protection blocks link-local."""
    with pytest.raises(SecurityError, match="Private IP blocked"):
        SecurityValidator.validate_url("https://169.254.169.254/metadata")


def test_ssrf_protection_allows_public():
    """Test SSRF protection allows public IPs."""
    # Should not raise
    SecurityValidator.validate_url("https://8.8.8.8/public")


def test_ssrf_protection_allows_hostnames():
    """Test SSRF protection allows DNS hostnames."""
    # Should not raise
    SecurityValidator.validate_url("https://api.example.com/endpoint")


def test_ssrf_protection_allow_private_flag():
    """Test allow_private flag bypasses SSRF protection."""
    # Should not raise with allow_private=True
    SecurityValidator.validate_url("https://127.0.0.1/admin", allow_private=True)


def test_https_enforcement():
    """Test HTTPS enforcement in production."""
    with pytest.raises(SecurityError, match="HTTPS required"):
        SecurityValidator.validate_url("http://api.example.com/endpoint")


def test_https_enforcement_allow_private():
    """Test allow_private flag bypasses HTTPS enforcement."""
    # Should not raise with allow_private=True
    SecurityValidator.validate_url("http://api.example.com/endpoint", allow_private=True)


def test_sanitize_headers_authorization():
    """Test header sanitization redacts Authorization."""
    headers = {"Authorization": "Bearer secret123", "Content-Type": "application/json"}
    sanitized = SecurityValidator.sanitize_headers(headers)

    assert sanitized["Authorization"] == "***REDACTED***"
    assert sanitized["Content-Type"] == "application/json"


def test_sanitize_headers_api_key():
    """Test header sanitization redacts API keys."""
    headers = {"API-Key": "secret", "api_key": "secret2"}  # pragma: allowlist secret
    sanitized = SecurityValidator.sanitize_headers(headers)

    assert sanitized["API-Key"] == "***REDACTED***"
    assert sanitized["api_key"] == "***REDACTED***"


def test_sanitize_headers_case_insensitive():
    """Test header sanitization is case insensitive."""
    headers = {"AUTHORIZATION": "Bearer token", "Authorization": "Bearer token2"}
    sanitized = SecurityValidator.sanitize_headers(headers)

    assert all(v == "***REDACTED***" for v in sanitized.values())
