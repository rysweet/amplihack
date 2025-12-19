"""Profile configuration management.

This module provides ProfileConfig for managing profile configuration persistence
including current profile selection and environment variable support.
"""

import os
from pathlib import Path

import yaml


class ConfigManager:
    """Manage profile configuration persistence.

    Handles:
    - Current profile selection
    - Config file persistence (~/.amplihack/config.yaml)
    - Environment variable support (AMPLIHACK_PROFILE)

    Priority for current profile:
    1. AMPLIHACK_PROFILE environment variable
    2. Saved config file
    3. Default: all

    Example:
        >>> config = ConfigManager()
        >>> uri = config.get_current_profile()
        >>> config.set_current_profile("amplihack://profiles/coding")
    """

    def __init__(self, config_path: Path | None = None):
        """Initialize config manager.

        Args:
            config_path: Path to config file (default: ~/.amplihack/config.yaml)
        """
        if config_path is None:
            config_path = Path.home() / ".amplihack" / "config.yaml"

        self.config_path = config_path

        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def get_current_profile(self) -> str:
        """Get currently active profile URI.

        Priority:
        1. AMPLIHACK_PROFILE environment variable
        2. Saved config file
        3. Default: all

        Returns:
            Profile URI

        Example:
            >>> config = ConfigManager()
            >>> uri = config.get_current_profile()
            >>> print(uri)
            all
        """
        # Check environment variable first (highest priority)
        env_profile = os.environ.get("AMPLIHACK_PROFILE")
        if env_profile:
            return env_profile

        # Check config file
        if self.config_path.exists():
            config = self._load_config()
            return config.get("current_profile", "all")

        # Default profile
        return "all"

    def set_current_profile(self, uri: str):
        """Set current profile URI.

        Saves profile URI to config file. This does NOT override the
        AMPLIHACK_PROFILE environment variable if set.

        Args:
            uri: Profile URI to save

        Example:
            >>> config = ConfigManager()
            >>> config.set_current_profile("amplihack://profiles/coding")
        """
        config = self._load_config() if self.config_path.exists() else {}
        config["current_profile"] = uri
        self._save_config(config)

    def _load_config(self) -> dict:
        """Load config from file.

        Returns:
            Config dictionary (empty dict if file doesn't exist or invalid)
        """
        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config if isinstance(config, dict) else {}
        except (FileNotFoundError, yaml.YAMLError, PermissionError):
            # Return empty dict on any error (file not found, invalid YAML, etc.)
            return {}

    def _save_config(self, config: dict):
        """Save config to file.

        Args:
            config: Config dictionary to save
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

    def is_env_override_active(self) -> bool:
        """Check if AMPLIHACK_PROFILE environment variable is set.

        Returns:
            True if environment variable is set, False otherwise

        Example:
            >>> config = ConfigManager()
            >>> if config.is_env_override_active():
            ...     print("Profile is set via environment variable")
        """
        return os.environ.get("AMPLIHACK_PROFILE") is not None
