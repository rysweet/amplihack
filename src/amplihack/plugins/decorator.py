"""Plugin registration decorator.

This module provides the @register_plugin decorator for automatic plugin registration.

Philosophy:
- Simple decorator pattern
- Validates PluginBase inheritance
- Stores metadata for introspection
- Standard library only

Public API (the "studs"):
    register_plugin: Decorator for automatic plugin registration
"""

from collections.abc import Callable

from .base import PluginBase
from .registry import PluginRegistry


def register_plugin(
    name: str | None = None, description: str | None = None
) -> Callable[[type[PluginBase]], type[PluginBase]]:
    """Decorator to automatically register a plugin class.

    This decorator validates the plugin class and registers it with the
    PluginRegistry. It also stores metadata on the class for introspection.

    Args:
        name: Optional custom name for the plugin (defaults to class name)
        description: Optional description of the plugin

    Returns:
        Callable: Decorator function that registers the plugin

    Raises:
        TypeError: If decorated class doesn't inherit from PluginBase

    Example:
        >>> @register_plugin(name="my_plugin", description="Does cool stuff")
        ... class MyPlugin(PluginBase):
        ...     def execute(self, args: Dict[str, Any]) -> Any:
        ...         return "result"
    """

    def decorator(cls: type[PluginBase]) -> type[PluginBase]:
        """Inner decorator function that performs registration.

        Args:
            cls: Plugin class to register

        Returns:
            Type[PluginBase]: The same class (unmodified)

        Raises:
            TypeError: If class doesn't inherit from PluginBase
        """
        # Validate plugin inherits from PluginBase
        if not issubclass(cls, PluginBase):
            raise TypeError(
                f"Class {cls.__name__} must inherit from PluginBase to be registered as a plugin"
            )

        # Determine plugin name
        plugin_name = name if name is not None else cls.__name__

        # Store metadata on the class
        cls._plugin_metadata = {
            "name": plugin_name,
            "description": description or "",
            "class_name": cls.__name__,
        }

        # Register with the singleton registry
        registry = PluginRegistry()
        registry.register(plugin_name, cls)

        return cls

    return decorator


__all__ = ["register_plugin"]
