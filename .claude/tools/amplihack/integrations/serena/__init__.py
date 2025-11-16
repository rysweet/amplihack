"""Serena MCP integration module.

This module provides detection, configuration, and CLI management
for integrating the Serena MCP server with Claude Desktop.

Example:
    >>> from .claude.tools.amplihack.integrations.serena import SerenaDetector
    >>> detector = SerenaDetector()
    >>> result = detector.detect_all()
    >>> print(result.get_status_summary())

Public API:
    SerenaDetector: Detects prerequisites and configuration paths
    SerenaDetectionResult: Results from prerequisite detection
    SerenaConfigurator: Manages MCP configuration
    SerenaConfig: Serena MCP server configuration
    SerenaCLI: Command-line interface
    SerenaIntegrationError: Base exception class
    UvNotFoundError: Raised when uv is not installed
    SerenaNotFoundError: Raised when Serena is not accessible
    ConfigurationError: Raised when configuration operations fail
    PlatformNotSupportedError: Raised for unsupported platforms
"""

from .cli import SerenaCLI
from .configurator import SerenaConfig, SerenaConfigurator
from .detector import SerenaDetectionResult, SerenaDetector
from .errors import (
    ConfigurationError,
    PlatformNotSupportedError,
    SerenaIntegrationError,
    SerenaNotFoundError,
    UvNotFoundError,
)

__all__ = [
    # Detector
    "SerenaDetector",
    "SerenaDetectionResult",
    # Configurator
    "SerenaConfigurator",
    "SerenaConfig",
    # CLI
    "SerenaCLI",
    # Errors
    "SerenaIntegrationError",
    "UvNotFoundError",
    "SerenaNotFoundError",
    "ConfigurationError",
    "PlatformNotSupportedError",
]
