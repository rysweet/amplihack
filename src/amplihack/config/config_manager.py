"""
ConfigManager - Thread-safe configuration management with YAML and environment variable support.

This module provides a robust configuration manager that:
- Loads configuration from YAML files
- Supports environment variable overrides (AMPLIHACK_* prefix)
- Provides dot-notation access to nested keys
- Thread-safe operations using RLock
- Validation of required configuration keys

Philosophy:
- Zero-BS: Every function works, no stubs or TODOs
- Ruthless simplicity: Direct implementation without over-engineering
- Thread safety: RLock protects all config operations
- Clear error messages: Help users understand what went wrong

Public API:
    ConfigManager: Main configuration management class
    ConfigError: Base exception for configuration errors
    ConfigFileError: File-related errors (missing, permission, malformed)
    ConfigValidationError: Validation failures
    ConfigKeyError: Key not found errors
"""

import os
import threading
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required for ConfigManager. Install with: pip install pyyaml")


class ConfigError(Exception):
    """Base exception for configuration errors"""


class ConfigFileError(ConfigError):
    """Exception raised for file-related errors"""


class ConfigValidationError(ConfigError):
    """Exception raised for validation failures"""


class ConfigKeyError(ConfigError):
    """Exception raised when a configuration key is not found"""


class ConfigManager:
    """
    Thread-safe configuration manager with YAML and environment variable support.

    Features:
    - Load configuration from YAML files
    - Override with environment variables (AMPLIHACK_* prefix)
    - Dot-notation for nested keys (e.g., "database.host")
    - Thread-safe operations
    - Validation of required keys

    Example:
        >>> config = ConfigManager(config_file="config.yaml")
        >>> host = config.get("database.host")
        >>> config.set("database.port", 5432)
        >>> config.validate(required_keys=["database.host", "database.port"])
    """

    def __init__(self, config_file: Path | None = None):
        """
        Initialize ConfigManager.

        Args:
            config_file: Path to YAML configuration file (optional)

        Raises:
            ConfigFileError: If config_file is provided but cannot be loaded
        """
        self._config: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._config_file = Path(config_file) if config_file else None

        # Load configuration
        if self._config_file:
            self._load_yaml_file(self._config_file)

        # Apply environment variable overrides
        self._apply_env_overrides()

    def get(self, key: str, default: Any = ...) -> Any:
        """
        Get configuration value by key using dot notation.

        Args:
            key: Configuration key (supports dot notation for nesting)
            default: Default value if key doesn't exist (optional).
                    Uses Ellipsis (...) sentinel to distinguish "no default" from None.

        Returns:
            Configuration value or default

        Raises:
            ConfigKeyError: If key doesn't exist and no default provided

        Example:
            >>> config.get("database.host")
            'localhost'
            >>> config.get("missing.key", default="fallback")
            'fallback'
        """
        if not key:
            raise ConfigKeyError("Key cannot be empty")

        with self._lock:
            try:
                return self._get_nested_value(key)
            except ConfigKeyError:
                if default is ...:
                    raise
                return default

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key using dot notation.

        Creates intermediate keys if they don't exist.

        Args:
            key: Configuration key (supports dot notation for nesting)
            value: Value to set

        Raises:
            ConfigKeyError: If key is invalid

        Example:
            >>> config.set("database.host", "localhost")
            >>> config.set("new.nested.key", "value")
        """
        if not key:
            raise ConfigKeyError("Key cannot be empty")

        with self._lock:
            self._set_nested_value(key, value)

    def reload(self) -> None:
        """
        Reload configuration from file.

        Reloads YAML file and reapplies environment variable overrides.
        Runtime values set with set() are cleared.

        Raises:
            ConfigFileError: If config file cannot be reloaded
        """
        with self._lock:
            self._config = {}

            if self._config_file:
                self._load_yaml_file(self._config_file)

            # Reapply environment variable overrides
            self._apply_env_overrides()

    def validate(self, required_keys: list[str] | None = None) -> None:
        """
        Validate that all required keys are present.

        Args:
            required_keys: List of required configuration keys

        Raises:
            ConfigValidationError: If any required keys are missing

        Example:
            >>> config.validate(required_keys=["database.host", "database.port"])
        """
        if not required_keys:
            return

        with self._lock:
            missing_keys = [key for key in required_keys if not self._key_exists(key)]

            if missing_keys:
                raise ConfigValidationError(
                    f"Missing required configuration keys: {', '.join(missing_keys)}"
                )

    def _key_exists(self, key: str) -> bool:
        """Check if a key exists in the configuration."""
        try:
            self._get_nested_value(key)
            return True
        except ConfigKeyError:
            return False

    def _load_yaml_file(self, filepath: Path) -> None:
        """
        Load YAML configuration file.

        Args:
            filepath: Path to YAML file

        Raises:
            ConfigFileError: If file cannot be loaded
        """
        if not filepath.exists():
            raise ConfigFileError(f"Configuration file not found: {filepath}")

        try:
            content = filepath.read_text()
            loaded = yaml.safe_load(content) if content.strip() else None
            self._config = loaded if loaded else {}
        except PermissionError:
            raise ConfigFileError(f"Permission denied reading config file: {filepath}")
        except yaml.YAMLError as e:
            raise ConfigFileError(f"Invalid YAML syntax in config file: {filepath} - {e}")
        except Exception as e:
            raise ConfigFileError(f"Error loading config file: {filepath} - {e}")

    def _apply_env_overrides(self) -> None:
        """
        Apply environment variable overrides.

        Looks for AMPLIHACK_* environment variables and applies them to config.
        Double underscores (__) are converted to dots for nesting.
        Case-insensitive key matching.
        """
        prefix = "AMPLIHACK_"

        for env_key, env_value in os.environ.items():
            if not env_key.upper().startswith(prefix.upper()):
                continue

            config_key = env_key[len(prefix) :].replace("__", ".").lower()
            converted_value = self._convert_env_value(env_value)
            self._set_nested_value(config_key, converted_value)

    def _convert_env_value(self, value: str) -> Any:
        """
        Convert environment variable string to appropriate type.

        Args:
            value: String value from environment variable

        Returns:
            Converted value (int, float, bool, or string)
        """
        if value == "":
            return ""

        value_lower = value.lower()
        if value_lower in ("true", "yes", "1", "on"):
            return True
        if value_lower in ("false", "no", "0", "off"):
            return False

        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def _get_nested_value(self, key: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            key: Dot-separated key path

        Returns:
            Value at key path

        Raises:
            ConfigKeyError: If key path doesn't exist
        """
        keys = key.split(".")
        current = self._config

        for i, k in enumerate(keys):
            if not isinstance(current, dict):
                path_so_far = ".".join(keys[:i])
                raise ConfigKeyError(
                    f"Cannot access '{key}': intermediate key '{path_so_far}' "
                    f"is {type(current).__name__}, not a dict"
                )

            if k not in current:
                raise ConfigKeyError(f"Configuration key not found: {key}")

            current = current[k]

        return current

    def _set_nested_value(self, key: str, value: Any) -> None:
        """
        Set value in nested dictionary using dot notation.

        Creates intermediate dictionaries if they don't exist.

        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split(".")
        current = self._config

        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value


__all__ = [
    "ConfigManager",
    "ConfigError",
    "ConfigFileError",
    "ConfigValidationError",
    "ConfigKeyError",
]
