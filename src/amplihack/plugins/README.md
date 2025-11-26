# Plugin System

**Extensible CLI command system for amplihack using thread-safe plugin discovery and registration.**

## Overview

The amplihack plugin system allows ye to extend CLI functionality by creatin' custom plugins. Plugins be self-contained modules that register themselves automatically and integrate seamlessly with the CLI.

## Quick Start

### Creating a Plugin

Create a new Python file in the `plugins/` directory:

```python
# plugins/hello.py
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class HelloPlugin(PluginBase):
    """Simple greeting plugin."""

    name = "hello"
    description = "Print a friendly greeting"

    def execute(self, args):
        """Execute the hello command."""
        name = args.name if hasattr(args, 'name') and args.name else "World"
        print(f"Hello, {name}!")
        return 0
```

### Using the Plugin

```bash
# The plugin is automatically discovered and registered
amplihack hello
# Output: Hello, World!

amplihack hello --name Claude
# Output: Hello, Claude!
```

That's all ye need! The `@register_plugin` decorator handles registration automatically.

## Table of Contents

- [Architecture](#architecture)
- [Plugin Lifecycle](#plugin-lifecycle)
- [Creating Plugins](#creating-plugins)
- [Plugin API Reference](#plugin-api-reference)
- [Security Considerations](#security-considerations)
- [Testing Plugins](#testing-plugins)
- [Troubleshooting](#troubleshooting)

## Architecture

The plugin system consists of three core components:

1. **PluginBase**: Abstract base class that all plugins must inherit from
2. **PluginRegistry**: Thread-safe singleton that manages plugin discovery and registration
3. **@register_plugin**: Decorator that automatically registers plugins at import time

### Design Principles

- **Thread-safe**: Uses double-checked locking for singleton access
- **Security-first**: Path traversal prevention, file size limits, safe imports
- **Ruthlessly simple**: Standard library only, minimal abstractions
- **SOLID principles**: Clear separation of concerns, single responsibility

## Plugin Lifecycle

Plugins move through several stages from creation to execution:

```
1. Plugin File Created
   └─> File placed in plugins/ directory

2. Discovery
   └─> PluginRegistry.discover_plugins() scans directory

3. Import & Registration
   └─> @register_plugin decorator registers plugin class

4. Validation
   └─> PluginRegistry validates plugin implements required interface

5. Execution
   └─> CLI calls plugin.execute(args)
```

### Lifecycle Example

```python
from amplihack.plugins import PluginRegistry

# Discovery and loading (done automatically at CLI startup)
registry = PluginRegistry()
registry.discover_plugins("./plugins")

# Retrieve plugin
plugin = registry.get_plugin("hello")

# Execute plugin
import argparse
args = argparse.Namespace(name="Captain")
exit_code = plugin.execute(args)
# Output: Hello, Captain!
# Returns: 0
```

## Creating Plugins

### Minimal Plugin

Every plugin needs three things:

1. Inherit from `PluginBase`
2. Set `name` and `description` class attributes
3. Implement `execute(args)` method

```python
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class MinimalPlugin(PluginBase):
    """Minimal working plugin."""

    name = "minimal"
    description = "Does the minimum required"

    def execute(self, args):
        """Execute the plugin."""
        print("Minimal plugin executed")
        return 0  # Success exit code
```

### Plugin with Arguments

Plugins receive parsed arguments through the `args` parameter:

```python
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class GreetPlugin(PluginBase):
    """Greeting plugin with argument parsing."""

    name = "greet"
    description = "Greet someone with style"

    def execute(self, args):
        """Execute the greeting with custom style."""
        name = getattr(args, 'name', 'World')
        style = getattr(args, 'style', 'normal')

        if style == 'pirate':
            print(f"Ahoy, {name}! Ye scurvy dog!")
        elif style == 'formal':
            print(f"Good day, {name}. How do you do?")
        else:
            print(f"Hello, {name}!")

        return 0
```

Usage:

```bash
amplihack greet --name Claude --style pirate
# Output: Ahoy, Claude! Ye scurvy dog!
```

### Plugin with Error Handling

Robust plugins handle errors gracefully:

```python
from amplihack.plugins import PluginBase, register_plugin
from pathlib import Path

@register_plugin
class FileCountPlugin(PluginBase):
    """Count files in a directory."""

    name = "countfiles"
    description = "Count files in specified directory"

    def execute(self, args):
        """Execute file counting."""
        try:
            directory = getattr(args, 'directory', '.')
            path = Path(directory)

            if not path.exists():
                print(f"Error: Directory not found: {directory}")
                return 1

            if not path.is_dir():
                print(f"Error: Not a directory: {directory}")
                return 1

            count = len(list(path.glob('*')))
            print(f"Found {count} items in {directory}")
            return 0

        except PermissionError:
            print(f"Error: Permission denied accessing {directory}")
            return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1
```

### Plugin with Configuration

Plugins can read configuration from files or environment:

```python
from amplihack.plugins import PluginBase, register_plugin
import json
from pathlib import Path
import os

@register_plugin
class ConfigurablePlugin(PluginBase):
    """Plugin that reads configuration."""

    name = "configured"
    description = "Plugin with configuration support"

    def __init__(self):
        super().__init__()
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from file or environment."""
        # Try config file first
        config_path = Path.home() / ".amplihack" / "plugin_config.json"
        if config_path.exists():
            return json.loads(config_path.read_text())

        # Fall back to environment variables
        return {
            "api_key": os.environ.get("PLUGIN_API_KEY", ""),
            "timeout": int(os.environ.get("PLUGIN_TIMEOUT", "30"))
        }

    def execute(self, args):
        """Execute using configuration."""
        timeout = self.config.get("timeout", 30)
        print(f"Running with timeout: {timeout}s")
        # ... plugin logic ...
        return 0
```

## Plugin API Reference

### PluginBase

Abstract base class for all plugins.

**Required Attributes:**

- `name` (str): Unique plugin identifier, used in CLI commands
- `description` (str): Brief description shown in help text

**Required Methods:**

- `execute(args: argparse.Namespace) -> int`: Main execution method

**Return Values:**

- `0`: Success
- `1`: General error
- Other non-zero: Specific error codes

**Example:**

```python
from amplihack.plugins import PluginBase

class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My custom plugin"

    def execute(self, args):
        # Plugin logic here
        return 0
```

### PluginRegistry

Thread-safe singleton for managing plugins.

**Public Methods:**

#### `get_instance() -> PluginRegistry`

Get the singleton registry instance.

```python
from amplihack.plugins import PluginRegistry

registry = PluginRegistry.get_instance()
```

#### `register_plugin(plugin_class: Type[PluginBase]) -> None`

Register a plugin class. Usually called via decorator, but can be used directly.

```python
registry.register_plugin(MyPluginClass)
```

#### `get_plugin(name: str) -> Optional[PluginBase]`

Retrieve a registered plugin by name.

```python
plugin = registry.get_plugin("hello")
if plugin:
    plugin.execute(args)
```

#### `list_plugins() -> List[str]`

Get list of all registered plugin names.

```python
plugins = registry.list_plugins()
print(f"Available plugins: {', '.join(plugins)}")
# Output: Available plugins: hello, greet, countfiles
```

#### `discover_plugins(plugin_dir: str) -> None`

Discover and load plugins from a directory.

```python
registry.discover_plugins("./plugins")
```

**Security Features:**

- Path traversal prevention
- File size limits (default: 10MB)
- Safe import isolation
- Python file validation

### @register_plugin

Decorator that automatically registers plugins at import time.

**Usage:**

```python
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My plugin"

    def execute(self, args):
        return 0
```

**What it does:**

1. Validates plugin implements required interface
2. Registers plugin with PluginRegistry
3. Returns the original class (transparent decorator)

## Security Considerations

The plugin system includes several security features to prevent common vulnerabilities:

### Path Traversal Prevention

The registry validates all file paths to prevent directory traversal attacks:

```python
# SAFE - Normal plugin path
registry.discover_plugins("./plugins")

# BLOCKED - Path traversal attempt
registry.discover_plugins("./plugins/../../../etc")
# Raises: SecurityError("Path traversal detected")
```

### File Size Limits

Plugins are limited to 10MB by default to prevent resource exhaustion:

```python
# Files larger than 10MB are skipped with warning
# This prevents memory exhaustion attacks
```

### Safe Import Isolation

Plugins are imported in isolation to prevent cross-plugin interference:

```python
# Each plugin import is isolated
# Import failures don't affect other plugins
# Exceptions are caught and logged
```

### Validation

All plugins must pass validation before registration:

```python
# Required: name attribute
# Required: description attribute
# Required: execute() method
# Invalid plugins are rejected at registration time
```

### Best Practices

1. **Never trust user input**: Always validate and sanitize arguments
2. **Use absolute paths**: Avoid relative paths that could be manipulated
3. **Limit file operations**: Use context managers and close resources
4. **Handle exceptions**: Don't let errors crash the CLI
5. **Log security events**: Track registration and execution

## Testing Plugins

### Unit Testing

Test plugins in isolation:

```python
# test_hello_plugin.py
import unittest
import argparse
from plugins.hello import HelloPlugin

class TestHelloPlugin(unittest.TestCase):
    def setUp(self):
        """Create plugin instance for testing."""
        self.plugin = HelloPlugin()

    def test_name_attribute(self):
        """Test plugin has correct name."""
        self.assertEqual(self.plugin.name, "hello")

    def test_execute_no_args(self):
        """Test execution with no arguments."""
        args = argparse.Namespace()
        result = self.plugin.execute(args)
        self.assertEqual(result, 0)

    def test_execute_with_name(self):
        """Test execution with name argument."""
        args = argparse.Namespace(name="Claude")
        result = self.plugin.execute(args)
        self.assertEqual(result, 0)
```

### Integration Testing

Test plugin discovery and registration:

```python
# test_plugin_integration.py
import unittest
import tempfile
from pathlib import Path
from amplihack.plugins import PluginRegistry

class TestPluginIntegration(unittest.TestCase):
    def setUp(self):
        """Create temporary plugin directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = PluginRegistry.get_instance()

    def test_discover_plugins(self):
        """Test plugin discovery from directory."""
        # Create test plugin file
        plugin_file = Path(self.temp_dir) / "test_plugin.py"
        plugin_file.write_text('''
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class TestPlugin(PluginBase):
    name = "testplugin"
    description = "Test plugin"

    def execute(self, args):
        return 0
''')

        # Discover plugins
        self.registry.discover_plugins(self.temp_dir)

        # Verify plugin registered
        self.assertIn("testplugin", self.registry.list_plugins())
```

### End-to-End Testing

Test complete CLI integration:

```python
# test_plugin_e2e.py
import unittest
import subprocess

class TestPluginE2E(unittest.TestCase):
    def test_hello_command(self):
        """Test hello plugin via CLI."""
        result = subprocess.run(
            ["amplihack", "hello", "--name", "Test"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Hello, Test!", result.stdout)
```

## Troubleshooting

### Plugin Not Found

**Problem**: CLI doesn't recognize your plugin command.

**Solution**:

1. Verify plugin file is in `plugins/` directory
2. Check plugin has `@register_plugin` decorator
3. Ensure plugin inherits from `PluginBase`
4. Verify `name` attribute is set correctly

```python
# Common mistake - missing decorator
class MyPlugin(PluginBase):  # ❌ Not registered
    name = "myplugin"
    # ...

# Correct
@register_plugin  # ✓ Will be discovered
class MyPlugin(PluginBase):
    name = "myplugin"
    # ...
```

### Import Errors

**Problem**: Plugin import fails with `ModuleNotFoundError`.

**Solution**:

1. Check all imports are available in the environment
2. Verify import paths are correct
3. Use absolute imports, not relative
4. Check for circular dependencies

```python
# Problematic
from .utils import helper  # ❌ Relative import may fail

# Better
from amplihack.plugins.utils import helper  # ✓ Absolute import
```

### Plugin Name Conflicts

**Problem**: Two plugins have the same name.

**Solution**:

1. Rename one of the plugins
2. Use unique, descriptive names
3. Check existing plugins with `registry.list_plugins()`

```python
# Check for conflicts before registering
registry = PluginRegistry.get_instance()
if "myplugin" in registry.list_plugins():
    print("Warning: Plugin name already taken")
```

### Execute Method Not Called

**Problem**: Plugin registers but execute method doesn't run.

**Solution**:

1. Verify method signature: `execute(self, args)`
2. Check return value is an integer
3. Ensure no exceptions are raised during execution

```python
# Wrong signature
def execute(self):  # ❌ Missing args parameter
    return 0

# Correct signature
def execute(self, args):  # ✓ Includes args
    return 0
```

### Security Errors

**Problem**: `SecurityError: Path traversal detected`

**Solution**:

1. Use absolute paths or paths relative to known safe directory
2. Don't allow user input in plugin directory paths
3. Validate all file paths before use

```python
# Unsafe - user input directly used
plugin_dir = input("Plugin directory: ")  # ❌ User could enter ../../../
registry.discover_plugins(plugin_dir)

# Safe - validate path first
plugin_dir = Path(input("Plugin directory: ")).resolve()
if plugin_dir.is_relative_to(safe_base_dir):  # ✓ Validated
    registry.discover_plugins(str(plugin_dir))
```

### Testing Issues

**Problem**: Tests pass individually but fail together.

**Solution**:

1. Registry is a singleton - reset between tests
2. Use separate test directories for isolation
3. Mock registry in unit tests

```python
# Reset registry between tests
def tearDown(self):
    """Clean up after test."""
    registry = PluginRegistry.get_instance()
    # Clear registered plugins (implementation-specific)
    registry._plugins.clear()
```

## Advanced Topics

### Custom Plugin Discovery

For advanced use cases, you can implement custom discovery logic:

```python
from amplihack.plugins import PluginRegistry
from pathlib import Path

def discover_plugins_recursive(base_dir: str):
    """Discover plugins in nested directories."""
    registry = PluginRegistry.get_instance()

    for plugin_dir in Path(base_dir).rglob("plugins"):
        if plugin_dir.is_dir():
            registry.discover_plugins(str(plugin_dir))
```

### Plugin Metadata

Add rich metadata to plugins for better CLI integration:

```python
@register_plugin
class MetadataPlugin(PluginBase):
    """Plugin with rich metadata."""

    name = "metadata"
    description = "Plugin with metadata example"
    version = "1.0.0"
    author = "Your Name"
    requires = ["requests>=2.28.0"]

    def execute(self, args):
        return 0
```

### Plugin Dependencies

Handle dependencies between plugins:

```python
@register_plugin
class DependentPlugin(PluginBase):
    """Plugin that depends on another plugin."""

    name = "dependent"
    description = "Depends on other plugins"

    def execute(self, args):
        # Get required plugin
        registry = PluginRegistry.get_instance()
        required = registry.get_plugin("required-plugin")

        if not required:
            print("Error: Required plugin not found")
            return 1

        # Use required plugin
        # ...
        return 0
```

## Next Steps

- **Read the tutorials**: See [examples/](./examples/) for complete plugin examples
- **Explore existing plugins**: Check [plugins/](../../plugins/) for real-world examples
- **Contribute**: Submit your plugins via pull request
- **Get help**: Open an issue on GitHub for plugin development questions

## Related Documentation

- [CLI Documentation](../../docs/cli.md) - Main CLI command reference
- [Architecture Guide](../../docs/architecture.md) - Overall system design
- [Contributing Guide](../../CONTRIBUTING.md) - How to contribute plugins

---

**Last updated**: 2025-11-26
**Version**: 1.0.0
**Status**: Production-ready
