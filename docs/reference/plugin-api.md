# Plugin API Reference

**Complete API reference for the amplihack plugin system.**

## Overview

This reference documents all public classes, methods, and attributes in the plugin system. For tutorials and examples, see [Plugin System README](../../src/amplihack/plugins/README.md).

## Table of Contents

- [PluginBase Class](#pluginbase-class)
- [PluginRegistry Class](#pluginregistry-class)
- [Decorators](#decorators)
- [Exceptions](#exceptions)
- [Type Definitions](#type-definitions)

## PluginBase Class

Abstract base class that all plugins must inherit from.

### Class Definition

```python
from abc import ABC, abstractmethod
import argparse

class PluginBase(ABC):
    """Abstract base class for all amplihack plugins."""

    name: str
    description: str

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the plugin command."""
        pass
```

### Required Attributes

#### `name: str`

Unique identifier for the plugin. Used in CLI commands.

**Requirements:**

- Must be unique across all plugins
- Lowercase alphanumeric characters and hyphens only
- No spaces or special characters
- Maximum 50 characters

**Example:**

```python
class MyPlugin(PluginBase):
    name = "analyze-code"  # ✓ Valid
    # name = "Analyze Code"  # ❌ Invalid: spaces and uppercase
    # name = "analyze_code"  # ⚠ Discouraged: use hyphens not underscores
```

#### `description: str`

Brief description of plugin functionality. Shown in help text.

**Requirements:**

- One sentence describing what the plugin does
- Maximum 100 characters
- No trailing period

**Example:**

```python
class MyPlugin(PluginBase):
    description = "Analyze code quality and complexity"  # ✓ Valid
    # description = "Analyzes code."  # ⚠ Avoid trailing period
```

### Required Methods

#### `execute(args: argparse.Namespace) -> int`

Main execution method called when plugin is invoked from CLI.

**Parameters:**

- `args` (argparse.Namespace): Parsed command-line arguments

**Returns:**

- `int`: Exit code (0 for success, non-zero for error)

**Standard Exit Codes:**

- `0`: Success
- `1`: General error
- `2`: Command line usage error
- `126`: Command cannot execute
- `127`: Command not found
- `128+N`: Fatal error signal N

**Example:**

```python
def execute(self, args: argparse.Namespace) -> int:
    """Execute the plugin."""
    try:
        # Access arguments
        verbose = getattr(args, 'verbose', False)
        file_path = getattr(args, 'file', None)

        # Validate input
        if not file_path:
            print("Error: --file argument required")
            return 2

        # Execute plugin logic
        result = self._process_file(file_path)

        # Return success
        if verbose:
            print(f"Processed {file_path} successfully")
        return 0

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
```

### Optional Methods

Plugins can define additional methods for internal organization:

```python
class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My plugin"

    def execute(self, args: argparse.Namespace) -> int:
        """Main entry point."""
        data = self._load_data(args.file)
        result = self._process_data(data)
        self._save_result(result, args.output)
        return 0

    def _load_data(self, file_path: str):
        """Load data from file."""
        # Implementation...

    def _process_data(self, data):
        """Process loaded data."""
        # Implementation...

    def _save_result(self, result, output_path: str):
        """Save result to file."""
        # Implementation...
```

### Accessing Arguments

Use `getattr()` for safe argument access with defaults:

```python
def execute(self, args: argparse.Namespace) -> int:
    # Safe access with default
    verbose = getattr(args, 'verbose', False)
    timeout = getattr(args, 'timeout', 30)
    config_file = getattr(args, 'config', None)

    # Check if argument exists
    if hasattr(args, 'api_key'):
        api_key = args.api_key
    else:
        print("Warning: No API key provided")
```

## PluginRegistry Class

Thread-safe singleton that manages plugin discovery, registration, and retrieval.

### Class Definition

```python
class PluginRegistry:
    """Thread-safe singleton registry for plugins."""

    _instance = None
    _lock = threading.Lock()
    _init_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'PluginRegistry':
        """Get the singleton instance."""
        # Implementation uses double-checked locking
```

### Singleton Access

#### `PluginRegistry.get_instance() -> PluginRegistry`

Get the singleton registry instance. Thread-safe.

**Returns:**

- `PluginRegistry`: The singleton instance

**Example:**

```python
from amplihack.plugins import PluginRegistry

registry = PluginRegistry.get_instance()
```

**Thread Safety:**

```python
import threading

def register_in_thread():
    registry = PluginRegistry.get_instance()  # Same instance
    # ... use registry ...

# All threads get same instance
threads = [threading.Thread(target=register_in_thread) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

### Plugin Registration

#### `register_plugin(plugin_class: Type[PluginBase]) -> None`

Register a plugin class. Thread-safe.

**Parameters:**

- `plugin_class` (Type[PluginBase]): Plugin class to register

**Raises:**

- `TypeError`: If plugin doesn't inherit from PluginBase
- `ValueError`: If plugin missing required attributes
- `ValueError`: If plugin name already registered

**Example:**

```python
from amplihack.plugins import PluginRegistry, PluginBase

class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My plugin"
    def execute(self, args):
        return 0

registry = PluginRegistry.get_instance()
registry.register_plugin(MyPlugin)
```

**Validation:**

```python
# ❌ Raises TypeError: Not a PluginBase subclass
registry.register_plugin(str)

# ❌ Raises ValueError: Missing name attribute
class BadPlugin(PluginBase):
    description = "Missing name"
    def execute(self, args):
        return 0
registry.register_plugin(BadPlugin)

# ❌ Raises ValueError: Name already registered
registry.register_plugin(MyPlugin)  # First registration
registry.register_plugin(MyPlugin)  # Second registration raises error
```

### Plugin Retrieval

#### `get_plugin(name: str) -> Optional[PluginBase]`

Retrieve a registered plugin by name. Returns an instance.

**Parameters:**

- `name` (str): Plugin name to retrieve

**Returns:**

- `PluginBase`: Plugin instance if found
- `None`: If plugin not found

**Example:**

```python
registry = PluginRegistry.get_instance()

# Get plugin
plugin = registry.get_plugin("hello")
if plugin:
    print(f"Found: {plugin.description}")
    result = plugin.execute(args)
else:
    print("Plugin not found")
```

**Instance Creation:**

```python
# Each call returns a NEW instance
plugin1 = registry.get_plugin("hello")
plugin2 = registry.get_plugin("hello")
assert plugin1 is not plugin2  # Different instances
```

#### `list_plugins() -> List[str]`

Get list of all registered plugin names.

**Returns:**

- `List[str]`: Sorted list of plugin names

**Example:**

```python
registry = PluginRegistry.get_instance()

plugins = registry.list_plugins()
print(f"Available plugins: {', '.join(plugins)}")
# Output: Available plugins: analyze, countfiles, hello

# Check if plugin exists
if "hello" in registry.list_plugins():
    plugin = registry.get_plugin("hello")
```

### Plugin Discovery

#### `discover_plugins(plugin_dir: str, max_file_size: int = 10485760) -> None`

Discover and load plugins from a directory. Thread-safe.

**Parameters:**

- `plugin_dir` (str): Directory path to scan for plugins
- `max_file_size` (int, optional): Maximum file size in bytes (default: 10MB)

**Raises:**

- `SecurityError`: If path traversal detected
- `FileNotFoundError`: If directory doesn't exist
- `PermissionError`: If directory not readable

**Security Features:**

- Path traversal prevention
- File size limits
- Safe import isolation
- Python file validation

**Example:**

```python
from amplihack.plugins import PluginRegistry

registry = PluginRegistry.get_instance()

# Discover plugins in directory
registry.discover_plugins("./plugins")

# Discover with custom size limit (5MB)
registry.discover_plugins("./plugins", max_file_size=5*1024*1024)
```

**Directory Structure:**

```
plugins/
├── hello.py          # ✓ Discovered
├── greet.py          # ✓ Discovered
├── utils.py          # ⚠ Ignored (no @register_plugin)
├── __init__.py       # ⚠ Ignored (special file)
└── test_plugin.py    # ⚠ Ignored (test file)
```

**Security Examples:**

```python
# ✓ Safe paths
registry.discover_plugins("./plugins")
registry.discover_plugins("/opt/amplihack/plugins")

# ❌ Blocked: Path traversal attempts
registry.discover_plugins("./plugins/../../../etc")
# Raises: SecurityError("Path traversal detected")

registry.discover_plugins("./plugins/../sensitive")
# Raises: SecurityError("Path traversal detected")
```

**Error Handling:**

```python
try:
    registry.discover_plugins("./plugins")
except FileNotFoundError:
    print("Plugin directory not found")
except PermissionError:
    print("Cannot read plugin directory")
except SecurityError as e:
    print(f"Security error: {e}")
```

## Decorators

### @register_plugin

Decorator that automatically registers plugins at import time.

**Signature:**

```python
def register_plugin(cls: Type[PluginBase]) -> Type[PluginBase]:
    """Register a plugin class with the registry."""
```

**Parameters:**

- `cls` (Type[PluginBase]): Plugin class to register

**Returns:**

- `Type[PluginBase]`: The original class (transparent decorator)

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

**What It Does:**

1. **Validates** plugin implements required interface:
   - Inherits from PluginBase
   - Has `name` attribute
   - Has `description` attribute
   - Has `execute()` method

2. **Registers** plugin with PluginRegistry singleton

3. **Returns** original class unchanged (transparent)

**Transparent Decorator:**

```python
@register_plugin
class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My plugin"

    def execute(self, args):
        return 0

# MyPlugin is still the original class
assert MyPlugin.name == "myplugin"
assert isinstance(MyPlugin(), PluginBase)
```

**Error Handling:**

```python
# ❌ Raises TypeError: Not a PluginBase subclass
@register_plugin
class NotAPlugin:
    pass

# ❌ Raises ValueError: Missing required attributes
@register_plugin
class IncompletePlugin(PluginBase):
    # Missing name and description
    def execute(self, args):
        return 0
```

## Exceptions

### Standard Exceptions

The plugin system uses standard Python exceptions with descriptive messages:

#### `TypeError`

Raised when plugin class doesn't inherit from PluginBase.

```python
@register_plugin
class NotAPlugin:  # Doesn't inherit from PluginBase
    pass
# Raises: TypeError("Plugin must inherit from PluginBase")
```

#### `ValueError`

Raised when plugin missing required attributes or invalid values.

```python
@register_plugin
class BadPlugin(PluginBase):
    # Missing name attribute
    description = "No name"
    def execute(self, args):
        return 0
# Raises: ValueError("Plugin must define 'name' attribute")
```

#### `SecurityError`

Raised when security violations detected (path traversal, size limits).

```python
registry.discover_plugins("./plugins/../../../etc")
# Raises: SecurityError("Path traversal detected")
```

#### `FileNotFoundError`

Raised when plugin directory doesn't exist.

```python
registry.discover_plugins("./nonexistent")
# Raises: FileNotFoundError
```

#### `PermissionError`

Raised when plugin directory not readable.

```python
registry.discover_plugins("/root/plugins")
# Raises: PermissionError (if no read permission)
```

## Type Definitions

### Type Hints

The plugin system uses standard Python type hints:

```python
from typing import Type, Optional, List
from abc import ABC, abstractmethod
import argparse

class PluginBase(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        pass

class PluginRegistry:
    def register_plugin(self, plugin_class: Type[PluginBase]) -> None:
        pass

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        pass

    def list_plugins(self) -> List[str]:
        pass

    def discover_plugins(self, plugin_dir: str, max_file_size: int = 10485760) -> None:
        pass
```

### Common Type Patterns

```python
from typing import Type, Optional, List, Dict, Any
import argparse

# Plugin class type
PluginClass = Type[PluginBase]

# Arguments type
Args = argparse.Namespace

# Exit code type
ExitCode = int

# Plugin dictionary type
PluginDict = Dict[str, Type[PluginBase]]
```

## Usage Examples

### Complete Plugin Implementation

```python
from amplihack.plugins import PluginBase, register_plugin
from pathlib import Path
from typing import Optional
import json

@register_plugin
class ConfigAnalyzerPlugin(PluginBase):
    """Analyze configuration files for issues."""

    name = "analyze-config"
    description = "Analyze configuration files for common issues"

    def execute(self, args: argparse.Namespace) -> int:
        """Execute configuration analysis."""
        try:
            # Get arguments
            config_file = getattr(args, 'config', None)
            verbose = getattr(args, 'verbose', False)

            # Validate
            if not config_file:
                print("Error: --config argument required")
                return 2

            # Process
            issues = self._analyze_config(config_file, verbose)

            # Report
            if issues:
                print(f"Found {len(issues)} issues:")
                for issue in issues:
                    print(f"  - {issue}")
                return 1
            else:
                print("No issues found")
                return 0

        except FileNotFoundError:
            print(f"Error: Config file not found: {config_file}")
            return 1
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config: {e}")
            return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1

    def _analyze_config(self, config_file: str, verbose: bool) -> List[str]:
        """Analyze configuration file."""
        issues = []

        # Load config
        path = Path(config_file)
        config = json.loads(path.read_text())

        if verbose:
            print(f"Analyzing {config_file}...")

        # Check for issues
        if not config.get('version'):
            issues.append("Missing 'version' field")

        if not config.get('name'):
            issues.append("Missing 'name' field")

        # Add more checks...

        return issues
```

### Complete CLI Integration

```python
# main.py - CLI entry point
import argparse
from amplihack.plugins import PluginRegistry

def main():
    """Main CLI entry point."""
    # Discover plugins
    registry = PluginRegistry.get_instance()
    registry.discover_plugins("./plugins")

    # Create parser
    parser = argparse.ArgumentParser(description="amplihack CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Add plugin commands
    for plugin_name in registry.list_plugins():
        plugin = registry.get_plugin(plugin_name)
        subparser = subparsers.add_parser(plugin_name, help=plugin.description)
        # Add plugin-specific arguments here

    # Parse arguments
    args = parser.parse_args()

    # Execute plugin
    if args.command:
        plugin = registry.get_plugin(args.command)
        if plugin:
            exit_code = plugin.execute(args)
            return exit_code
        else:
            print(f"Error: Unknown command: {args.command}")
            return 1
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    exit(main())
```

## Related Documentation

- [Plugin System Overview](../../src/amplihack/plugins/README.md) - Complete guide with tutorials
- [CLI Documentation](../cli.md) - Main CLI reference
- [Architecture Guide](../architecture.md) - System design

---

**Last updated**: 2025-11-26
**Version**: 1.0.0
**Status**: Production-ready
