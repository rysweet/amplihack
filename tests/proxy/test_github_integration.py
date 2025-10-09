"""Tests for GitHub Copilot integration components."""

from unittest.mock import Mock, patch

import pytest

from amplihack.proxy.config import ProxyConfig
from amplihack.proxy.github_auth import GitHubAuthManager
from amplihack.proxy.github_detector import GitHubEndpointDetector
from amplihack.proxy.github_models import GitHubModelMapper


class TestGitHubEndpointDetector:
    """Test GitHub endpoint detection."""

    def test_github_api_endpoint_detection(self):
        """Test detection of GitHub API endpoints."""
        detector = GitHubEndpointDetector()

        # Valid GitHub endpoints
        assert detector.is_github_endpoint("https://api.github.com/copilot", {})
        assert detector.is_github_endpoint("https://copilot-proxy.githubusercontent.com", {})

        # Invalid endpoints
        assert not detector.is_github_endpoint("https://api.openai.com", {})
        assert not detector.is_github_endpoint("https://example.com", {})

    def test_github_config_indicators(self):
        """Test detection via configuration indicators."""
        detector = GitHubEndpointDetector()

        # Config with GitHub indicators
        config_with_github = {"GITHUB_TOKEN": "gho_test"}
        assert detector.is_github_endpoint(None, config_with_github)

        config_with_proxy_type = {"PROXY_TYPE": "github_copilot"}
        assert detector.is_github_endpoint(None, config_with_proxy_type)

        # Config without GitHub indicators
        config_without_github = {"OPENAI_API_KEY": "sk-test"}  # pragma: allowlist secret
        assert not detector.is_github_endpoint(None, config_without_github)

    def test_endpoint_type_detection(self):
        """Test endpoint type detection."""
        detector = GitHubEndpointDetector()

        github_config = {"GITHUB_TOKEN": "gho_test"}
        assert detector.get_endpoint_type(None, github_config) == "github_copilot"

        openai_config = {"OPENAI_API_KEY": "sk-test"}  # pragma: allowlist secret
        assert detector.get_endpoint_type(None, openai_config) == "openai"

    def test_canonical_endpoint(self):
        """Test canonical endpoint resolution."""
        detector = GitHubEndpointDetector()

        # Valid endpoint should return as-is
        valid_endpoint = "https://api.github.com/copilot"
        assert detector.get_canonical_endpoint(valid_endpoint) == valid_endpoint

        # Invalid endpoint should return default
        assert (
            detector.get_canonical_endpoint("https://invalid.com")
            == "https://api.github.com/copilot"
        )
        assert detector.get_canonical_endpoint(None) == "https://api.github.com/copilot"


class TestGitHubModelMapper:
    """Test GitHub model mapping."""

    def test_default_model_mapping(self):
        """Test default OpenAI to GitHub model mappings."""
        mapper = GitHubModelMapper({})

        assert mapper.get_github_model("gpt-4") == "copilot-gpt-4"
        assert mapper.get_github_model("gpt-3.5-turbo") == "copilot-gpt-3.5-turbo"
        assert mapper.get_github_model("gpt-4o") == "copilot-gpt-4"

    def test_custom_model_mapping(self):
        """Test custom model mappings from config."""
        config = {"GITHUB_COPILOT_MODEL": "custom-model"}
        mapper = GitHubModelMapper(config)

        # For models with default mappings, should use default, not custom
        assert mapper.get_github_model("gpt-4") == "copilot-gpt-4"

        # For models without default mappings, should use custom
        assert mapper.get_github_model("unknown-model") == "custom-model"

    def test_model_capabilities(self):
        """Test model capability detection."""
        mapper = GitHubModelMapper({})

        # GPT-4 capabilities
        caps = mapper.get_model_capabilities("copilot-gpt-4")
        assert caps["function_calling"] is True
        assert caps["context_window"] == 128000
        assert caps["code_generation"] is True

        # GPT-3.5 capabilities
        caps = mapper.get_model_capabilities("copilot-gpt-3.5-turbo")
        assert caps["function_calling"] is True
        assert caps["context_window"] == 16384

    def test_supported_languages(self):
        """Test programming language support."""
        mapper = GitHubModelMapper({})

        languages = mapper.get_supported_languages("copilot-gpt-4")
        assert "python" in languages
        assert "javascript" in languages
        assert "rust" in languages

    def test_streaming_support(self):
        """Test streaming support detection."""
        mapper = GitHubModelMapper({})

        assert mapper.supports_streaming("copilot-gpt-4") is True
        assert mapper.supports_streaming("copilot-gpt-3.5-turbo") is True


class TestGitHubAuthManager:
    """Test GitHub authentication manager."""

    @patch("subprocess.run")
    def test_existing_token_detection(self, mock_run):
        """Test detection of existing GitHub CLI tokens."""
        auth_manager = GitHubAuthManager()

        # Mock successful gh auth status
        mock_run.side_effect = [
            Mock(returncode=0),  # gh auth status
            Mock(returncode=0, stdout="gho_test_token\n"),  # gh auth token
        ]

        with patch.object(auth_manager, "_verify_copilot_access", return_value=True):
            token = auth_manager.get_existing_token()
            assert token == "gho_test_token"

    @patch("subprocess.run")
    def test_no_existing_token(self, mock_run):
        """Test when no existing token is available."""
        auth_manager = GitHubAuthManager()

        # Mock failed gh auth status
        mock_run.return_value = Mock(returncode=1)

        token = auth_manager.get_existing_token()
        assert token is None

    def test_token_validation(self):
        """Test GitHub token format validation via ProxyConfig."""
        config = ProxyConfig()

        # Valid tokens
        assert config._validate_github_token_format("gho_" + "x" * 20) is True
        assert config._validate_github_token_format("ghp_" + "x" * 20) is True
        assert config._validate_github_token_format("test-token-123") is True

        # Invalid tokens
        assert config._validate_github_token_format("") is False
        assert config._validate_github_token_format("short") is False
        assert config._validate_github_token_format("invalid_prefix_token") is False


class TestProxyConfigGitHubIntegration:
    """Test ProxyConfig GitHub integration."""

    def test_github_endpoint_detection(self):
        """Test GitHub endpoint detection in ProxyConfig."""
        config = ProxyConfig()
        config.config = {"GITHUB_TOKEN": "gho_test"}

        assert config.is_github_endpoint() is True
        assert config.get_endpoint_type() == "github_copilot"

    def test_github_config_validation(self):
        """Test GitHub configuration validation."""
        config = ProxyConfig()
        config.config = {"GITHUB_TOKEN": "gho_" + "x" * 20}

        assert config.validate_github_config() is True

    def test_github_config_validation_failure(self):
        """Test GitHub configuration validation failure."""
        config = ProxyConfig()
        config.config = {}  # Missing token

        assert config.validate_github_config() is False
        assert len(config.get_validation_errors()) > 0

    def test_github_model_mapping(self):
        """Test GitHub model mapping through ProxyConfig."""
        config = ProxyConfig()
        # Use a model that doesn't have a default mapping
        config.config = {"GITHUB_COPILOT_MODEL": "custom-model"}
        # Reinitialize the mapper with new config
        config._github_mapper = GitHubModelMapper(config.config)

        # Test with a model that has default mapping - should use default
        assert config.get_github_model("gpt-4") == "copilot-gpt-4"

        # Test with a model that has no default mapping - should use custom
        assert config.get_github_model("unknown-model") == "custom-model"

    def test_github_token_retrieval(self):
        """Test GitHub token retrieval."""
        config = ProxyConfig()
        config.config = {"GITHUB_TOKEN": "gho_test_token"}

        assert config.get_github_token() == "gho_test_token"

    def test_github_copilot_enabled_detection(self):
        """Test GitHub Copilot enabled detection."""
        config = ProxyConfig()

        # Test enabled values
        for enabled_value in ["true", "1", "yes", "on"]:
            config.config = {"GITHUB_COPILOT_ENABLED": enabled_value}
            assert config.is_github_copilot_enabled() is True

        # Test disabled values
        for disabled_value in ["false", "0", "no", "off", ""]:
            config.config = {"GITHUB_COPILOT_ENABLED": disabled_value}
            assert config.is_github_copilot_enabled() is False

    def test_full_validation_with_github(self):
        """Test full configuration validation with GitHub setup."""
        config = ProxyConfig()
        config.config = {
            "GITHUB_TOKEN": "gho_" + "x" * 20,
            "GITHUB_COPILOT_ENABLED": "true",
            "PROXY_TYPE": "github_copilot",
        }

        assert config.validate() is True


if __name__ == "__main__":
    pytest.main([__file__])
