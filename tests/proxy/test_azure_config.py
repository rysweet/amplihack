"""
Azure OpenAI proxy configuration and validation tests.

These tests define the expected behavior for Azure OpenAI proxy integration,
following TDD principles to guide implementation.
"""

import os
from pathlib import Path
from unittest.mock import patch

from amplihack.proxy.config import ProxyConfig


class TestAzureEndpointDetection:
    """Tests for Azure vs OpenAI endpoint detection and configuration."""

    def test_detect_azure_endpoint_from_base_url(self, tmp_path):
        """Should detect Azure endpoint from AZURE_OPENAI_BASE_URL."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_BASE_URL=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-azure-key\n"
        )

        config = ProxyConfig(config_file)

        # This will fail until Azure detection is implemented
        assert config.is_azure_endpoint() is True
        assert config.get_endpoint_type() == "azure"

    def test_detect_openai_endpoint_from_base_url(self, tmp_path):
        """Should detect standard OpenAI endpoint."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "OPENAI_BASE_URL=https://api.openai.com/v1\nOPENAI_API_KEY=test-openai-key\n"
        )

        config = ProxyConfig(config_file)

        assert config.is_azure_endpoint() is False
        assert config.get_endpoint_type() == "openai"

    def test_detect_azure_from_endpoint_pattern(self, tmp_path):
        """Should detect Azure from endpoint URL pattern."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "OPENAI_BASE_URL=https://eastus.api.cognitive.microsoft.com/openai\n"
            "AZURE_OPENAI_API_KEY=test-azure-key\n"
        )

        config = ProxyConfig(config_file)

        # Azure endpoints contain 'azure', 'cognitive.microsoft', or specific patterns
        assert config.is_azure_endpoint() is True
        assert config.get_endpoint_type() == "azure"

    def test_default_to_openai_when_ambiguous(self, tmp_path):
        """Should default to OpenAI when endpoint type is unclear."""
        config_file = tmp_path / ".env"
        config_file.write_text("OPENAI_API_KEY=test-key\n")

        config = ProxyConfig(config_file)

        assert config.is_azure_endpoint() is False
        assert config.get_endpoint_type() == "openai"

    def test_explicit_azure_configuration(self, tmp_path):
        """Should handle explicit Azure configuration variables."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-azure-key\n"
            "AZURE_OPENAI_API_VERSION=2024-02-01\n"
        )

        config = ProxyConfig(config_file)

        assert config.is_azure_endpoint() is True
        assert config.get_azure_endpoint() == "https://myresource.openai.azure.com"
        assert config.get_azure_api_version() == "2024-02-01"


class TestAzureConfigValidation:
    """Tests for Azure-specific configuration validation."""

    def test_validate_azure_required_fields(self, tmp_path):
        """Should validate required Azure configuration fields."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-key\n"
        )

        config = ProxyConfig(config_file)

        # Should pass validation with required fields
        assert config.validate_azure_config() is True

    def test_fail_validation_missing_azure_endpoint(self, tmp_path):
        """Should fail validation when Azure endpoint is missing."""
        config_file = tmp_path / ".env"
        config_file.write_text("AZURE_OPENAI_API_KEY=test-key\n")

        config = ProxyConfig(config_file)

        # Should fail without endpoint
        assert config.validate_azure_config() is False

    def test_fail_validation_missing_azure_api_key(self, tmp_path):
        """Should fail validation when Azure API key is missing."""
        config_file = tmp_path / ".env"
        config_file.write_text("AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n")

        config = ProxyConfig(config_file)

        # Should fail without API key
        assert config.validate_azure_config() is False

    def test_validate_azure_endpoint_format(self, tmp_path):
        """Should validate Azure endpoint URL format."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=not-a-valid-url\nAZURE_OPENAI_API_KEY=test-key\n"  # pragma: allowlist secret
        )

        config = ProxyConfig(config_file)

        # Should fail with invalid endpoint format
        assert config.validate_azure_endpoint_format() is False

    def test_validate_azure_api_version(self, tmp_path):
        """Should validate Azure API version format."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-key\n"
            "AZURE_OPENAI_API_VERSION=invalid-version\n"
        )

        config = ProxyConfig(config_file)

        # Should fail with invalid API version format
        assert config.validate_azure_api_version() is False

    def test_validate_with_deployment_names(self, tmp_path):
        """Should validate Azure deployment name configuration."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-key\n"
            "AZURE_GPT4_DEPLOYMENT=gpt-4-32k-deploy\n"  # pragma: allowlist secret
            "AZURE_GPT4_MINI_DEPLOYMENT=gpt-4o-mini-deploy\n"  # pragma: allowlist secret
        )

        config = ProxyConfig(config_file)

        # Should pass with valid deployment names
        assert config.validate_azure_deployments() is True
        assert config.get_azure_deployment("gpt-4") == "gpt-4-32k-deploy"
        assert config.get_azure_deployment("gpt-4o-mini") == "gpt-4o-mini-deploy"


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing OpenAI configurations."""

    def test_existing_openai_config_still_works(self, tmp_path):
        """Should continue to work with existing OpenAI configurations."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "OPENAI_API_KEY=test-openai-key\nOPENAI_BASE_URL=https://api.openai.com/v1\n"
        )

        config = ProxyConfig(config_file)

        # Should validate successfully for OpenAI
        assert config.validate() is True
        assert config.is_azure_endpoint() is False
        assert config.get_endpoint_type() == "openai"

    def test_mixed_config_prefers_explicit_type(self, tmp_path):
        """Should prefer explicit configuration type when both present."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "OPENAI_API_KEY=test-openai-key\n"
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-azure-key\n"
            "PROXY_TYPE=azure\n"
        )

        config = ProxyConfig(config_file)

        # Should prefer Azure when explicitly specified
        assert config.get_endpoint_type() == "azure"
        assert config.is_azure_endpoint() is True

    def test_fallback_behavior_for_legacy_configs(self, tmp_path):
        """Should gracefully handle legacy configuration patterns."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "OPENAI_API_KEY=test-key\n# Legacy comment: This used to be our Azure config\n"
        )

        config = ProxyConfig(config_file)

        # Should default to OpenAI for legacy configs
        assert config.validate() is True
        assert config.get_endpoint_type() == "openai"


class TestAzureConfigErrors:
    """Tests for Azure configuration error handling."""

    def test_missing_config_file_error(self):
        """Should handle missing configuration file gracefully."""
        config = ProxyConfig(Path("nonexistent.env"))

        # Should not crash but indicate invalid config
        assert config.validate() is False
        assert len(config.config) == 0

    def test_invalid_azure_url_error(self, tmp_path):
        """Should provide helpful error for invalid Azure URLs."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=not-a-url\nAZURE_OPENAI_API_KEY=test-key\n"  # pragma: allowlist secret
        )

        config = ProxyConfig(config_file)

        # Should capture validation error with helpful message
        assert config.validate_azure_config() is False
        errors = config.get_validation_errors()
        assert any("Invalid Azure endpoint URL" in error for error in errors)

    def test_empty_azure_api_key_error(self, tmp_path):
        """Should detect empty Azure API key."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\nAZURE_OPENAI_API_KEY=\n"
        )

        config = ProxyConfig(config_file)

        # Should fail validation with empty key
        assert config.validate_azure_config() is False
        errors = config.get_validation_errors()
        assert any("Azure API key cannot be empty" in error for error in errors)

    def test_malformed_config_file_error(self, tmp_path):
        """Should handle malformed configuration files."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT\n"  # Missing = sign
            "AZURE_OPENAI_API_KEY=valid-key\n"
        )

        config = ProxyConfig(config_file)

        # Should skip malformed lines but continue processing
        assert "AZURE_OPENAI_ENDPOINT" not in config.config
        assert config.get("AZURE_OPENAI_API_KEY") == "valid-key"


class TestEnvironmentVariableIntegration:
    """Tests for environment variable integration with Azure config."""

    def test_environment_variables_override_file(self, tmp_path):
        """Should allow environment variables to override file configuration."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://file.openai.azure.com\nAZURE_OPENAI_API_KEY=file-key\n"
        )

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://env.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "env-key",  # pragma: allowlist secret
            },
        ):
            config = ProxyConfig(config_file)

            # Environment should override file
            assert config.get("AZURE_OPENAI_ENDPOINT") == "https://env.openai.azure.com"
            assert config.get("AZURE_OPENAI_API_KEY") == "env-key"

    def test_mixed_file_and_env_variables(self, tmp_path):
        """Should handle mix of file and environment variables."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_VERSION=2024-02-01\n"
        )

        with patch.dict(
            os.environ,
            {"AZURE_OPENAI_API_KEY": "env-key"},  # pragma: allowlist secret
        ):
            config = ProxyConfig(config_file)

            # Should combine file and environment
            assert config.get("AZURE_OPENAI_ENDPOINT") == "https://myresource.openai.azure.com"
            assert config.get("AZURE_OPENAI_API_KEY") == "env-key"
            assert config.get("AZURE_OPENAI_API_VERSION") == "2024-02-01"
