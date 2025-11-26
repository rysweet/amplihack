# ConfigManager API Reference

Thread-safe configuration management with YAML loading and environment variable overrides.

## Overview

The ConfigManager provides a singleton configuration system that:

- Loads configuration from YAML files
- Supports environment variable overrides with `AMPLIHACK_*` prefix
- Uses dot-notation for nested keys (`database.host`)
- Ensures thread-safe operations
- Validates configuration structure

**Location**: `src/amplihack/config/manager.py`

## Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Public API](#public-api)
- [Configuration Format](#configuration-format)
- [Environment Variables](#environment-variables)
- [Error Handling](#error-handling)
- [Thread Safety](#thread-safety)
- [Validation](#validation)

## Installation

```bash
pip install amplihack
```

The ConfigManager is included in the core package. No additional dependencies required beyond PyYAML.

## Quick Start

```python
from amplihack.config import ConfigManager

# Initialize with config file
config = ConfigManager("config/default.yaml")

# Get configuration values
db_host = config.get("database.host")
port = config.get("server.port", default=8000)

# Set values programmatically
config.set("cache.enabled", True)

# Reload from file
config.reload()

# Validate configuration
config.validate()
```

## Public API

### ConfigManager(config_path: str)

Creates or retrieves the singleton ConfigManager instance.

**Parameters**:

- `config_path` (str): Path to YAML configuration file

**Raises**:

- `ConfigFileError`: If file doesn't exist or can't be parsed

**Example**:

```python
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")
# Returns same instance on subsequent calls
config2 = ConfigManager("config/default.yaml")
assert config is config2  # True - singleton pattern
```

### get(key: str, default=None) -> Any

Retrieves a configuration value using dot-notation.

**Parameters**:

- `key` (str): Dot-separated path to value (e.g., "database.host")
- `default` (Any, optional): Value to return if key not found

**Returns**:

- Configuration value or default if key doesn't exist

**Example**:

```python
# Get nested value
host = config.get("database.host")
# Output: "localhost"

# Get with default
timeout = config.get("database.timeout", default=30)
# Output: 30 (if not in config)

# Get top-level value
debug = config.get("debug")
# Output: False
```

**Edge Cases**:

```python
# Non-existent key without default returns None
result = config.get("nonexistent.key")
assert result is None

# Empty string key raises ConfigError
try:
    config.get("")
except ConfigError as e:
    print(e)  # "Key cannot be empty"

# Accessing non-dict intermediate values returns None
config.set("scalar_value", 42)
result = config.get("scalar_value.nested")
assert result is None
```

### set(key: str, value: Any) -> None

Sets a configuration value using dot-notation, creating nested structures as needed.

**Parameters**:

- `key` (str): Dot-separated path to value
- `value` (Any): Value to set (must be JSON-serializable)

**Raises**:

- `ConfigError`: If key is invalid or value not serializable

**Example**:

```python
# Set simple value
config.set("debug", True)

# Set nested value (creates structure)
config.set("database.host", "db.example.com")
config.set("database.port", 5432)

# Set complex structure
config.set("cache.redis", {
    "host": "localhost",
    "port": 6379,
    "db": 0
})
```

**Edge Cases**:

```python
# Creates intermediate dictionaries
config.set("new.nested.deep.value", 42)
# Creates: {"new": {"nested": {"deep": {"value": 42}}}}

# Overwrites existing values
config.set("existing.key", "old")
config.set("existing.key", "new")

# Non-serializable values raise ConfigError
try:
    config.set("bad", lambda x: x)
except ConfigError as e:
    print(e)  # "Value must be JSON-serializable"
```

### reload() -> None

Reloads configuration from the YAML file, re-applying environment variable overrides.

**Raises**:

- `ConfigFileError`: If file can't be read or parsed

**Example**:

```python
# Make changes to config file externally
# Then reload
config.reload()

# Changed values are now available
new_value = config.get("updated.setting")
```

**Behavior**:

- Clears all programmatic changes from `set()`
- Re-reads YAML file
- Re-applies environment variable overrides
- Thread-safe operation

### validate() -> None

Validates the current configuration structure.

**Raises**:

- `ConfigValidationError`: If configuration is invalid

**Example**:

```python
try:
    config.validate()
except ConfigValidationError as e:
    print(f"Invalid config: {e}")
    # Output: "Invalid config: Required key 'database.host' not found"
```

**Validation Checks**:

- Required keys exist
- Values match expected types
- Nested structures are well-formed
- No circular references

## Configuration Format

### YAML Structure

Configuration files use standard YAML syntax:

```yaml
# config/default.yaml
debug: false

database:
  host: localhost
  port: 5432
  name: amplihack
  pool_size: 10

server:
  host: 0.0.0.0
  port: 8000
  workers: 4

cache:
  enabled: true
  ttl: 3600

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  handlers:
    - console
    - file
```

### Supported Types

- Scalars: `str`, `int`, `float`, `bool`, `None`
- Collections: `list`, `dict`
- No support for custom objects or functions

## Environment Variables

### Override Syntax

Environment variables override YAML values using the `AMPLIHACK_` prefix:

**Format**: `AMPLIHACK_SECTION__SUBSECTION__KEY=value`

**Rules**:

- Prefix: `AMPLIHACK_`
- Separator: Double underscore `__` for nesting
- Case: Uppercase recommended but not required

### Examples

```bash
# Override top-level key
export AMPLIHACK_DEBUG=true

# Override nested key (single level)
export AMPLIHACK_DATABASE__HOST=production.db.com

# Override deeply nested key
export AMPLIHACK_CACHE__REDIS__PORT=6380

# Override with different types
export AMPLIHACK_SERVER__PORT=9000  # Parsed as int
export AMPLIHACK_DATABASE__POOL_SIZE=20  # Parsed as int
export AMPLIHACK_CACHE__ENABLED=false  # Parsed as bool
```

### Type Parsing

Environment variables are automatically parsed to appropriate types:

```python
# String values
AMPLIHACK_DATABASE__NAME=mydb
config.get("database.name")  # "mydb" (str)

# Integer values
AMPLIHACK_SERVER__PORT=8080
config.get("server.port")  # 8080 (int)

# Boolean values
AMPLIHACK_DEBUG=true
config.get("debug")  # True (bool)
# Accepts: true/false, True/False, yes/no, 1/0

# Float values
AMPLIHACK_CACHE__TTL=3600.5
config.get("cache.ttl")  # 3600.5 (float)

# List values (JSON format)
AMPLIHACK_LOGGING__HANDLERS='["console", "file"]'
config.get("logging.handlers")  # ["console", "file"] (list)
```

### Precedence

Configuration values follow this precedence (highest to lowest):

1. Environment variables (`AMPLIHACK_*`)
2. Programmatic `set()` calls
3. YAML file values
4. Default parameter in `get()`

```python
# YAML has: database.host = "localhost"
# ENV has: AMPLIHACK_DATABASE__HOST=prod.db.com

config.get("database.host")
# Returns: "prod.db.com" (environment wins)

config.set("database.host", "custom.db.com")
config.get("database.host")
# Returns: "custom.db.com" (set() wins)

config.reload()
config.get("database.host")
# Returns: "prod.db.com" (back to environment after reload)
```

## Error Handling

### Exception Hierarchy

```python
ConfigError                    # Base exception
├── ConfigFileError           # File I/O or parsing errors
└── ConfigValidationError     # Validation failures
```

### ConfigError

Base exception for all configuration errors.

```python
from amplihack.config import ConfigError

try:
    config.set("", "value")
except ConfigError as e:
    print(f"Configuration error: {e}")
```

### ConfigFileError

Raised when configuration file operations fail.

```python
from amplihack.config import ConfigFileError

try:
    config = ConfigManager("nonexistent.yaml")
except ConfigFileError as e:
    print(f"File error: {e}")
    # Output: "File error: Configuration file not found: nonexistent.yaml"

try:
    # Create invalid YAML
    with open("bad.yaml", "w") as f:
        f.write("invalid: yaml: content:")
    config = ConfigManager("bad.yaml")
except ConfigFileError as e:
    print(f"Parse error: {e}")
    # Output: "Parse error: Failed to parse YAML: ..."
```

### ConfigValidationError

Raised when configuration validation fails.

```python
from amplihack.config import ConfigValidationError

try:
    config.validate()
except ConfigValidationError as e:
    print(f"Validation failed: {e}")
    # Output: "Validation failed: Required key 'database.host' not found"
```

## Thread Safety

The ConfigManager is thread-safe using `threading.RLock` (reentrant lock).

### Guarantees

- Multiple threads can read simultaneously
- Write operations are serialized
- `reload()` is atomic - readers see old or new config, never partial
- Same thread can acquire lock multiple times (reentrant)

### Usage in Multithreaded Applications

```python
import threading
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

def worker_thread(thread_id):
    # Safe: Multiple threads reading
    host = config.get("database.host")
    print(f"Thread {thread_id}: {host}")

    # Safe: Multiple threads writing
    config.set(f"thread.{thread_id}.status", "active")

    # Safe: Reload while other threads are reading
    if thread_id == 0:
        config.reload()

# Spawn multiple threads
threads = [
    threading.Thread(target=worker_thread, args=(i,))
    for i in range(10)
]

for t in threads:
    t.start()

for t in threads:
    t.join()
```

### Lock Behavior

```python
# Lock is acquired and released automatically
config.get("key")  # Acquires lock, reads, releases

config.set("key", "value")  # Acquires lock, writes, releases

config.reload()  # Acquires lock, reloads entire config, releases

# Reentrant: Same thread can call nested operations
def complex_operation():
    config.set("outer", config.get("inner"))  # Both operations use same lock
```

## Validation

### Built-in Validation

The `validate()` method checks:

1. **Required keys exist** (if configured)
2. **Type constraints** (if configured)
3. **Value ranges** (if configured)
4. **Structure integrity** (no malformed dicts)

### Example Validation

```python
from amplihack.config import ConfigManager, ConfigValidationError

config = ConfigManager("config/default.yaml")

try:
    config.validate()
    print("Configuration is valid")
except ConfigValidationError as e:
    print(f"Invalid configuration: {e}")
    # Take corrective action
    config.set("database.host", "localhost")
    config.validate()  # Try again
```

### Validation on Load

Validation can be automatic on initialization:

```python
# Validates immediately after loading
config = ConfigManager("config/default.yaml")
# Raises ConfigValidationError if invalid
```

## Complete Example

```python
from amplihack.config import ConfigManager, ConfigError, ConfigFileError
import os

# Set environment override
os.environ["AMPLIHACK_DATABASE__HOST"] = "production.db.com"

try:
    # Initialize configuration
    config = ConfigManager("config/default.yaml")

    # Validate configuration
    config.validate()

    # Read values with defaults
    db_host = config.get("database.host")  # Gets env override
    db_port = config.get("database.port", default=5432)
    debug_mode = config.get("debug", default=False)

    print(f"Database: {db_host}:{db_port}")
    # Output: Database: production.db.com:5432

    # Set runtime values
    config.set("server.workers", 8)
    config.set("cache.enabled", True)

    # Get nested structure
    cache_config = config.get("cache")
    print(f"Cache: {cache_config}")
    # Output: Cache: {'enabled': True, 'ttl': 3600}

    # Reload from file (loses set() changes)
    config.reload()
    workers = config.get("server.workers")  # Back to YAML value

except ConfigFileError as e:
    print(f"Failed to load config: {e}")

except ConfigError as e:
    print(f"Configuration error: {e}")
```

## See Also

- [Configuration How-To Guide](../howto/configuration-setup.md) - Step-by-step setup
- [Environment Variables Guide](../howto/environment-variables.md) - Advanced override patterns
- [Thread Safety Concepts](../concepts/config-thread-safety.md) - Understanding the locking mechanism
