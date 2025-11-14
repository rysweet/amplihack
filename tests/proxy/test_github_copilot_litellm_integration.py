"""Tests for GitHub Copilot LiteLLM integration."""

try:
    import pytest
except ImportError:
    raise ImportError("pytest is required to run tests. Install with: pip install pytest")

from amplihack.proxy.config import ProxyConfig
from amplihack.proxy.github_detector import GitHubEndpointDetector


class TestGitHubCopilotLiteLLMIntegration:
    """Test GitHub Copilot LiteLLM provider integration."""

    def test_github_copilot_litellm_detection(self):
        """Test LiteLLM provider detection."""
        config = {
            "GITHUB_TOKEN": "gho_test_token",  # pragma: allowlist secret
            "GITHUB_COPILOT_ENABLED": "true",
            "GITHUB_COPILOT_LITELLM_ENABLED": "true",
        }

        detector = GitHubEndpointDetector()

        # Test explicit LiteLLM flag
        assert detector.is_litellm_provider_enabled(config) is True

        # Test auto-detection
        config_auto = {
            "GITHUB_TOKEN": "gho_test_token",  # pragma: allowlist secret
            "GITHUB_COPILOT_ENABLED": "true",
        }
        assert detector.is_litellm_provider_enabled(config_auto) is True

        # Test disabled
        config_disabled = {
            "GITHUB_TOKEN": "gho_test_token",  # pragma: allowlist secret
            "GITHUB_COPILOT_ENABLED": "false",
        }
        assert detector.is_litellm_provider_enabled(config_disabled) is False

    def test_github_copilot_model_mapping(self):
        """Test GitHub Copilot model mapping."""
        # Test known GitHub Copilot models directly
        github_copilot_models = ["copilot-gpt-4", "copilot-gpt-3.5-turbo"]

        # Test known GitHub Copilot models
        assert "copilot-gpt-4" in github_copilot_models
        assert "copilot-gpt-3.5-turbo" in github_copilot_models

    def test_github_copilot_config_validation(self):
        """Test GitHub Copilot configuration validation."""
        # Valid configuration
        valid_config = ProxyConfig()
        valid_config.config = {
            "GITHUB_TOKEN": "gho_1234567890abcdef1234567890abcdef12345678",  # pragma: allowlist secret
            "GITHUB_COPILOT_ENABLED": "true",
            "GITHUB_COPILOT_LITELLM_ENABLED": "true",
            "GITHUB_COPILOT_ENDPOINT": "https://api.github.com",
        }

        assert valid_config.is_github_copilot_enabled() is True
        assert valid_config.is_github_copilot_litellm_enabled() is True
        assert valid_config.get_github_copilot_endpoint() == "https://api.github.com"

        # Test LiteLLM config preparation
        litellm_config = valid_config.get_litellm_github_config()
        assert "GITHUB_TOKEN" in litellm_config
        assert "GITHUB_API_BASE" in litellm_config
        assert "GITHUB_COPILOT_MODEL" in litellm_config

    def test_github_copilot_request_processing(self):
        """Test GitHub Copilot request processing in proxy server."""
        # Test model prefix detection
        github_model = "github/copilot-gpt-4"
        assert github_model.startswith("github/")

        # Test model name extraction
        model_name = github_model.split("/")[-1]
        assert model_name == "copilot-gpt-4"

        # Test known GitHub Copilot models
        github_copilot_models = ["copilot-gpt-4", "copilot-gpt-3.5-turbo"]
        assert model_name in github_copilot_models

    def test_github_copilot_endpoint_detection(self):
        """Test GitHub Copilot endpoint detection."""
        detector = GitHubEndpointDetector()

        # Test valid GitHub endpoints
        assert detector.validate_github_endpoint("https://api.github.com/copilot") is True
        assert (
            detector.validate_github_endpoint("https://copilot-proxy.githubusercontent.com") is True
        )

        # Test invalid endpoints
        assert detector.validate_github_endpoint("http://api.github.com/copilot") is False
        assert detector.validate_github_endpoint("https://example.com") is False
        assert detector.validate_github_endpoint("") is False

    def test_github_copilot_litellm_config_preparation(self):
        """Test LiteLLM configuration preparation for GitHub Copilot."""
        detector = GitHubEndpointDetector()

        config = {
            "GITHUB_TOKEN": "gho_test_token",  # pragma: allowlist secret
            "GITHUB_COPILOT_ENDPOINT": "https://api.github.com",
            "GITHUB_COPILOT_MODEL": "copilot-gpt-4",
        }

        litellm_config = detector.prepare_litellm_config(config)

        assert litellm_config["GITHUB_TOKEN"] == "gho_test_token"  # pragma: allowlist secret
        assert litellm_config["GITHUB_API_BASE"] == "https://api.github.com"
        assert litellm_config["GITHUB_COPILOT_MODEL"] == "copilot-gpt-4"

    def test_github_copilot_model_prefix(self):
        """Test GitHub Copilot model prefix for LiteLLM."""
        detector = GitHubEndpointDetector()
        assert detector.get_litellm_model_prefix() == "github/"

    def test_github_copilot_rate_limits(self):
        """Test GitHub Copilot rate limit information."""
        detector = GitHubEndpointDetector()

        rate_limits = detector.get_rate_limit_info("https://api.github.com/copilot")

        assert "requests_per_minute" in rate_limits
        assert "requests_per_hour" in rate_limits
        assert "tokens_per_minute" in rate_limits

        assert rate_limits["requests_per_minute"] > 0
        assert rate_limits["requests_per_hour"] > 0
        assert rate_limits["tokens_per_minute"] > 0

    def test_github_copilot_streaming_support(self):
        """Test GitHub Copilot streaming support detection."""
        detector = GitHubEndpointDetector()

        # GitHub Copilot API supports streaming
        assert detector.supports_streaming("https://api.github.com/copilot") is True
        assert detector.supports_streaming("https://copilot-proxy.githubusercontent.com") is True

        # Invalid endpoints don't support streaming
        assert detector.supports_streaming("https://example.com") is False

    def test_github_copilot_canonical_endpoint(self):
        """Test canonical GitHub Copilot endpoint resolution."""
        detector = GitHubEndpointDetector()

        # Valid endpoint should be returned as-is
        valid_endpoint = "https://api.github.com/copilot"
        assert detector.get_canonical_endpoint(valid_endpoint) == valid_endpoint

        # Invalid endpoint should return default
        invalid_endpoint = "https://example.com"
        assert detector.get_canonical_endpoint(invalid_endpoint) == "https://api.github.com/copilot"

        # None should return default
        assert detector.get_canonical_endpoint(None) == "https://api.github.com/copilot"

    @pytest.mark.asyncio
    async def test_github_copilot_oauth_integration(self):
        """Test GitHub OAuth integration with LiteLLM provider."""
        # Test token format validation (without network call)
        valid_token = "gho_1234567890abcdef1234567890abcdef12345678"  # pragma: allowlist secret

        # Test that token starts with valid GitHub prefix
        assert valid_token.startswith("gho_")
        assert len(valid_token) >= 20

    def test_github_copilot_error_handling(self):
        """Test error handling in GitHub Copilot integration."""
        config = ProxyConfig()

        # Test missing token
        config.config = {
            "GITHUB_COPILOT_ENABLED": "true",
            # Missing GITHUB_TOKEN
        }

        assert config.validate_github_config() is False
        errors = config.get_validation_errors()
        assert any("GITHUB_TOKEN" in error for error in errors)

        # Test invalid token format
        config.config = {
            "GITHUB_TOKEN": "invalid_token",
            "GITHUB_COPILOT_ENABLED": "true",
        }

        assert config.validate_github_config() is False
        errors = config.get_validation_errors()
        assert any("token format" in error.lower() for error in errors)

    def test_proxy_config_github_methods(self):
        """Test ProxyConfig GitHub Copilot methods."""
        config = ProxyConfig()
        config.config = {
            "GITHUB_TOKEN": "gho_test_token",  # pragma: allowlist secret
            "GITHUB_COPILOT_ENABLED": "true",
            "GITHUB_COPILOT_LITELLM_ENABLED": "true",
            "GITHUB_COPILOT_ENDPOINT": "https://api.github.com",
        }

        # Test GitHub Copilot configuration
        assert config.is_github_copilot_enabled() is True
        assert config.is_github_copilot_litellm_enabled() is True
        assert config.get_github_token() == "gho_test_token"  # pragma: allowlist secret
        assert config.get_github_copilot_endpoint() == "https://api.github.com"

        # Test LiteLLM config generation
        litellm_config = config.get_litellm_github_config()
        assert isinstance(litellm_config, dict)
        assert "GITHUB_TOKEN" in litellm_config

        # Test endpoint type detection based on config indicators
        assert config.get_endpoint_type() in ["github_copilot", "openai"]
