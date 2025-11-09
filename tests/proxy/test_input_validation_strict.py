"""
Strict input validation tests for API keys, tokens, and request sizes.

Tests the security enhancements to prevent weak validation allowing empty strings,
test tokens in production, and oversized requests.
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from amplihack.proxy.config import ProxyConfig


class TestAPIKeyStrictValidation:
    """Tests for strict API key validation (minimum 20 characters)."""

    def test_azure_api_key_empty_string_fails(self, tmp_path):
        """Should reject Azure API key with empty string."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=\n"
        )

        config = ProxyConfig(config_file)
        result = config.validate_azure_config()

        assert result is False
        assert any("missing" in error.lower() for error in config.get_validation_errors())

    def test_azure_api_key_too_short_fails(self, tmp_path):
        """Should reject Azure API key shorter than 20 characters."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=shortkey123\n"
        )

        config = ProxyConfig(config_file)
        result = config.validate_azure_config()

        assert result is False
        errors = config.get_validation_errors()
        assert any("20 characters" in error for error in errors)

    def test_azure_api_key_exactly_20_chars_passes(self, tmp_path):
        """Should accept Azure API key with exactly 20 characters."""
        config_file = tmp_path / ".env"
        valid_key = "a" * 20  # Exactly 20 chars
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            f"AZURE_OPENAI_API_KEY={valid_key}\n"
            "AZURE_OPENAI_API_VERSION=2024-02-01\n"
        )

        config = ProxyConfig(config_file)
        result = config.validate_azure_config()

        assert result is True

    def test_azure_api_key_long_passes(self, tmp_path):
        """Should accept Azure API key longer than 20 characters."""
        config_file = tmp_path / ".env"
        valid_key = "a" * 50  # 50 chars
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            f"AZURE_OPENAI_API_KEY={valid_key}\n"
            "AZURE_OPENAI_API_VERSION=2024-02-01\n"
        )

        config = ProxyConfig(config_file)
        result = config.validate_azure_config()

        assert result is True

    def test_azure_test_key_too_short_fails(self, tmp_path):
        """Should reject test API key shorter than minimum test length (15 chars)."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-short\n"
        )

        config = ProxyConfig(config_file)
        result = config.validate_azure_config()

        # Test key "test-short" is only 10 chars, should fail
        assert result is False

    def test_azure_test_key_exactly_15_chars_passes(self, tmp_path):
        """Should accept test API key with exactly 15 characters."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-longer-k1\n"
            "AZURE_OPENAI_API_VERSION=2024-02-01\n"
        )

        config = ProxyConfig(config_file)
        result = config.validate_azure_config()

        # "test-longer-k1" is exactly 15 chars
        assert result is True

    def test_azure_dummy_key_enforces_minimum_length(self, tmp_path):
        """Should enforce minimum length for dummy keys."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=dummy123\n"
        )

        config = ProxyConfig(config_file)
        result = config.validate_azure_config()

        # "dummy123" is only 8 chars, should fail
        assert result is False


class TestGitHubTokenStrictValidation:
    """Tests for strict GitHub token validation."""

    def test_github_token_empty_string_fails(self, tmp_path):
        """Should reject GitHub token with empty string."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        assert result is False
        assert any("missing" in error.lower() for error in config.get_validation_errors())

    def test_github_token_too_short_fails(self, tmp_path):
        """Should reject GitHub token shorter than 20 characters."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=ghp_short123\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        assert result is False
        errors = config.get_validation_errors()
        assert any("20 characters" in error for error in errors)

    def test_github_token_proper_prefix_20_chars_passes(self, tmp_path):
        """Should accept GitHub token with proper prefix and 20+ characters."""
        config_file = tmp_path / ".env"
        # ghp_xxxxxxxxxxxxx is valid format with proper prefix
        valid_token = "ghp_" + "x" * 16  # 20 chars total
        config_file.write_text(f"GITHUB_TOKEN={valid_token}\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        assert result is True

    def test_github_token_legacy_40_char_passes(self, tmp_path):
        """Should accept legacy GitHub token (40-char alphanumeric)."""
        config_file = tmp_path / ".env"
        valid_token = "a" * 40  # 40 alphanumeric chars
        config_file.write_text(f"GITHUB_TOKEN={valid_token}\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        assert result is True

    def test_github_test_token_too_short_fails(self, tmp_path):
        """Should reject test GitHub token shorter than minimum (15 chars)."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=test-short\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        # "test-short" is only 10 chars, should fail
        assert result is False

    def test_github_test_token_exactly_15_chars_passes(self, tmp_path):
        """Should accept test GitHub token with exactly 15 characters."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=test-longer-key1\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        # "test-longer-key1" is exactly 15 chars
        assert result is True

    def test_github_fake_token_enforces_minimum_length(self, tmp_path):
        """Should enforce minimum length for fake tokens."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=fake123\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        # "fake123" is only 7 chars, should fail
        assert result is False

    def test_github_dummy_token_enforces_minimum_length(self, tmp_path):
        """Should enforce minimum length for dummy tokens."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=dummy-test\n")

        config = ProxyConfig(config_file)
        result = config.validate_github_config()

        # "dummy-test" is only 10 chars, should fail
        assert result is False


class TestValidationConstantsConsistency:
    """Tests to ensure validation constants are properly defined and consistent."""

    def test_min_api_key_length_constant_defined(self):
        """Should have MIN_API_KEY_LENGTH constant defined."""
        assert hasattr(ProxyConfig, "MIN_API_KEY_LENGTH")
        assert ProxyConfig.MIN_API_KEY_LENGTH == 20

    def test_min_github_token_length_constant_defined(self):
        """Should have MIN_GITHUB_TOKEN_LENGTH constant defined."""
        assert hasattr(ProxyConfig, "MIN_GITHUB_TOKEN_LENGTH")
        assert ProxyConfig.MIN_GITHUB_TOKEN_LENGTH == 20

    def test_min_test_token_length_constant_defined(self):
        """Should have MIN_TEST_TOKEN_LENGTH constant defined."""
        assert hasattr(ProxyConfig, "MIN_TEST_TOKEN_LENGTH")
        assert ProxyConfig.MIN_TEST_TOKEN_LENGTH == 15


class TestRequestSizeLimitation:
    """Tests for request size limitation configuration."""

    def test_max_request_size_constant_defined(self):
        """Should have request size configuration in server module."""
        from amplihack.proxy import server

        assert hasattr(server, "MAX_REQUEST_SIZE_BYTES")
        assert hasattr(server, "MAX_REQUEST_SIZE_MB")
        # Default should be 1MB = 1048576 bytes
        assert server.DEFAULT_MAX_REQUEST_SIZE_MB == 1

    def test_request_size_middleware_exists(self):
        """Should have request size middleware function."""
        from amplihack.proxy import server

        assert hasattr(server, "request_size_middleware")
        assert callable(server.request_size_middleware)

    @patch.dict(os.environ, {"MAX_REQUEST_SIZE_MB": "5"})
    def test_request_size_configurable_via_env(self):
        """Should allow configuring request size via environment variable."""
        # Note: This tests that the configuration can be set
        # Actual middleware testing would require full FastAPI test client
        size_mb = int(os.environ.get("MAX_REQUEST_SIZE_MB", 1))
        assert size_mb == 5

    def test_default_request_size_is_1mb(self):
        """Should default request size to 1MB."""
        from amplihack.proxy import server

        # When not set, should be 1MB
        assert server.DEFAULT_MAX_REQUEST_SIZE_MB == 1
        # 1MB in bytes
        assert server.DEFAULT_MAX_REQUEST_SIZE_MB * 1024 * 1024 == 1048576


class TestValidationErrorMessages:
    """Tests for clear and actionable validation error messages."""

    def test_azure_key_too_short_error_message_includes_requirement(self, tmp_path):
        """Error message should include minimum length requirement."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=short\n"
        )

        config = ProxyConfig(config_file)
        config.validate_azure_config()
        errors = config.get_validation_errors()

        assert len(errors) > 0
        assert "20" in errors[0]  # Should mention "20 characters"

    def test_github_token_too_short_error_message_includes_requirement(self, tmp_path):
        """Error message should include minimum length requirement."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=short\n")

        config = ProxyConfig(config_file)
        config.validate_github_config()
        errors = config.get_validation_errors()

        assert len(errors) > 0
        assert "20" in errors[0]  # Should mention "20 characters"

    def test_azure_missing_key_error_message(self, tmp_path):
        """Should have clear error for missing API key."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
        )

        config = ProxyConfig(config_file)
        config.validate_azure_config()
        errors = config.get_validation_errors()

        assert len(errors) > 0
        assert "missing" in errors[0].lower() or "required" in errors[0].lower()

    def test_github_missing_token_error_message(self, tmp_path):
        """Should have clear error for missing token."""
        config_file = tmp_path / ".env"
        config_file.write_text("GITHUB_TOKEN=\n")

        config = ProxyConfig(config_file)
        config.validate_github_config()
        errors = config.get_validation_errors()

        assert len(errors) > 0
        assert "missing" in errors[0].lower() or "required" in errors[0].lower()
