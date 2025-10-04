"""Environment variable management for proxy integration."""

import os
import re
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
        # Validate config before setting up environment
        if config and not self._validate_azure_config_security(config):
            raise ValueError("Invalid Azure configuration - security validation failed")
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
                sanitized_value = self._sanitize_env_value(config[config_key])
                if sanitized_value:  # Only set if sanitization didn't remove everything
                    os.environ[env_key] = sanitized_value

        # Set performance and server configuration variables
        performance_mappings = {
            "REQUEST_TIMEOUT": "REQUEST_TIMEOUT",
            "MAX_RETRIES": "MAX_RETRIES",
            "LOG_LEVEL": "LOG_LEVEL",
            "HOST": "HOST",
            "PORT": "PORT",
            "MAX_TOKENS_LIMIT": "MAX_TOKENS_LIMIT",
            "MIN_TOKENS_LIMIT": "MIN_TOKENS_LIMIT",
        }

        for config_key, env_key in performance_mappings.items():
            if config_key in config and config[config_key]:
                # These values should be clean already from our config parser
                os.environ[env_key] = config[config_key]

        # Set Azure-specific variables with validation
        azure_api_key = config.get("AZURE_OPENAI_API_KEY")
        if azure_api_key and self._validate_api_key_format(azure_api_key):
            os.environ["OPENAI_API_KEY"] = azure_api_key

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

    def _validate_azure_config_security(self, config: Dict[str, str]) -> bool:
        """Validate Azure configuration for security issues.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is secure, False otherwise.
        """
        # Check for required fields - be lenient for backward compatibility
        has_api_key = config.get("AZURE_OPENAI_API_KEY")
        has_endpoint = config.get("AZURE_OPENAI_ENDPOINT") or config.get("AZURE_OPENAI_BASE_URL")

        if not (has_api_key and has_endpoint):
            return False

        # Validate API key format
        api_key = config.get("AZURE_OPENAI_API_KEY")
        if api_key and not self._validate_api_key_format(api_key):
            return False

        # Validate endpoint URL
        endpoint = config.get("AZURE_OPENAI_ENDPOINT") or config.get("AZURE_OPENAI_BASE_URL")
        if endpoint and not self._validate_endpoint_url(endpoint):
            return False

        return True

    def _validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format.

        Args:
            api_key: API key to validate

        Returns:
            True if format is valid, False otherwise.
        """
        if not api_key:
            return False

        # Allow test keys for development/testing
        if api_key.startswith(("test-", "sk-test-", "dummy-")):
            return len(api_key) >= 8

        # For production keys, require minimum length and format
        if len(api_key) < 20:
            return False

        # API keys should be alphanumeric with dashes/underscores
        pattern = r"^[a-zA-Z0-9\-_]{20,}$"
        return bool(re.match(pattern, api_key))

    def _validate_endpoint_url(self, url: str) -> bool:
        """Validate endpoint URL format.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid, False otherwise.
        """
        if not url:
            return False

        # Must be HTTPS
        if not url.startswith("https://"):
            return False

        # Basic URL format validation
        url_pattern = r"^https://[a-zA-Z0-9\-_.]+\.[a-zA-Z]{2,}(/.*)?$"
        return bool(re.match(url_pattern, url))

    def _sanitize_env_value(self, value: str) -> str:
        """Sanitize environment variable value.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized value.
        """
        if not value:
            return ""

        # Remove potentially dangerous characters
        dangerous_chars = ["<", ">", '"', "'", "&", "|", ";", "$", "`"]
        sanitized = value
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        return sanitized
