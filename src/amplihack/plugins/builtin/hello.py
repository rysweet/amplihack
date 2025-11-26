"""HelloPlugin - Example plugin demonstrating the plugin system.

This is a simple example plugin that demonstrates:
- Inheriting from PluginBase
- Using @register_plugin decorator
- Implementing the execute() method
- Handling arguments

Philosophy:
- Simple, clear example for documentation
- Demonstrates best practices
- Fully functional (no stubs)
"""

from typing import Any

from ..base import PluginBase
from ..decorator import register_plugin


@register_plugin(name="hello", description="Simple greeting plugin example")
class HelloPlugin(PluginBase):
    """Example plugin that generates greetings.

    This plugin demonstrates the basic structure of a plugin:
    - Inherits from PluginBase
    - Implements execute() method
    - Uses decorator for auto-registration

    Example:
        >>> plugin = HelloPlugin()
        >>> result = plugin.execute({"name": "World"})
        >>> print(result)
        "Hello, World!"
    """

    @property
    def name(self) -> str:
        """Return the plugin name from metadata."""
        return self._plugin_metadata.get("name", "hello")

    def execute(self, args: dict[str, Any]) -> str:
        """Generate a greeting message.

        Args:
            args: Dictionary with optional 'name' key

        Returns:
            str: Greeting message

        Example:
            >>> plugin.execute({"name": "Alice"})
            "Hello, Alice!"
            >>> plugin.execute({})
            "Hello, Friend!"
        """
        name = args.get("name", "Friend")
        message = f"Hello, {name}!"
        print(message)
        return message


__all__ = ["HelloPlugin"]
