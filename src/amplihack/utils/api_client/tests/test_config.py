"""Tests for APIClientConfig.

Tests the configuration class using the actual implementation API:
- APIClientConfig(base_url, timeout=30, max_retries=3, backoff_base=0.5,
                  backoff_max=60.0, backoff_jitter=0.25, headers=None)
- Frozen dataclass (immutable)
- Validates base_url, timeout, max_retries, backoff settings

Testing pyramid target: 60% unit tests
"""

import os
from unittest.mock import patch

import pytest


class TestAPIClientConfigImport:
    """Tests for APIClientConfig import and basic creation."""

    def test_import_config_class(self) -> None:
        """Test that APIClientConfig can be imported."""
        from amplihack.utils.api_client.config import APIClientConfig

        assert APIClientConfig is not None

    def test_create_config_with_base_url_only(self) -> None:
        """Test creating config with only base_url."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        assert config.base_url == "https://api.example.com"

    def test_create_config_with_defaults(self) -> None:
        """Test creating config with default values."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        assert config.base_url == "https://api.example.com"
        assert config.timeout == 30  # Default timeout
        assert config.max_retries == 3  # Default retries
        assert config.backoff_base == 0.5  # Default base delay
        assert config.backoff_max == 60.0  # Default max delay
        assert config.backoff_jitter == 0.25  # Default jitter factor

    def test_create_config_with_custom_values(self) -> None:
        """Test creating config with custom values."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(
            base_url="https://api.example.com",
            timeout=60,
            max_retries=5,
            backoff_base=1.0,
            backoff_max=120.0,
            backoff_jitter=0.1,
            default_headers={"Authorization": "Bearer token123"},
        )

        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.backoff_base == 1.0
        assert config.backoff_max == 120.0
        assert config.backoff_jitter == 0.1
        assert config.default_headers == {"Authorization": "Bearer token123"}


class TestAPIClientConfigImmutability:
    """Tests for APIClientConfig immutability (frozen dataclass)."""

    def test_config_is_frozen_immutable(self) -> None:
        """Test that config is immutable (frozen dataclass)."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with pytest.raises((AttributeError, TypeError)):
            config.base_url = "https://other.example.com"  # type: ignore

    def test_config_timeout_immutable(self) -> None:
        """Test that timeout cannot be modified."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with pytest.raises((AttributeError, TypeError)):
            config.timeout = 60  # type: ignore


class TestAPIClientConfigValidation:
    """Tests for APIClientConfig validation."""

    def test_empty_base_url_raises_error(self) -> None:
        """Test that empty base_url raises ConfigurationError."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            APIClientConfig(base_url="")

    def test_whitespace_base_url_raises_error(self) -> None:
        """Test that whitespace-only base_url raises ConfigurationError."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            APIClientConfig(base_url="   ")

    def test_invalid_url_scheme_raises_error(self) -> None:
        """Test that non-HTTP(S) URL raises ConfigurationError."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            APIClientConfig(base_url="ftp://files.example.com")

    def test_negative_timeout_raises_error(self) -> None:
        """Test that negative timeout raises ConfigurationError."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            APIClientConfig(base_url="https://api.example.com", timeout=-1)

    def test_zero_timeout_raises_error(self) -> None:
        """Test that zero timeout raises ConfigurationError."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            APIClientConfig(base_url="https://api.example.com", timeout=0)

    def test_negative_max_retries_raises_error(self) -> None:
        """Test that negative max_retries raises ConfigurationError."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            APIClientConfig(base_url="https://api.example.com", max_retries=-1)

    def test_zero_max_retries_allowed(self) -> None:
        """Test that zero max_retries is allowed (no retries)."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com", max_retries=0)
        assert config.max_retries == 0

    def test_negative_backoff_base_raises_error(self) -> None:
        """Test that negative backoff_base raises ConfigurationError."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            APIClientConfig(base_url="https://api.example.com", backoff_base=-0.5)


class TestAPIClientConfigEquality:
    """Tests for APIClientConfig equality."""

    def test_configs_with_same_values_are_equal(self) -> None:
        """Test that configs with same values are equal."""
        from amplihack.utils.api_client.config import APIClientConfig

        config1 = APIClientConfig(base_url="https://api.example.com", timeout=30)
        config2 = APIClientConfig(base_url="https://api.example.com", timeout=30)

        assert config1 == config2

    def test_configs_with_different_values_are_not_equal(self) -> None:
        """Test that configs with different values are not equal."""
        from amplihack.utils.api_client.config import APIClientConfig

        config1 = APIClientConfig(base_url="https://api1.example.com")
        config2 = APIClientConfig(base_url="https://api2.example.com")

        assert config1 != config2
