# Configuration Module

Thread-safe configuration management with YAML loading and environment variable overrides.

## Philosophy

**Brick**: Self-contained configuration system with single responsibility
**Stud**: Public API (`get`, `set`, `reload`, `validate`)
**Regeneratable**: Can be rebuilt from this specification

## Public API

The module exports these components via `__all__`:

```python
from amplihack.config import (
    ConfigManager,      # Main configuration manager class
    ConfigError,        # Base exception
    ConfigFileError,    # File I/O errors
    ConfigValidationError  # Validation errors
)
```

## Quick Start

```python
from amplihack.config import ConfigManager

# Initialize with YAML file
config = ConfigManager("config/default.yaml")

# Get values (dot-notation for nested keys)
db_host = config.get("database.host")
port = config.get("server.port", default=8000)

# Set values programmatically
config.set("cache.enabled", True)

# Reload from file
config.reload()

# Validate configuration
config.validate()
```

## Contract Specification

### ConfigManager Class

**Purpose**: Thread-safe singleton configuration manager

**Methods**:

- `__init__(config_path: str)` - Initialize with YAML file path
- `get(key: str, default=None) -> Any` - Retrieve configuration value
- `set(key: str, value: Any) -> None` - Set configuration value
- `reload() -> None` - Reload configuration from file
- `validate() -> None` - Validate configuration structure

**Key Semantics**:

- Dot-notation for nested keys: `"database.host"`
- Case-sensitive keys
- Creates intermediate dicts in `set()` if needed

**Thread Safety**:

- All operations are thread-safe using `threading.RLock`
- Reentrant lock allows same thread to acquire multiple times
- `reload()` is atomic - readers see old or new config, never partial

### Environment Variable Overrides

**Format**: `AMPLIHACK_SECTION__SUBSECTION__KEY=value`

**Rules**:

- Prefix: `AMPLIHACK_` (required)
- Separator: Double underscore `__` for nesting levels
- Type parsing: Automatic (int, float, bool, str, list via JSON)

**Examples**:

```bash
export AMPLIHACK_DEBUG=true
export AMPLIHACK_DATABASE__HOST=prod.db.com
export AMPLIHACK_SERVER__PORT=9000
```

**Precedence** (highest to lowest):

1. Environment variables
2. Programmatic `set()` calls
3. YAML file values
4. Default parameter in `get()`

### Exception Hierarchy

```
ConfigError (base)
├── ConfigFileError (file I/O, parsing errors)
└── ConfigValidationError (validation failures)
```

### Configuration File Format

Standard YAML with nested structure:

```yaml
# config/default.yaml
debug: false

database:
  host: localhost
  port: 5432
  name: amplihack

server:
  host: 0.0.0.0
  port: 8000
  workers: 4
```

## Implementation Details

**Location**: `src/amplihack/config/manager.py`

**Architecture**:

- `ConfigManager` - Main class (singleton pattern)
- `_YAMLLoader` - Private helper for YAML parsing
- `_EnvParser` - Private helper for environment variable parsing

**Dependencies**:

- `PyYAML` - YAML file parsing
- `threading` - Thread safety (RLock)
- Standard library only (pathlib, os, json)

**Design Patterns**:

- Singleton: One ConfigManager instance per config file
- Reentrant Locking: Thread-safe with nested operations
- Lazy Loading: Config loaded on first access

## Usage Examples

### Basic Configuration

```python
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

# Simple access
debug_enabled = config.get("debug")

# Nested access
db_host = config.get("database.host")
db_port = config.get("database.port", default=5432)

# Set values
config.set("server.workers", 8)
```

### Environment Overrides

```bash
# Set environment variables
export AMPLIHACK_DATABASE__HOST=production.db.com
export AMPLIHACK_DATABASE__PORT=5433
export AMPLIHACK_DEBUG=true
```

```python
config = ConfigManager("config/default.yaml")

# Gets environment override
host = config.get("database.host")
# Returns: "production.db.com"
```

### Error Handling

```python
from amplihack.config import (
    ConfigManager,
    ConfigFileError,
    ConfigValidationError
)

try:
    config = ConfigManager("config/production.yaml")
    config.validate()

    db_host = config.get("database.host")

except ConfigFileError as e:
    print(f"Failed to load config: {e}")

except ConfigValidationError as e:
    print(f"Invalid configuration: {e}")
```

### Thread-Safe Operations

```python
import threading
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

def worker_thread(thread_id):
    # Thread-safe read
    value = config.get("database.host")

    # Thread-safe write
    config.set(f"thread.{thread_id}.status", "active")

threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(10)]
for t in threads:
    t.start()
```

### Reload Configuration

```python
config = ConfigManager("config/default.yaml")

# Make runtime changes
config.set("cache.enabled", False)

# External process updates YAML file
# ...

# Reload from file (loses set() changes)
config.reload()

# Back to file values plus env overrides
cache_enabled = config.get("cache.enabled")
```

## Testing

Test the public contract, not implementation:

```python
import pytest
from amplihack.config import ConfigManager, ConfigError

def test_get_with_default(tmp_path):
    """Test get() returns default for missing keys"""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: value")

    config = ConfigManager(str(config_file))

    assert config.get("nonexistent", default="default") == "default"

def test_set_creates_nested(tmp_path):
    """Test set() creates intermediate dicts"""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("{}")

    config = ConfigManager(str(config_file))
    config.set("a.b.c", "value")

    assert config.get("a.b.c") == "value"

def test_env_override(tmp_path, monkeypatch):
    """Test environment variables override YAML"""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: yaml_value")

    monkeypatch.setenv("AMPLIHACK_KEY", "env_value")

    config = ConfigManager(str(config_file))
    assert config.get("key") == "env_value"
```

## Module Structure

```
src/amplihack/config/
├── __init__.py          # Public API exports
├── manager.py           # ConfigManager implementation
├── exceptions.py        # Exception classes
├── README.md           # This file (contract specification)
└── tests/
    ├── test_manager.py
    ├── test_env_parsing.py
    └── fixtures/
        └── sample_config.yaml
```

## Edge Cases

### Empty Keys

```python
# Empty string key raises ConfigError
config.get("")  # Raises ConfigError
config.set("", value)  # Raises ConfigError
```

### Non-Dict Intermediate Values

```python
config.set("scalar", 42)

# Accessing nested path on scalar returns None
result = config.get("scalar.nested")
assert result is None
```

### Type Coercion

```python
# No automatic type coercion in get()
config.set("port", "8000")  # String
port = config.get("port")   # Returns "8000" (str)

# Environment variables are parsed
# AMPLIHACK_PORT=8000
port = config.get("port")   # Returns 8000 (int)
```

### Concurrent Reload

```python
# Multiple threads can call reload() safely
# Last reload wins, all readers see consistent state

def thread_a():
    config.reload()  # Reloads from file

def thread_b():
    value = config.get("key")  # Gets old or new, never partial
```

## Design Decisions

### Why Singleton?

Configuration is naturally global state. Singleton ensures all code shares the same config instance, avoiding sync issues.

### Why Reentrant Lock?

Allows nested operations without deadlock:

```python
def complex_operation():
    # Both acquire same lock - reentrant allows this
    value = config.get("key")
    config.set("other_key", value)
```

### Why Dot-Notation?

Simpler API than nested dictionary access:

```python
# Dot-notation (simple)
config.get("database.host")

# Alternative (complex)
config.get("database")["host"]  # Fails if database is None
```

### Why Environment Override?

Follows 12-factor app methodology - configuration via environment is standard for cloud deployments and CI/CD.

## Documentation

Complete documentation in `docs/`:

- [API Reference](../../docs/reference/config-manager.md) - Full API documentation
- [How-To Guide](../../docs/howto/configuration-setup.md) - Step-by-step setup
- [Thread Safety Concepts](../../docs/concepts/config-thread-safety.md) - Understanding locking

## Version

**Specification Version**: 1.0
**Implementation**: `src/amplihack/config/manager.py`
**Last Updated**: 2025-11-26
