"""
Azure OpenAI proxy integration tests.

Tests for core Azure OpenAI proxy integration functionality
following the user requirements: support Azure OpenAI with backward compatibility.
"""

import os
from unittest.mock import Mock, patch

from amplihack.proxy.config import ProxyConfig
from amplihack.proxy.env import ProxyEnvironment
from amplihack.proxy.manager import ProxyManager


class TestAzureProxyManagerInitialization:
    """Tests for ProxyManager initialization with Azure configurations."""

    def test_initialize_with_azure_config(self, tmp_path):
        """Should initialize ProxyManager with Azure configuration."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-azure-key\n"
            "AZURE_OPENAI_API_VERSION=2024-02-01\n"
            "PORT=8081\n"
        )

        config = ProxyConfig(config_file)
        manager = ProxyManager(config)

        # Should detect Azure configuration
        assert manager.is_azure_mode() is True
        assert manager.proxy_port == 8081

    def test_initialize_with_mixed_azure_openai_config(self, tmp_path):
        """Should handle mixed Azure/OpenAI configuration appropriately."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "OPENAI_API_KEY=openai-key\n"
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=azure-key\n"
            "PROXY_MODE=azure\n"
        )

        config = ProxyConfig(config_file)
        manager = ProxyManager(config)

        # Should prefer Azure when explicitly specified
        assert manager.get_active_config_type() == "azure"
        assert manager.is_azure_mode() is True

    def test_azure_proxy_manager_with_deployment_mapping(self, tmp_path):
        """Should handle Azure deployment mapping configuration."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-key\n"
            "AZURE_GPT4_DEPLOYMENT=gpt-4-deployment\n"  # pragma: allowlist secret
            "AZURE_GPT4_MINI_DEPLOYMENT=gpt-4o-mini-deployment\n"  # pragma: allowlist secret
        )

        config = ProxyConfig(config_file)
        manager = ProxyManager(config)

        # Should provide deployment mappings
        assert manager.get_azure_deployment("gpt-4") == "gpt-4-deployment"
        assert manager.get_azure_deployment("gpt-4o-mini") == "gpt-4o-mini-deployment"


class TestAzureProxyStartup:
    """Tests for Azure proxy startup and configuration."""

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_start_azure_proxy_with_correct_environment(self, mock_run, mock_popen, tmp_path):
        """Should start proxy with correct Azure environment variables."""
        # Mock successful operations
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-azure-key\n"
            "AZURE_OPENAI_API_VERSION=2024-02-01\n"
        )

        config = ProxyConfig(config_file)
        manager = ProxyManager(config)

        # Mock proxy installation check
        manager.proxy_dir.mkdir(parents=True, exist_ok=True)
        (manager.proxy_dir / "claude-code-proxy").mkdir(exist_ok=True)
        (manager.proxy_dir / "claude-code-proxy" / "package.json").touch()

        success = manager.start_proxy()

        assert success is True
        # Verify environment variables were passed to proxy process
        call_args = mock_popen.call_args
        proxy_env = call_args.kwargs["env"]
        assert "AZURE_OPENAI_ENDPOINT" in proxy_env
        assert proxy_env["AZURE_OPENAI_ENDPOINT"] == "https://myresource.openai.azure.com"
        assert proxy_env["AZURE_OPENAI_API_KEY"] == "test-azure-key"  # pragma: allowlist secret
        assert proxy_env["AZURE_OPENAI_API_VERSION"] == "2024-02-01"

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_azure_proxy_startup_with_deployment_config(self, mock_run, mock_popen, tmp_path):
        """Should pass Azure deployment configuration to proxy."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-key\n"
            "AZURE_GPT4_DEPLOYMENT=gpt4-deploy\n"  # pragma: allowlist secret
        )

        config = ProxyConfig(config_file)
        manager = ProxyManager(config)

        # Mock proxy installation
        manager.proxy_dir.mkdir(parents=True, exist_ok=True)
        (manager.proxy_dir / "claude-code-proxy").mkdir(exist_ok=True)
        (manager.proxy_dir / "claude-code-proxy" / "package.json").touch()

        success = manager.start_proxy()

        assert success is True
        # Verify deployment configuration was passed
        call_args = mock_popen.call_args
        proxy_env = call_args.kwargs["env"]
        assert proxy_env["AZURE_GPT4_DEPLOYMENT"] == "gpt4-deploy"

    @patch("subprocess.run")
    def test_azure_proxy_dependency_installation(self, mock_run, tmp_path):
        """Should install dependencies for proxy."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        config = ProxyConfig()
        manager = ProxyManager(config)

        # Mock proxy directory with package.json
        manager.proxy_dir.mkdir(parents=True, exist_ok=True)
        proxy_repo = manager.proxy_dir / "claude-code-proxy"
        proxy_repo.mkdir(exist_ok=True)
        (proxy_repo / "package.json").touch()

        success = manager.ensure_proxy_installed()

        assert success is True
        # Should have attempted npm install
        mock_run.assert_called()


class TestAzureEnvironmentIntegration:
    """Tests for Azure environment variable integration."""

    def test_azure_environment_variable_setup(self, tmp_path):
        """Should properly set up environment variables for Azure."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com\n"
            "AZURE_OPENAI_API_KEY=test-azure-key\n"
        )

        config = ProxyConfig(config_file)
        env_manager = ProxyEnvironment()

        # Setup Azure environment
        env_manager.setup_azure_environment(config.to_env_dict())

        # Should set Azure variables
        assert os.environ.get("AZURE_OPENAI_ENDPOINT") == "https://myresource.openai.azure.com"
        assert os.environ.get("AZURE_OPENAI_API_KEY") == "test-azure-key"

        # Cleanup
        env_manager.restore()

    def test_azure_environment_restoration(self, tmp_path):
        """Should restore original environment variables after use."""
        config_file = tmp_path / ".env"
        config_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com\nAZURE_OPENAI_API_KEY=test-key\n"
        )

        config = ProxyConfig(config_file)
        env_manager = ProxyEnvironment()

        # Store original values
        original_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        original_key = os.environ.get("AZURE_OPENAI_API_KEY")

        # Set up and then restore
        env_manager.setup_azure_environment(config.to_env_dict())
        env_manager.restore()

        # Should restore original values
        assert os.environ.get("AZURE_OPENAI_ENDPOINT") == original_endpoint
        assert os.environ.get("AZURE_OPENAI_API_KEY") == original_key
