"""Environment variable management for proxy integration."""

import os
from typing import Dict, Optional


class ProxyEnvironment:
    """Manages environment variables for Claude Code proxy."""

    def __init__(self):
        """Initialize environment manager."""
        self.original_env: Dict[str, Optional[str]] = {}

    def setup(
        self,
        proxy_port: int = 8080,
        api_key: Optional[str] = None,
        azure_config: Optional[Dict[str, str]] = None,
    ) -> None:
        """Set up environment variables for proxy.

        Args:
            proxy_port: Port where proxy is running.
            api_key: Anthropic API key to use.
            azure_config: Azure configuration dictionary.
        """
        # Store original values
        self.original_env["ANTHROPIC_BASE_URL"] = os.environ.get("ANTHROPIC_BASE_URL")
        self.original_env["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY")

        # Store Azure environment variables if they exist
        azure_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_BASE_URL",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_API_VERSION",
            "OPENAI_API_BASE",
            "OPENAI_BASE_URL",
        ]
        for var in azure_vars:
            self.original_env[var] = os.environ.get(var)

        # Set proxy environment variables
        os.environ["ANTHROPIC_BASE_URL"] = f"http://localhost:{proxy_port}"

        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

        # Set up Azure environment variables if provided
        if azure_config:
            self.setup_azure_environment(azure_config)

    def restore(self) -> None:
        """Restore original environment variables."""
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.original_env.clear()

    def get_proxy_env(
        self, proxy_port: int = 8080, config: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Get environment variables for subprocess.

        Args:
            proxy_port: Port where proxy is running.
            config: Additional configuration values.

        Returns:
            Dictionary of environment variables for subprocess.
        """
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = f"http://localhost:{proxy_port}"

        if config:
            env.update(config)

        return env

    def setup_azure_environment(self, config: Dict[str, str]) -> None:
        """Set up Azure-specific environment variables.

        Args:
            config: Azure configuration dictionary
        """
        self._setup_azure_environment(config)

    def _setup_azure_environment(self, config: Dict[str, str]) -> None:
        """Internal method to set up Azure environment variables.

        Args:
            config: Azure configuration dictionary
        """
        # Set Azure-specific environment variables
        azure_mappings = {
            "AZURE_OPENAI_ENDPOINT": "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_BASE_URL": "AZURE_OPENAI_BASE_URL",
            "AZURE_OPENAI_API_KEY": "AZURE_OPENAI_API_KEY",  # pragma: allowlist secret
            "AZURE_OPENAI_API_VERSION": "AZURE_OPENAI_API_VERSION",
        }

        for config_key, env_key in azure_mappings.items():
            if config_key in config and config[config_key]:
                os.environ[env_key] = config[config_key]

        # Set Azure-specific variables
        if config.get("AZURE_OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = config["AZURE_OPENAI_API_KEY"]

    def __enter__(self):
        """Context manager entry.

        Returns:
            Self for context manager use.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - restore environment.

        Args:
            exc_type: Exception type if any.
            exc_val: Exception value if any.
            exc_tb: Exception traceback if any.
        """
        self.restore()
