# Troubleshoot Plugin Issues

**Solve common plugin problems quickly.**

## Overview

This guide helps ye diagnose and fix common plugin issues. Each problem includes symptoms, causes, and solutions.

## Quick Diagnosis

Start here to identify yer problem:

| Symptom                          | Problem                                         | Section |
| -------------------------------- | ----------------------------------------------- | ------- |
| CLI doesn't recognize command    | [Plugin Not Discovered](#plugin-not-discovered) |
| Import errors on startup         | [Import Failures](#import-failures)             |
| Plugin registers but doesn't run | [Execute Method Issues](#execute-method-issues) |
| Arguments not working            | [Argument Problems](#argument-problems)         |
| Security errors                  | [Security Violations](#security-violations)     |
| Tests failing                    | [Testing Issues](#testing-issues)               |

## Plugin Not Discovered

### Symptoms

```bash
amplihack myplugin
# Output: amplihack: 'myplugin' is not a valid command
```

### Causes & Solutions

#### Cause 1: Missing Decorator

**Check:**

```python
# ❌ Missing decorator
class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My plugin"
    def execute(self, args):
        return 0
```

**Fix:**

```python
# ✓ Add @register_plugin decorator
@register_plugin
class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My plugin"
    def execute(self, args):
        return 0
```

#### Cause 2: Wrong Directory

**Check:**

```bash
ls plugins/myplugin.py
# If not found, file is in wrong location
```

**Fix:**

```bash
# Move plugin to correct directory
mv myplugin.py plugins/
```

#### Cause 3: Not Inheriting from PluginBase

**Check:**

```python
# ❌ Missing inheritance
@register_plugin
class MyPlugin:
    name = "myplugin"
    description = "My plugin"
    def execute(self, args):
        return 0
```

**Fix:**

```python
# ✓ Inherit from PluginBase
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class MyPlugin(PluginBase):
    name = "myplugin"
    description = "My plugin"
    def execute(self, args):
        return 0
```

#### Cause 4: Invalid Name

**Check:**

```python
# ❌ Invalid name (spaces, uppercase)
class MyPlugin(PluginBase):
    name = "My Plugin"  # Spaces not allowed
    # or
    name = "MyPlugin"   # Uppercase not allowed
```

**Fix:**

```python
# ✓ Valid name (lowercase, hyphens)
class MyPlugin(PluginBase):
    name = "my-plugin"
```

## Import Failures

### Symptoms

```bash
amplihack hello
# Output: ImportError: No module named 'some_module'
```

### Causes & Solutions

#### Cause 1: Missing Dependency

**Check:**

```python
# Plugin imports module that's not installed
import requests  # May not be installed
```

**Fix:**

```bash
# Install missing dependency
pip install requests

# Or use standard library instead
import urllib.request  # Built-in
```

#### Cause 2: Wrong Import Path

**Check:**

```python
# ❌ Relative import
from .utils import helper

# ❌ Wrong path
from plugins.utils import helper
```

**Fix:**

```python
# ✓ Absolute import
from amplihack.plugins.utils import helper

# ✓ Or standard library
from pathlib import Path
```

#### Cause 3: Circular Dependency

**Check:**

```python
# plugin_a.py
from plugin_b import HelperB

# plugin_b.py
from plugin_a import HelperA  # Circular!
```

**Fix:**

```python
# Move shared code to separate module
# utils.py
class SharedHelper:
    pass

# plugin_a.py
from utils import SharedHelper

# plugin_b.py
from utils import SharedHelper
```

## Execute Method Issues

### Symptoms

```bash
amplihack myplugin
# Plugin does nothing or errors occur
```

### Causes & Solutions

#### Cause 1: Wrong Method Signature

**Check:**

```python
# ❌ Missing args parameter
def execute(self):
    return 0

# ❌ Wrong parameter name
def execute(self, arguments):
    return 0
```

**Fix:**

```python
# ✓ Correct signature
def execute(self, args):
    return 0
```

#### Cause 2: Not Returning Exit Code

**Check:**

```python
# ❌ No return value
def execute(self, args):
    print("Done")
    # Missing return

# ❌ Wrong return type
def execute(self, args):
    return "success"  # Should be int
```

**Fix:**

```python
# ✓ Return integer exit code
def execute(self, args):
    print("Done")
    return 0  # Success
```

#### Cause 3: Unhandled Exception

**Check:**

```python
# ❌ No error handling
def execute(self, args):
    file_path = args.file  # May not exist
    data = open(file_path).read()  # May fail
    return 0
```

**Fix:**

```python
# ✓ Handle exceptions
def execute(self, args):
    try:
        file_path = getattr(args, 'file', None)
        if not file_path:
            print("Error: --file required")
            return 2

        with open(file_path) as f:
            data = f.read()
        return 0

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
```

## Argument Problems

### Symptoms

```bash
amplihack myplugin --name test
# Arguments not accessible or causing errors
```

### Causes & Solutions

#### Cause 1: Direct Attribute Access

**Check:**

```python
# ❌ Direct access (fails if argument not provided)
def execute(self, args):
    name = args.name  # AttributeError if --name not provided
```

**Fix:**

```python
# ✓ Safe access with getattr()
def execute(self, args):
    name = getattr(args, 'name', 'default')
```

#### Cause 2: Not Checking if Argument Exists

**Check:**

```python
# ❌ Assumes argument exists
def execute(self, args):
    config = args.config  # May not exist
```

**Fix:**

```python
# ✓ Check with hasattr() or getattr()
def execute(self, args):
    if hasattr(args, 'config'):
        config = args.config
    else:
        config = 'default.json'

    # Or use getattr() with default
    config = getattr(args, 'config', 'default.json')
```

#### Cause 3: Wrong Argument Type

**Check:**

```python
# Arguments come as strings
def execute(self, args):
    count = args.count + 1  # TypeError if count is "5"
```

**Fix:**

```python
# ✓ Convert to correct type
def execute(self, args):
    count_str = getattr(args, 'count', '0')
    try:
        count = int(count_str) + 1
    except ValueError:
        print("Error: --count must be a number")
        return 1
    return 0
```

## Security Violations

### Symptoms

```bash
amplihack myplugin
# Output: SecurityError: Path traversal detected
```

### Causes & Solutions

#### Cause 1: Path Traversal in Discovery

**Check:**

```python
# ❌ User input directly in path
plugin_dir = input("Plugin directory: ")
registry.discover_plugins(plugin_dir)  # User could enter ../../../
```

**Fix:**

```python
# ✓ Validate path first
from pathlib import Path

plugin_dir = Path(input("Plugin directory: ")).resolve()
safe_base = Path("/opt/amplihack/plugins").resolve()

if plugin_dir.is_relative_to(safe_base):
    registry.discover_plugins(str(plugin_dir))
else:
    print("Error: Invalid plugin directory")
```

#### Cause 2: File Size Exceeded

**Check:**

```python
# Plugin file larger than 10MB (default limit)
```

**Fix:**

```bash
# Reduce file size or increase limit
registry.discover_plugins("./plugins", max_file_size=20*1024*1024)  # 20MB
```

#### Cause 3: Unsafe File Operations

**Check:**

```python
# ❌ User input in file path
def execute(self, args):
    filename = args.file  # User could enter ../../etc/passwd
    data = open(filename).read()
```

**Fix:**

```python
# ✓ Validate and sanitize paths
from pathlib import Path

def execute(self, args):
    filename = getattr(args, 'file', '')
    path = Path(filename).resolve()
    safe_dir = Path.cwd().resolve()

    # Ensure path is within safe directory
    if not path.is_relative_to(safe_dir):
        print("Error: File must be in current directory")
        return 1

    try:
        data = path.read_text()
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1

    return 0
```

## Testing Issues

### Symptoms

```bash
pytest test_myplugin.py
# Tests fail or errors occur
```

### Causes & Solutions

#### Cause 1: Singleton State Pollution

**Check:**

```python
# Tests interfere with each other due to shared registry
def test_plugin_a():
    registry = PluginRegistry.get_instance()
    registry.register_plugin(PluginA)
    assert "plugin-a" in registry.list_plugins()

def test_plugin_b():
    registry = PluginRegistry.get_instance()
    # Still has plugin-a from previous test!
    assert "plugin-b" in registry.list_plugins()  # Fails
```

**Fix:**

```python
# ✓ Reset registry between tests
def tearDown(self):
    """Clean up after test."""
    registry = PluginRegistry.get_instance()
    registry._plugins.clear()  # Clear state

# Or use separate test directories
def test_plugin_a(tmp_path):
    plugin_dir = tmp_path / "plugins_a"
    plugin_dir.mkdir()
    # Create plugin file
    registry.discover_plugins(str(plugin_dir))
```

#### Cause 2: Missing Test Isolation

**Check:**

```python
# ❌ Tests share files
def test_output():
    plugin.execute(args)
    data = open("output.txt").read()  # Other tests may modify this

def test_error():
    plugin.execute(bad_args)
    # output.txt may still exist from previous test
```

**Fix:**

```python
# ✓ Use temporary directories
import tempfile

def test_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "output.txt"
        args = argparse.Namespace(output=str(output_file))
        plugin.execute(args)
        data = output_file.read_text()
```

#### Cause 3: Not Mocking External Dependencies

**Check:**

```python
# ❌ Tests make real API calls
def test_api_plugin():
    plugin.execute(args)  # Makes real HTTP request
```

**Fix:**

```python
# ✓ Mock external calls
from unittest.mock import patch

def test_api_plugin():
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}
        result = plugin.execute(args)
        assert result == 0
```

## Debugging Strategies

### Enable Verbose Output

Add debug prints to track execution:

```python
def execute(self, args):
    verbose = getattr(args, 'verbose', False)

    if verbose:
        print(f"[DEBUG] Args: {args}")
        print(f"[DEBUG] Starting execution...")

    # ... plugin logic ...

    if verbose:
        print(f"[DEBUG] Execution complete")

    return 0
```

### Check Plugin Registration

Verify plugin is registered:

```python
from amplihack.plugins import PluginRegistry

registry = PluginRegistry.get_instance()
print("Registered plugins:", registry.list_plugins())

plugin = registry.get_plugin("myplugin")
print(f"Plugin found: {plugin is not None}")
if plugin:
    print(f"Plugin class: {plugin.__class__.__name__}")
```

### Test Plugin Directly

Bypass CLI to test plugin directly:

```python
import argparse
from plugins.myplugin import MyPlugin

# Create plugin instance
plugin = MyPlugin()

# Create test arguments
args = argparse.Namespace(
    name="test",
    verbose=True
)

# Execute directly
exit_code = plugin.execute(args)
print(f"Exit code: {exit_code}")
```

### Use Python Debugger

Insert breakpoint to inspect state:

```python
def execute(self, args):
    # Execution stops here
    breakpoint()

    # Continue execution
    name = getattr(args, 'name', 'World')
    print(f"Hello, {name}!")
    return 0
```

Run with debugger:

```bash
python -m pdb -m amplihack myplugin
```

## Getting Help

If these solutions don't help:

1. **Check logs**: Look for detailed error messages
2. **Search issues**: Check [GitHub issues](https://github.com/amplihack/amplihack/issues)
3. **Ask for help**: Open a new issue with:
   - Plugin code
   - Full error message
   - Steps to reproduce
   - Environment details (OS, Python version)

## Related Documentation

- [Create Your First Plugin](../tutorials/create-your-first-plugin.md) - Step-by-step tutorial
- [Plugin System Overview](../../src/amplihack/plugins/README.md) - Complete guide
- [Plugin API Reference](../reference/plugin-api.md) - Full API documentation

---

**Last updated**: 2025-11-26
**Version**: 1.0.0
