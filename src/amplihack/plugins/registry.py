"""Plugin registry with thread-safe singleton pattern.

This module provides centralized plugin registration and retrieval:
- PluginRegistry: Thread-safe singleton for managing plugin lifecycle

Philosophy:
- Thread-safe singleton with double-checked locking
- Standard library only (threading for locks)
- Clear registration/retrieval API

Public API (the "studs"):
    PluginRegistry: Singleton registry for all plugins
"""

import threading
from typing import Optional

from .base import PluginBase, PluginValidationError


class PluginRegistry:
    """Thread-safe singleton registry for plugins.

    Manages plugin registration, retrieval, and lifecycle. Uses double-checked
    locking pattern for thread-safe singleton initialization.

    Example:
        >>> registry = PluginRegistry()
        >>> registry.register("my_plugin", MyPluginClass)
        >>> plugin_class = registry.get("my_plugin")
        >>> plugin_instance = plugin_class()
    """

    _instance: Optional["PluginRegistry"] = None
    _lock = threading.Lock()

    # Instance attributes (initialized in __new__)
    _plugins: dict[str, type[PluginBase]]
    _registry_lock: threading.Lock

    def __new__(cls) -> "PluginRegistry":
        """Create or return the singleton instance (thread-safe).

        Uses double-checked locking pattern:
        1. Check if instance exists (fast path, no lock)
        2. Acquire lock if needed
        3. Check again inside lock (thread safety)
        4. Create instance if still needed

        Returns:
            PluginRegistry: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check inside lock for thread safety
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._plugins = {}
                    cls._instance._registry_lock = threading.Lock()
        return cls._instance

    def register(self, name: str, plugin_class: type[PluginBase]) -> None:
        """Register a plugin class with the registry.

        Args:
            name: Unique name for the plugin
            plugin_class: Plugin class (must inherit from PluginBase)

        Raises:
            ValueError: If plugin name is already registered
            PluginValidationError: If plugin_class doesn't inherit from PluginBase
        """
        # Validate plugin inherits from PluginBase
        if not issubclass(plugin_class, PluginBase):
            raise PluginValidationError(
                f"Plugin class {plugin_class.__name__} must inherit from PluginBase"
            )

        with self._registry_lock:
            if name in self._plugins:
                raise ValueError(
                    f"Plugin '{name}' is already registered. "
                    f"Existing: {self._plugins[name].__name__}, "
                    f"New: {plugin_class.__name__}"
                )
            self._plugins[name] = plugin_class

    def get(self, name: str) -> type[PluginBase] | None:
        """Get a registered plugin class by name.

        Args:
            name: Plugin name to retrieve

        Returns:
            Optional[Type[PluginBase]]: Plugin class if found, None otherwise
        """
        with self._registry_lock:
            return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        """List all registered plugin names.

        Returns:
            List[str]: List of registered plugin names
        """
        with self._registry_lock:
            return list(self._plugins.keys())

    def clear(self) -> None:
        """Clear all registered plugins.

        Used primarily for testing to ensure clean state between tests.
        """
        with self._registry_lock:
            self._plugins.clear()


__all__ = ["PluginRegistry"]
