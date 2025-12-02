"""Tests for configuration module."""

import pytest

from amplihack.api_client.config import RestApiConfig
from amplihack.api_client.exceptions import ValidationError


def test_config_defaults():
    """Test default configuration values."""
    config = RestApiConfig(base_url="https://api.example.com")

    assert config.base_url == "https://api.example.com"
    assert config.timeout == 30.0
    assert config.max_retries == 3
    assert config.retry_backoff == 1.0
    assert config.verify_ssl is True
    assert config.headers == {}


def test_config_custom_values():
    """Test custom configuration values."""
    config = RestApiConfig(
        base_url="https://custom.api.com",
        timeout=60.0,
        max_retries=5,
        retry_backoff=2.0,
        verify_ssl=False,
        headers={"Authorization": "Bearer token"},
    )

    assert config.timeout == 60.0
    assert config.max_retries == 5
    assert config.retry_backoff == 2.0
    assert config.verify_ssl is False
    assert config.headers is not None
    assert config.headers["Authorization"] == "Bearer token"


def test_config_validation_invalid_url():
    """Test validation rejects invalid URLs."""
    with pytest.raises(ValidationError, match="must start with http"):
        RestApiConfig(base_url="invalid-url")


def test_config_validation_negative_timeout():
    """Test validation rejects negative timeout."""
    with pytest.raises(ValidationError, match="timeout must be positive"):
        RestApiConfig(base_url="https://api.example.com", timeout=-1.0)


def test_config_validation_negative_retries():
    """Test validation rejects negative retries."""
    with pytest.raises(ValidationError, match="max_retries must be non-negative"):
        RestApiConfig(base_url="https://api.example.com", max_retries=-1)


def test_config_validation_negative_backoff():
    """Test validation rejects negative backoff."""
    with pytest.raises(ValidationError, match="retry_backoff must be non-negative"):
        RestApiConfig(base_url="https://api.example.com", retry_backoff=-1.0)
