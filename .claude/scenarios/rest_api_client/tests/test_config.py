"""Unit tests for configuration module."""

import pytest

# Check if PyYAML is available
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# These imports will fail initially (TDD)
from rest_api_client.config import APIConfig, load_config, merge_configs, validate_config


class TestAPIConfig:
    """Test APIConfig dataclass."""

    def test_create_config_defaults(self):
        """Test creating config with defaults."""
        config = APIConfig()
        assert config.base_url == ""
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.max_retry_delay == 60.0
        assert config.rate_limit_calls == 100
        assert config.rate_limit_period == 60
        assert config.verify_ssl is True
        assert config.headers == {}

    def test_create_config_custom(self):
        """Test creating config with custom values."""
        headers = {"X-API-Key": "secret"}
        config = APIConfig(
            base_url="https://api.example.com",
            timeout=60,
            max_retries=5,
            headers=headers,
            verify_ssl=False,
        )
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.headers == headers
        assert config.verify_ssl is False

    def test_config_immutable(self):
        """Test that config is immutable."""
        from dataclasses import FrozenInstanceError

        config = APIConfig()
        with pytest.raises(FrozenInstanceError):
            config.timeout = 100

    def test_config_validation(self):
        """Test config validation rules."""
        # Negative timeout
        with pytest.raises(ValueError, match="Timeout must be positive"):
            APIConfig(timeout=-1)

        # Negative retries
        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            APIConfig(max_retries=-1)

        # Invalid rate limit
        with pytest.raises(ValueError, match="Rate limit calls must be positive"):
            APIConfig(rate_limit_calls=0)

        # Invalid URL format
        with pytest.raises(ValueError, match="Invalid base URL"):
            APIConfig(base_url="not-a-url")


class TestLoadConfig:
    """Test configuration loading from files."""

    def test_load_from_json(self, tmp_path):
        """Test loading config from JSON file."""
        config_file = tmp_path / "config.json"
        config_file.write_text("""
        {
            "base_url": "https://api.test.com",
            "timeout": 45,
            "headers": {
                "Authorization": "Bearer token"
            }
        }
        """)

        config = load_config(str(config_file))
        assert config.base_url == "https://api.test.com"
        assert config.timeout == 45
        assert config.headers["Authorization"] == "Bearer token"

    @pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
    def test_load_from_yaml(self, tmp_path):
        """Test loading config from YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
        base_url: https://api.test.com
        timeout: 45
        headers:
            Authorization: Bearer token
        """)

        config = load_config(str(config_file))
        assert config.base_url == "https://api.test.com"
        assert config.timeout == 45

    def test_load_from_env(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("API_BASE_URL", "https://env.test.com")
        monkeypatch.setenv("API_TIMEOUT", "90")
        monkeypatch.setenv("API_MAX_RETRIES", "10")
        monkeypatch.setenv("API_VERIFY_SSL", "false")

        config = load_config()
        assert config.base_url == "https://env.test.com"
        assert config.timeout == 90
        assert config.max_retries == 10
        assert config.verify_ssl is False

    def test_load_precedence(self, tmp_path, monkeypatch):
        """Test configuration precedence: env > file > defaults."""
        # File config
        config_file = tmp_path / "config.json"
        config_file.write_text("""
        {
            "base_url": "https://file.test.com",
            "timeout": 60,
            "max_retries": 5
        }
        """)

        # Env config (should override file)
        monkeypatch.setenv("API_TIMEOUT", "120")

        config = load_config(str(config_file))
        assert config.base_url == "https://file.test.com"  # From file
        assert config.timeout == 120  # From env (overrides file)
        assert config.max_retries == 5  # From file

    def test_load_invalid_file(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config("/non/existent/file.json")

    def test_load_malformed_json(self, tmp_path):
        """Test loading malformed JSON."""
        config_file = tmp_path / "bad.json"
        config_file.write_text("not valid json{")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_config(str(config_file))


class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_valid_config(self):
        """Test validating valid configuration."""
        config = {"base_url": "https://api.example.com", "timeout": 30, "max_retries": 3}
        errors = validate_config(config)
        assert errors == []

    def test_validate_invalid_types(self):
        """Test validating config with wrong types."""
        config = {"timeout": "not-a-number", "max_retries": 3.5, "verify_ssl": "yes"}
        errors = validate_config(config)
        assert len(errors) > 0
        assert any("timeout" in str(e) for e in errors)
        assert any("verify_ssl" in str(e) for e in errors)

    def test_validate_out_of_range(self):
        """Test validating config with out-of-range values."""
        config = {"timeout": -10, "max_retries": 1000, "rate_limit_calls": 0}
        errors = validate_config(config)
        assert len(errors) > 0
        assert any("timeout" in str(e) for e in errors)
        assert any("rate_limit" in str(e) for e in errors)


class TestMergeConfigs:
    """Test configuration merging."""

    def test_merge_configs(self):
        """Test merging multiple configurations."""
        base = {"base_url": "https://base.com", "timeout": 30, "headers": {"User-Agent": "Base"}}
        override = {"timeout": 60, "headers": {"Authorization": "Bearer token"}, "max_retries": 5}

        merged = merge_configs(base, override)
        assert merged["base_url"] == "https://base.com"  # From base
        assert merged["timeout"] == 60  # Overridden
        assert merged["max_retries"] == 5  # From override
        # Headers should be merged, not replaced
        assert merged["headers"]["User-Agent"] == "Base"
        assert merged["headers"]["Authorization"] == "Bearer token"

    def test_merge_deep_nested(self):
        """Test merging deeply nested configurations."""
        base = {"retry": {"max_attempts": 3, "backoff": {"initial": 1, "max": 60}}}
        override = {"retry": {"backoff": {"max": 120}}}

        merged = merge_configs(base, override)
        assert merged["retry"]["max_attempts"] == 3
        assert merged["retry"]["backoff"]["initial"] == 1
        assert merged["retry"]["backoff"]["max"] == 120  # Overridden
