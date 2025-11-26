"""Base plugin system infrastructure.

This module provides the foundation for the plugin system:
- PluginBase: Abstract base class that all plugins must inherit from
- Custom exceptions for plugin system errors

Philosophy:
- Ruthless simplicity: Standard library only
- SOLID principles: Single responsibility, clear contracts
- Zero-BS: All functionality is complete and working

Public API (the "studs"):
    PluginBase: Abstract base class for all plugins
    PluginError: Base exception for plugin errors
    PluginValidationError: Raised when plugin validation fails
    PluginNotFoundError: Raised when requested plugin doesn't exist
    PluginLoadError: Raised when plugin fails to load
"""

from abc import ABC, abstractmethod
from typing import Any

# ============================================================================
# EXCEPTIONS
# ============================================================================


class PluginError(Exception):
    """Base exception for all plugin-related errors."""


class PluginValidationError(PluginError):
    """Raised when plugin fails validation (e.g., doesn't inherit from PluginBase)."""


class PluginNotFoundError(PluginError):
    """Raised when requested plugin is not registered."""


class PluginLoadError(PluginError):
    """Raised when plugin fails to initialize or load."""


# ============================================================================
# PLUGIN BASE CLASS
# ============================================================================


class PluginBase(ABC):
    """Abstract base class for all plugins.

    All plugins must inherit from this class and implement the execute() method.
    This ensures a consistent interface across all plugins.

    Example:
        >>> class MyPlugin(PluginBase):
        ...     def execute(self, args: Dict[str, Any]) -> Any:
        ...         return f"Processed: {args}"
        ...
        >>> plugin = MyPlugin()
        >>> plugin.execute({"data": "test"})
        "Processed: {'data': 'test'}"
    """

    # Plugin metadata (set by @register_plugin decorator)
    _plugin_metadata: dict[str, str]

    @abstractmethod
    def execute(self, args: dict[str, Any]) -> Any:
        """Execute the plugin with given arguments.

        Args:
            args: Dictionary of arguments for plugin execution

        Returns:
            Any: Result of plugin execution (type depends on plugin implementation)

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """

    @property
    def name(self) -> str:
        """Get the plugin name (defaults to class name).

        Can be overridden by subclasses to provide custom names.

        Returns:
            str: Plugin name
        """
        return self.__class__.__name__


__all__ = [
    "PluginBase",
    "PluginError",
    "PluginValidationError",
    "PluginNotFoundError",
    "PluginLoadError",
]
