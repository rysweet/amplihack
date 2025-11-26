"""Plugin system for amplihack.

This module provides a complete plugin system with:
- Abstract base class for all plugins (PluginBase)
- Singleton registry for managing plugins (PluginRegistry)
- Decorator for automatic registration (@register_plugin)
- Discovery of plugin files with security validation
- Plugin loading with caching and validation
- Built-in example plugins

Philosophy:
- Ruthless simplicity: Standard library only
- SOLID principles: Clear separation of concerns
- Zero-BS: All functionality is complete and working
- Modular design: Self-contained, regeneratable components

Example:
    >>> from amplihack.plugins import PluginBase, register_plugin, load_plugin
    >>>
    >>> @register_plugin(name="my_plugin")
    >>> class MyPlugin(PluginBase):
    ...     def execute(self, args):
    ...         return f"Processed: {args}"
    >>>
    >>> plugin = load_plugin("my_plugin")
    >>> result = plugin.execute({"data": "test"})
    >>> print(result)
    "Processed: {'data': 'test'}"

Public API:
    PluginBase: Abstract base class for all plugins
    PluginRegistry: Singleton registry for managing plugins
    register_plugin: Decorator for automatic plugin registration
    discover_plugins: Find plugin files with security validation
    load_plugin: Load a plugin instance by name
    load_all_plugins: Load all registered plugins

    Exceptions:
        PluginError: Base exception for all plugin errors
        PluginValidationError: Raised when plugin validation fails
        PluginNotFoundError: Raised when plugin not found
        PluginLoadError: Raised when plugin fails to load
"""

# Base classes and exceptions
from .base import (
    PluginBase,
    PluginError,
    PluginLoadError,
    PluginNotFoundError,
    PluginValidationError,
)

# Decorator
from .decorator import register_plugin

# Discovery
from .discovery import discover_plugins

# Loader
from .loader import load_all_plugins, load_plugin

# Registry
from .registry import PluginRegistry

# Built-in plugins are not imported here to avoid auto-registration at package import.
# They register themselves when explicitly imported by users.
# Example: from amplihack.plugins.builtin import HelloPlugin


__all__ = [
    # Base
    "PluginBase",
    # Registry
    "PluginRegistry",
    # Decorator
    "register_plugin",
    # Discovery
    "discover_plugins",
    # Loader
    "load_plugin",
    "load_all_plugins",
    # Exceptions
    "PluginError",
    "PluginValidationError",
    "PluginNotFoundError",
    "PluginLoadError",
    # Built-in plugins are exported from their submodule
    # Access via: from amplihack.plugins.builtin import HelloPlugin
]
