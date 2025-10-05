"""Proxy configuration parsing and validation."""

import os
from pathlib import Path
from typing import Dict, Optional


class ProxyConfig:
    """Manages proxy configuration from .env files."""

    def __init__(self, config_path: Optional[Path] = None, allow_env_fallback: bool = True):
        """Initialize proxy configuration.

        Args:
            config_path: Path to .env configuration file.
            allow_env_fallback: Whether to fall back to environment variables if config file is missing.
        """
        self.config_path = config_path
        self.allow_env_fallback = allow_env_fallback
        self.config: Dict[str, str] = {}

        # Try to load from file first
        if config_path and config_path.exists():
            self._load_config()
        elif allow_env_fallback:
            # Fall back to environment variables if file not found or not provided
            self._load_from_environment()

    def _load_config(self) -> None:
        """Load configuration from .env file."""
        if not self.config_path or not self.config_path.exists():
            return

        with open(self.config_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    self.config[key] = value

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Common environment variables for proxy configuration
        env_keys = [
            "OPENAI_API_KEY",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_VERSION",
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "ANTHROPIC_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_API_VERSION",
        ]

        for key in env_keys:
            value = os.environ.get(key)
            if value:
                self.config[key] = value

    def validate(self) -> bool:
        """Validate required configuration values.

        Returns:
            True if configuration is valid, False otherwise.
        """
        # For proxy configuration, we need either:
        # 1. OPENAI_API_KEY (for OpenAI)
        # 2. AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT (for Azure OpenAI)

        # Check for OpenAI configuration
        if self.config.get("OPENAI_API_KEY"):
            return True

        # Check for Azure OpenAI configuration
        if self.config.get("AZURE_OPENAI_API_KEY") and self.config.get("AZURE_OPENAI_ENDPOINT"):
            return True

        # Neither configuration present
        return False

    def get(self, key: str, default: str = "") -> str:
        """Get configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        return self.config.get(key, default)

    def to_env_dict(self) -> Dict[str, str]:
        """Convert configuration to environment variables dictionary.

        Returns:
            Dictionary of environment variables.
        """
        return self.config.copy()

    def save_to(self, target_path: Path) -> None:
        """Save configuration to a new .env file.

        Args:
            target_path: Path where to save the configuration.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w") as f:
            for key, value in self.config.items():
                f.write(f"{key}={value}\n")

    def get_config_source(self) -> str:
        """Get description of where configuration was loaded from.

        Returns:
            Human-readable description of config source.
        """
        if self.config_path and self.config_path.exists():
            return f"file: {self.config_path}"
        elif self.allow_env_fallback and self.config:
            return "environment variables"
        elif self.config_path:
            return f"file not found: {self.config_path}"
        else:
            return "no configuration"
