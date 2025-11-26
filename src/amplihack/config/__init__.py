"""
Configuration management module for amplihack.

This module provides thread-safe configuration management with YAML file support
and environment variable overrides.

Public API:
    ConfigManager: Main configuration management class
    ConfigError: Base exception for configuration errors
    ConfigFileError: File-related errors
    ConfigValidationError: Validation failures
    ConfigKeyError: Key not found errors
"""

from .config_manager import (
    ConfigError,
    ConfigFileError,
    ConfigKeyError,
    ConfigManager,
    ConfigValidationError,
)

__all__ = [
    "ConfigManager",
    "ConfigError",
    "ConfigFileError",
    "ConfigValidationError",
    "ConfigKeyError",
]
