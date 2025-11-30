"""Configuration management for REST API client.

This module handles configuration loading from multiple sources (files, environment)
with proper precedence and validation.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class APIConfig:
    """API client configuration.

    Immutable configuration object with sensible defaults.

    Attributes:
        base_url: Base URL for all requests
        timeout: Default timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Initial retry delay in seconds
        max_retry_delay: Maximum retry delay in seconds
        rate_limit_calls: Max calls allowed in rate limit period
        rate_limit_period: Rate limit period in seconds
        verify_ssl: Whether to verify SSL certificates
        headers: Default headers for all requests
    """

    base_url: str = ""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    rate_limit_calls: int = 100
    rate_limit_period: int = 60
    verify_ssl: bool = True
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        if self.rate_limit_calls <= 0:
            raise ValueError("Rate limit calls must be positive")
        if self.base_url and not self._is_valid_url(self.base_url):
            raise ValueError(f"Invalid base URL: {self.base_url}")

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False


def load_config(config_path: str | None = None) -> APIConfig:
    """Load configuration from file and/or environment variables.

    Precedence order (highest to lowest):
    1. Environment variables (API_* prefix)
    2. Config file (if provided)
    3. Default values

    Args:
        config_path: Path to config file (JSON or YAML)

    Returns:
        APIConfig instance with merged configuration

    Raises:
        FileNotFoundError: If config_path is provided but doesn't exist
        ValueError: If config file is malformed
    """
    config_dict = {}

    # Load from file if provided
    if config_path:
        config_dict = _load_from_file(config_path)

    # Override with environment variables
    env_config = _load_from_env()
    config_dict = merge_configs(config_dict, env_config)

    # Create config object
    return _dict_to_config(config_dict)


def _load_from_file(path: str) -> dict[str, Any]:
    """Load configuration from file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        if file_path.suffix == ".json":
            with open(file_path) as f:
                return json.load(f)
        elif file_path.suffix in (".yaml", ".yml"):
            # YAML support requires PyYAML - not included to keep dependencies minimal
            try:
                import yaml

                with open(file_path) as f:
                    return yaml.safe_load(f)
            except ImportError:
                raise ValueError(
                    "YAML config files require PyYAML. Use JSON format or install PyYAML."
                )
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")
    except Exception as e:
        raise ValueError(f"Error loading config from {path}: {e}")


def _load_from_env() -> dict[str, Any]:
    """Load configuration from environment variables."""
    config = {}

    # Map environment variables to config keys
    env_map = {
        "API_BASE_URL": "base_url",
        "API_TIMEOUT": "timeout",
        "API_MAX_RETRIES": "max_retries",
        "API_RETRY_DELAY": "retry_delay",
        "API_MAX_RETRY_DELAY": "max_retry_delay",
        "API_RATE_LIMIT_CALLS": "rate_limit_calls",
        "API_RATE_LIMIT_PERIOD": "rate_limit_period",
        "API_VERIFY_SSL": "verify_ssl",
    }

    for env_key, config_key in env_map.items():
        value = os.getenv(env_key)
        if value is not None:
            # Convert to appropriate type
            if config_key in ("timeout", "max_retries", "rate_limit_calls", "rate_limit_period"):
                config[config_key] = int(value)
            elif config_key in ("retry_delay", "max_retry_delay"):
                config[config_key] = float(value)
            elif config_key == "verify_ssl":
                config[config_key] = value.lower() in ("true", "1", "yes")
            else:
                config[config_key] = value

    return config


def _dict_to_config(config_dict: dict[str, Any]) -> APIConfig:
    """Convert dictionary to APIConfig instance."""
    # Filter to only known fields
    known_fields = {
        "base_url",
        "timeout",
        "max_retries",
        "retry_delay",
        "max_retry_delay",
        "rate_limit_calls",
        "rate_limit_period",
        "verify_ssl",
        "headers",
    }

    filtered = {k: v for k, v in config_dict.items() if k in known_fields}
    return APIConfig(**filtered)


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Type validation
    type_checks = {
        "timeout": (int, "must be an integer"),
        "max_retries": (int, "must be an integer"),
        "retry_delay": ((int, float), "must be a number"),
        "max_retry_delay": ((int, float), "must be a number"),
        "rate_limit_calls": (int, "must be an integer"),
        "rate_limit_period": (int, "must be an integer"),
        "verify_ssl": (bool, "must be a boolean"),
        "base_url": (str, "must be a string"),
        "headers": (dict, "must be a dictionary"),
    }

    for field, (expected_type, error_msg) in type_checks.items():
        if field in config:
            if not isinstance(config[field], expected_type):
                errors.append(f"{field} {error_msg}")

    # Range validation
    if "timeout" in config and isinstance(config["timeout"], int):
        if config["timeout"] <= 0:
            errors.append("timeout must be positive")

    if "max_retries" in config and isinstance(config["max_retries"], int):
        if config["max_retries"] < 0:
            errors.append("max_retries must be non-negative")
        if config["max_retries"] > 100:
            errors.append("max_retries seems too high (>100)")

    if "rate_limit_calls" in config and isinstance(config["rate_limit_calls"], int):
        if config["rate_limit_calls"] <= 0:
            errors.append("rate_limit_calls must be positive")

    return errors


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two configuration dictionaries.

    The override values take precedence. For nested dictionaries (like headers),
    performs a deep merge.

    Args:
        base: Base configuration
        override: Configuration to override/merge

    Returns:
        Merged configuration dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Deep merge for dictionaries
            result[key] = merge_configs(result[key], value)
        else:
            # Direct override
            result[key] = value

    return result


__all__ = ["APIConfig", "load_config", "validate_config", "merge_configs"]
