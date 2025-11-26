"""Plugin loading with validation and caching.

This module provides plugin loading functionality:
- Load plugins by name from registry
- Optional instance caching
- Validation of PluginBase inheritance
- Graceful error handling

Philosophy:
- Fail fast with clear error messages
- Optional caching for performance
- Standard library only

Public API (the "studs"):
    load_plugin: Load a plugin instance by name
    load_all_plugins: Load all registered plugins
    PluginNotFoundError: Exception for missing plugins
    PluginLoadError: Exception for loading failures
"""

from typing import Any

from .base import PluginBase, PluginLoadError, PluginNotFoundError
from .registry import PluginRegistry

# Module-level cache for plugin instances
_plugin_cache: dict[str, PluginBase] = {}


def load_plugin(
    name: str,
    init_args: dict[str, Any] | None = None,
    use_cache: bool = True,
) -> PluginBase:
    """Load a plugin instance by name.

    Retrieves plugin class from registry, validates it, and returns an instance.
    By default, instances are cached for performance.

    Args:
        name: Plugin name to load
        init_args: Optional initialization arguments to pass to plugin __init__
        use_cache: If True, cache and reuse instances (default: True)

    Returns:
        PluginBase: Plugin instance ready for execution

    Raises:
        PluginNotFoundError: If plugin name is not registered
        PluginLoadError: If plugin fails to initialize
        TypeError: If plugin doesn't inherit from PluginBase

    Example:
        >>> plugin = load_plugin("hello", init_args={"greeting": "Hi"})
        >>> result = plugin.execute({"name": "World"})
    """
    # Check cache first if enabled
    if use_cache and name in _plugin_cache:
        return _plugin_cache[name]

    # Get plugin class from registry
    registry = PluginRegistry()
    plugin_class = registry.get(name)

    if plugin_class is None:
        raise PluginNotFoundError(
            f"Plugin '{name}' not found in registry. "
            f"Available plugins: {', '.join(registry.list_plugins())}"
        )

    # Validate plugin class inherits from PluginBase
    if not issubclass(plugin_class, PluginBase):
        raise TypeError(
            f"Plugin '{name}' (class: {plugin_class.__name__}) must inherit from PluginBase"
        )

    # Initialize plugin instance
    try:
        if init_args:
            instance = plugin_class(**init_args)
        else:
            instance = plugin_class()
    except TypeError as e:
        # TypeError for abstract classes should bubble up directly
        # This includes "Can't instantiate abstract class" errors
        if "abstract" in str(e).lower():
            raise
        # Other TypeErrors get wrapped
        raise PluginLoadError(
            f"Failed to initialize plugin '{name}' (class: {plugin_class.__name__}). "
            f"Error: {type(e).__name__}: {e}"
        )
    except Exception as e:
        raise PluginLoadError(
            f"Failed to initialize plugin '{name}' (class: {plugin_class.__name__}). "
            f"Error: {type(e).__name__}: {e}"
        )

    # Validate instance has execute method
    if not hasattr(instance, "execute") or not callable(instance.execute):
        raise PluginLoadError(f"Plugin '{name}' instance does not have a callable execute() method")

    # Cache if enabled
    if use_cache:
        _plugin_cache[name] = instance

    return instance


def load_all_plugins(use_cache: bool = True) -> dict[str, PluginBase]:
    """Load all registered plugins.

    Retrieves all plugins from registry and loads each one.
    Continues on individual plugin failures (resilient batch processing).

    Args:
        use_cache: If True, cache instances (default: True)

    Returns:
        Dict[str, PluginBase]: Dictionary mapping plugin names to instances

    Example:
        >>> all_plugins = load_all_plugins()
        >>> for name, plugin in all_plugins.items():
        ...     print(f"{name}: {plugin.execute({})}")
    """
    registry = PluginRegistry()
    all_plugin_names = registry.list_plugins()

    loaded_plugins = {}

    for plugin_name in all_plugin_names:
        try:
            plugin = load_plugin(plugin_name, use_cache=use_cache)
            loaded_plugins[plugin_name] = plugin
        except Exception:
            # Continue loading other plugins (resilient batch processing)
            # In production, might log this error
            continue

    return loaded_plugins


__all__ = [
    "load_plugin",
    "load_all_plugins",
    "PluginNotFoundError",
    "PluginLoadError",
]
