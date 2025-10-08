"""
Passthrough Mode implementation tests - TDD approach.

These tests define the expected behavior for Passthrough Mode with
Anthropic→Azure fallback on 429 errors, following all explicit user requirements.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.proxy.passthrough import PassthroughProvider, ProviderSwitcher
from amplihack.proxy.passthrough_config import PassthroughConfig


class TestPassthroughProvider:
    """Test core passthrough functionality - forwards ALL requests to api.anthropic.com initially."""

    @pytest.mark.asyncio
    async def test_anthropic_passthrough_success(self):
        """Test successful request forwarding to Anthropic API (EXPLICIT REQUIREMENT)."""
        # EXPLICIT USER REQUIREMENT: Start proxy and pass ALL requests to api.anthropic.com without modifying them initially
        provider = PassthroughProvider(anthropic_api_key="test-key")

        # Mock httpx to simulate Anthropic API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Hello"}}]}
        mock_response.headers = {"content-type": "application/json"}

        with patch.object(provider.client, "request", return_value=mock_response) as mock_request:
            request_data = {"model": "claude-3", "messages": [{"role": "user", "content": "test"}]}

            response = await provider.forward_request(
                method="POST",
                url="/v1/chat/completions",
                headers={"authorization": "Bearer test"},
                body=request_data,
            )

            # Verify request forwarded to api.anthropic.com without modification
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "api.anthropic.com" in call_args[1]["url"]
            assert call_args[1]["json"] == request_data  # Body unmodified
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_429_error_detection(self):
        """Test 429 error detection triggers Azure fallback (EXPLICIT REQUIREMENT)."""
        # EXPLICIT USER REQUIREMENT: Use Anthropic until hitting 429 error, then switch to fallback model (Azure OpenAI)
        provider = PassthroughProvider(anthropic_api_key="test-key")

        # Mock 429 response from Anthropic
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"type": "rate_limit_error"}}
        mock_response.headers = {"content-type": "application/json"}

        with patch.object(provider.client, "request", return_value=mock_response):
            request_data = {"model": "claude-3", "messages": []}

            response = await provider.forward_request(
                method="POST", url="/v1/chat/completions", headers={}, body=request_data
            )

            # Verify 429 error detected
            assert response.status_code == 429
            assert provider.last_error_was_429() is True

    def test_request_headers_preserved(self):
        """Test that request headers are passed through without modification."""
        # EXPLICIT REQUIREMENT: Pass requests without modifying them initially
        provider = PassthroughProvider(anthropic_api_key="test-key")

        original_headers = {
            "authorization": "Bearer test-token",
            "content-type": "application/json",
            "user-agent": "custom-client/1.0",
        }

        prepared_headers = provider._prepare_headers(original_headers)

        # Headers should be preserved (except auth which gets provider key)
        assert prepared_headers["content-type"] == original_headers["content-type"]
        assert prepared_headers["user-agent"] == original_headers["user-agent"]


class TestProviderSwitcher:
    """Test intelligent provider switching logic."""

    def test_429_triggers_azure_fallback(self):
        """Test 429 error triggers switch to Azure OpenAI (EXPLICIT REQUIREMENT)."""
        # EXPLICIT USER REQUIREMENT: Use Anthropic until hitting 429 error, then switch to Azure
        config = {
            "ANTHROPIC_API_KEY": "test-anthropic-key",  # pragma: allowlist secret
            "AZURE_OPENAI_API_KEY": "test-azure-key",  # pragma: allowlist secret
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        }

        # Use a unique state file for this test
        switcher = ProviderSwitcher(config, state_file="test_switch_state.json")

        # Initially should use Anthropic
        assert switcher.get_current_provider() == "anthropic"

        # Simulate 429 error
        switcher.handle_error(429, "rate_limit_error")

        # Should switch to Azure
        assert switcher.get_current_provider() == "azure"

        # Cleanup
        Path("test_switch_state.json").unlink(missing_ok=True)

    def test_cooldown_prevents_rapid_switching(self):
        """Test cooldown mechanism prevents rapid provider switching."""
        config = {
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
            "AZURE_OPENAI_API_KEY": "test-azure-key",  # pragma: allowlist secret
            "PROVIDER_SWITCH_COOLDOWN": "60",  # 60 seconds
        }

        switcher = ProviderSwitcher(config)

        # First switch should work
        switcher.handle_error(429, "rate_limit_error")
        assert switcher.get_current_provider() == "azure"

        # Immediate switch back should be blocked by cooldown
        switcher.handle_error(200, "success")  # Recovery signal
        assert switcher.get_current_provider() == "azure"  # Still Azure due to cooldown

    def test_provider_state_persistence(self):
        """Test provider state persists across restarts."""
        config = {
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
            "AZURE_OPENAI_API_KEY": "test-azure",  # pragma: allowlist secret
        }

        # Create switcher and change state
        switcher1 = ProviderSwitcher(config, state_file="test_state.json")
        switcher1.handle_error(429, "rate_limit_error")  # Switch to Azure

        # Create new switcher instance (simulating restart)
        switcher2 = ProviderSwitcher(config, state_file="test_state.json")

        # State should be preserved
        assert switcher2.get_current_provider() == "azure"

        # Cleanup
        Path("test_state.json").unlink(missing_ok=True)


class TestPassthroughConfig:
    """Test enhanced .env configuration for passthrough mode."""

    def test_enhanced_env_config_loading(self, tmp_path):
        """Test enhanced .env configuration supports passthrough mode (EXPLICIT REQUIREMENT)."""
        # EXPLICIT USER REQUIREMENT: Enhanced .env file configuration design for passthrough mode
        config_file = tmp_path / ".env"
        config_file.write_text("""
# Passthrough Mode Configuration
PASSTHROUGH_MODE=true
ANTHROPIC_API_KEY=sk-ant-test123
AZURE_OPENAI_API_KEY=azure-test-key
AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com/
PROVIDER_SWITCH_COOLDOWN=300
PASSTHROUGH_LOG_LEVEL=INFO
""")

        config = PassthroughConfig(config_file)

        # Verify passthrough mode configuration loaded
        assert config.is_passthrough_enabled() is True
        assert config.get_anthropic_key() == "sk-ant-test123"
        assert config.get_azure_key() == "azure-test-key"
        assert config.get_azure_endpoint() == "https://test.openai.azure.com/"
        assert config.get_switch_cooldown() == 300

    def test_multi_provider_config_validation(self, tmp_path):
        """Test multi-provider configuration management (EXPLICIT REQUIREMENT)."""
        # EXPLICIT USER REQUIREMENT: Multi-provider configuration management
        config_file = tmp_path / ".env"
        config_file.write_text("""
ANTHROPIC_API_KEY=sk-ant-valid-key-12345
AZURE_OPENAI_API_KEY=azure-valid-key-67890
AZURE_OPENAI_ENDPOINT=https://valid.openai.azure.com/
""")

        config = PassthroughConfig(config_file)

        # Verify both providers configured
        providers = config.get_configured_providers()
        assert "anthropic" in providers
        assert "azure" in providers

        # Verify configuration validation
        validation_result = config.validate_configuration()
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0

    def test_invalid_config_handling(self, tmp_path):
        """Test invalid configuration handling with clear error messages."""
        config_file = tmp_path / ".env"
        config_file.write_text("""
PASSTHROUGH_MODE=true
ANTHROPIC_API_KEY=invalid-key
AZURE_OPENAI_ENDPOINT=not-a-url
""")

        config = PassthroughConfig(config_file)
        validation_result = config.validate_configuration()

        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
        assert any("ANTHROPIC_API_KEY" in error for error in validation_result.errors)


class TestIntegration:
    """Integration tests for complete passthrough workflow."""

    @pytest.mark.asyncio
    async def test_anthropic_to_azure_fallback_integration(self):
        """Test complete Anthropic→Azure fallback workflow (EXPLICIT REQUIREMENT)."""
        # EXPLICIT USER REQUIREMENT: Integration with existing proxy system and Azure foundation
        # This test will verify end-to-end integration
        # Will be implemented with actual proxy integration
        # Placeholder for integration test

    def test_existing_proxy_system_integration(self):
        """Test integration with existing proxy system (EXPLICIT REQUIREMENT)."""
        # EXPLICIT USER REQUIREMENT: Integration with existing proxy system and Azure foundation
        # This will test that passthrough mode works with the existing FastAPI proxy
        # Placeholder for proxy integration test
