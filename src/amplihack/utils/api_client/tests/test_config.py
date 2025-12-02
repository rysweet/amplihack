"""Tests for APIClientConfig.

Tests the configuration dataclass using the actual implementation API:
- APIClientConfig(base_url, timeout, max_retries, retry_base_delay, ...)
- Frozen dataclass with validation in __post_init__
- Optional from_env() class method

Testing pyramid target: 60% unit tests
"""

import os
from unittest.mock import patch

import pytest


class TestAPIClientConfig:
    """Tests for APIClientConfig frozen dataclass."""

    def test_import_config_class(self) -> None:
        """Test that APIClientConfig can be imported."""
        from amplihack.utils.api_client.config import APIClientConfig

        assert APIClientConfig is not None

    def test_create_config_with_defaults(self) -> None:
        """Test creating config with default values."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        assert config.base_url == "https://api.example.com"
        assert config.timeout == 30  # Default timeout
        assert config.max_retries == 3  # Default retries
        assert config.retry_base_delay == 0.5  # Default base delay
        assert config.retry_max_delay == 60.0  # Default max delay
        assert config.retry_multiplier == 1.5  # Default multiplier

    def test_create_config_with_custom_values(self) -> None:
        """Test creating config with custom values."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(
            base_url="https://api.example.com",
            timeout=60,
            max_retries=5,
            retry_base_delay=1.0,
            retry_max_delay=120.0,
            retry_multiplier=2.0,
            default_headers={"Authorization": "Bearer token123"},
        )

        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_base_delay == 1.0
        assert config.retry_max_delay == 120.0
        assert config.retry_multiplier == 2.0
        assert config.default_headers == {"Authorization": "Bearer token123"}

    def test_config_is_frozen_immutable(self) -> None:
        """Test that config is immutable (frozen dataclass)."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with pytest.raises((AttributeError, TypeError)):
            config.base_url = "https://other.example.com"  # type: ignore

        with pytest.raises((AttributeError, TypeError)):
            config.timeout = 60  # type: ignore


class TestAPIClientConfigValidation:
    """Tests for APIClientConfig validation in __post_init__."""

    def test_empty_base_url_raises_error(self) -> None:
        """Test that empty base_url raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="base_url"):
            APIClientConfig(base_url="")

    def test_whitespace_base_url_raises_error(self) -> None:
        """Test that whitespace-only base_url raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="base_url"):
            APIClientConfig(base_url="   ")

    def test_invalid_url_scheme_raises_error(self) -> None:
        """Test that non-HTTP(S) URL raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="http"):
            APIClientConfig(base_url="ftp://files.example.com")

    def test_negative_timeout_raises_error(self) -> None:
        """Test that negative timeout raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="timeout"):
            APIClientConfig(base_url="https://api.example.com", timeout=-1)

    def test_zero_timeout_raises_error(self) -> None:
        """Test that zero timeout raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="timeout"):
            APIClientConfig(base_url="https://api.example.com", timeout=0)

    def test_negative_max_retries_raises_error(self) -> None:
        """Test that negative max_retries raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="max_retries"):
            APIClientConfig(base_url="https://api.example.com", max_retries=-1)

    def test_zero_max_retries_allowed(self) -> None:
        """Test that zero max_retries is allowed (no retries)."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com", max_retries=0)
        assert config.max_retries == 0

    def test_negative_retry_base_delay_raises_error(self) -> None:
        """Test that negative retry_base_delay raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="retry_base_delay"):
            APIClientConfig(base_url="https://api.example.com", retry_base_delay=-0.5)

    def test_retry_multiplier_less_than_one_raises_error(self) -> None:
        """Test that retry_multiplier < 1 raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="retry_multiplier"):
            APIClientConfig(base_url="https://api.example.com", retry_multiplier=0.5)

    def test_retry_max_delay_less_than_base_delay_raises_error(self) -> None:
        """Test that retry_max_delay < retry_base_delay raises ValueError."""
        from amplihack.utils.api_client.config import APIClientConfig

        with pytest.raises(ValueError, match="retry_max_delay"):
            APIClientConfig(
                base_url="https://api.example.com",
                retry_base_delay=10.0,
                retry_max_delay=5.0,
            )


class TestAPIClientConfigFromEnv:
    """Tests for APIClientConfig.from_env() class method."""

    def test_from_env_with_required_base_url(self) -> None:
        """Test from_env() with API_BASE_URL environment variable."""
        from amplihack.utils.api_client.config import APIClientConfig

        with patch.dict(os.environ, {"API_BASE_URL": "https://env.example.com"}, clear=True):
            config = APIClientConfig.from_env()
            assert config.base_url == "https://env.example.com"

    def test_from_env_missing_base_url_raises_error(self) -> None:
        """Test from_env() raises error when API_BASE_URL is missing."""
        from amplihack.utils.api_client.config import APIClientConfig

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API_BASE_URL"):
                APIClientConfig.from_env()

    def test_from_env_with_custom_prefix(self) -> None:
        """Test from_env() with custom environment variable prefix."""
        from amplihack.utils.api_client.config import APIClientConfig

        env_vars = {
            "MYAPP_API_BASE_URL": "https://myapp.example.com",
            "MYAPP_API_TIMEOUT": "45",
            "MYAPP_API_MAX_RETRIES": "5",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = APIClientConfig.from_env(prefix="MYAPP_API_")
            assert config.base_url == "https://myapp.example.com"
            assert config.timeout == 45
            assert config.max_retries == 5

    def test_from_env_with_all_optional_values(self) -> None:
        """Test from_env() with all optional environment variables."""
        from amplihack.utils.api_client.config import APIClientConfig

        env_vars = {
            "API_BASE_URL": "https://full.example.com",
            "API_TIMEOUT": "60",
            "API_MAX_RETRIES": "10",
            "API_RETRY_BASE_DELAY": "1.0",
            "API_RETRY_MAX_DELAY": "120.0",
            "API_RETRY_MULTIPLIER": "2.0",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = APIClientConfig.from_env()
            assert config.base_url == "https://full.example.com"
            assert config.timeout == 60
            assert config.max_retries == 10
            assert config.retry_base_delay == 1.0
            assert config.retry_max_delay == 120.0
            assert config.retry_multiplier == 2.0

    def test_from_env_invalid_timeout_raises_error(self) -> None:
        """Test from_env() with invalid timeout value raises error."""
        from amplihack.utils.api_client.config import APIClientConfig

        with patch.dict(
            os.environ, {"API_BASE_URL": "https://api.example.com", "API_TIMEOUT": "not_a_number"}
        ):
            with pytest.raises(ValueError, match="API_TIMEOUT"):
                APIClientConfig.from_env()

    def test_from_env_uses_defaults_for_missing_optional(self) -> None:
        """Test from_env() uses defaults when optional env vars missing."""
        from amplihack.utils.api_client.config import APIClientConfig

        with patch.dict(os.environ, {"API_BASE_URL": "https://api.example.com"}, clear=True):
            config = APIClientConfig.from_env()
            assert config.timeout == 30  # Default
            assert config.max_retries == 3  # Default


class TestAPIClientConfigEquality:
    """Tests for APIClientConfig equality and hashing."""

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

    def test_config_is_hashable(self) -> None:
        """Test that config can be used in sets and as dict keys."""
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        # Should be hashable
        config_set = {config}
        assert config in config_set

        config_dict = {config: "value"}
        assert config_dict[config] == "value"
