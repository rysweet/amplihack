"""Environment variable management for proxy integration."""

import os
from typing import Dict, Optional


class ProxyEnvironment:
    """Manages environment variables for Claude Code proxy."""

    def __init__(self):
        """Initialize environment manager."""
        self.original_env: Dict[str, Optional[str]] = {}

    def setup(self, proxy_port: int = 8080, api_key: Optional[str] = None) -> None:
        """Set up environment variables for proxy.

        Args:
            proxy_port: Port where proxy is running.
            api_key: Anthropic API key to use.
        """
        # Store original values
        self.original_env["ANTHROPIC_BASE_URL"] = os.environ.get("ANTHROPIC_BASE_URL")
        self.original_env["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY")

        # Set proxy environment variables
        os.environ["ANTHROPIC_BASE_URL"] = f"http://localhost:{proxy_port}"

        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

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
