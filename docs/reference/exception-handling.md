# Exception Handling Reference

**Document Type**: Reference (Diátaxis)
**Audience**: Developers working with amplihack internals
**Last Updated**: 2026-02-19

## Overview

Amplihack uses a structured exception hierarchy for error handling across the CLI, hooks, and core components. All exceptions inherit from `AmplihackError`, enabling both broad and specific exception handling.

## Exception Hierarchy

```
AmplihackError (base)
├── CLIError
│   ├── ClaudeBinaryNotFoundError
│   ├── LaunchError
│   └── AppendInstructionError
├── LauncherError
│   ├── AutoModeError
│   └── SessionNotFoundError
├── ConfigurationError
├── PluginError
└── RecipeError
    ├── RecipeNotFoundError
    └── RecipeValidationError
```

## Exception Classes

### Base Exception

#### `AmplihackError`

Base exception for all amplihack-specific errors.

**Usage**: Catch this to handle any amplihack error broadly.

```python
try:
    # amplihack operation
    pass
except AmplihackError as e:
    # Handle any amplihack error
    logger.error(f"Amplihack error: {e}")
```

### CLI Exceptions

#### `CLIError`

Base exception for CLI-level errors.

#### `ClaudeBinaryNotFoundError`

Raised when the Claude CLI binary cannot be located or installed.

**Common Causes**:
- Claude CLI not installed
- Binary not in PATH
- Installation failed

**Example**:
```python
from amplihack.exceptions import ClaudeBinaryNotFoundError

try:
    path = require_claude_cli()
except ClaudeBinaryNotFoundError as e:
    print(f"Please install Claude CLI: {e}")
```

#### `LaunchError`

Raised when launching Claude CLI fails.

**Common Causes**:
- Invalid arguments
- Permission issues
- Process spawn failure

#### `AppendInstructionError`

Raised when appending an instruction to an active session fails.

**Common Causes**:
- Session not found
- Communication error with Claude CLI
- Invalid instruction format

### Launcher Exceptions

#### `LauncherError`

Base exception for launcher-level errors.

#### `AutoModeError`

Raised when auto-mode encounters a fatal error.

**Common Causes**:
- Invalid auto-mode configuration
- File system access issues
- Markdown rendering failure

#### `SessionNotFoundError`

Raised when a required active session cannot be found.

**Common Causes**:
- No active Claude Code sessions
- Session terminated unexpectedly
- Session search failure

### Configuration Exceptions

#### `ConfigurationError`

Raised when configuration is missing or invalid.

**Common Causes**:
- Missing required configuration files
- Invalid JSON/YAML syntax
- Missing required fields
- Invalid configuration values

**Example**:
```python
from amplihack.exceptions import ConfigurationError

try:
    config = load_config()
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    # Use default configuration or exit
```

#### `PluginError`

Raised when a plugin operation fails.

**Common Causes**:
- Plugin not found
- Plugin initialization failure
- Git clone failure (for git-based plugins)
- Dependency conflicts

### Recipe Exceptions

#### `RecipeError`

Base exception for recipe-related failures.

#### `RecipeNotFoundError`

Raised when a requested recipe cannot be found.

**Common Causes**:
- Recipe name typo
- Recipe file missing
- Invalid recipe directory structure

**Example**:
```python
from amplihack.exceptions import RecipeNotFoundError

try:
    recipe = load_recipe("my-recipe")
except RecipeNotFoundError as e:
    print(f"Recipe not found: {e}")
    # List available recipes
```

#### `RecipeValidationError`

Raised when a recipe file fails validation.

**Common Causes**:
- Invalid YAML syntax
- Missing required fields
- Invalid step definitions
- Circular dependencies

## Exception Handling Best Practices

### 1. Always Log Exceptions

All exceptions should be logged at an appropriate level:

```python
import logging

try:
    risky_operation()
except AmplihackError as e:
    logging.error(f"Operation failed: {e}", exc_info=True)
```

### 2. Use Specific Exception Types

Catch specific exceptions when you can handle them differently:

```python
from amplihack.exceptions import (
    ClaudeBinaryNotFoundError,
    LaunchError,
    ConfigurationError
)

try:
    launch_claude()
except ClaudeBinaryNotFoundError:
    # Specific handling for missing binary
    install_claude_cli()
except LaunchError:
    # Specific handling for launch failure
    retry_launch()
except ConfigurationError:
    # Specific handling for config issues
    use_default_config()
```

### 3. Fail-Open for Non-Critical Operations

Hooks and monitoring code should fail-open (continue operation on error):

```python
try:
    collect_metrics()
except Exception as e:
    # Log but don't raise - fail-open
    logging.debug(f"Metrics collection failed: {e}")
```

### 4. Fail-Safe for Critical Operations

Critical operations should fail-safe (halt on error):

```python
from amplihack.exceptions import ConfigurationError

try:
    config = load_critical_config()
except ConfigurationError as e:
    logging.error(f"Critical config failed: {e}")
    sys.exit(1)  # Fail-safe - cannot continue
```

### 5. Never Use Bare `except`

Always specify the exception type or use `Exception`:

```python
# Bad
try:
    operation()
except:  # Catches everything including KeyboardInterrupt
    pass

# Good
try:
    operation()
except Exception as e:  # Catches runtime errors only
    logging.error(f"Operation failed: {e}")
```

## Hook Exception Handling

Hooks implement specific exception handling patterns based on their purpose:

### Session Hooks (fail-open)

```python
try:
    inject_context()
except Exception as e:
    # Log to stderr, continue session
    print(f"Warning: Context injection failed: {e}", file=sys.stderr)
```

### Power Steering Hook (sanitized logging)

```python
try:
    validate_response()
except Exception as e:
    # Sanitize paths/tokens before logging
    _log_sdk_error("validation", e)
```

### Stop Hook (fail-safe for lock checks)

```python
try:
    check_lock_flag()
except Exception as e:
    # Log but allow stop - fail-safe
    self.log(f"Lock check failed: {e}", level="DEBUG")
```

## Logging Levels

Use appropriate logging levels based on exception severity:

| Level | Use Case | Example |
|-------|----------|---------|
| `DEBUG` | Expected failures, fail-open scenarios | Metrics collection failed |
| `WARNING` | Degraded operation, using fallbacks | Config file missing, using defaults |
| `ERROR` | Operation failed but service continues | Request failed, will retry |
| `CRITICAL` | Fatal errors requiring immediate action | Database corruption detected |

## Migration Notes

### Pre-PR #2407 & #2409

Previously, many exception blocks were silent:

```python
# Before
try:
    operation()
except Exception:
    pass  # Silent failure
```

### Post-PR #2407 & #2409

All exception blocks now log errors while preserving fail-open/fail-safe semantics:

```python
# After
try:
    operation()
except Exception as e:
    logging.debug(f"Operation failed: {e}")
```

## See Also

- [How-To: Exception Handling Best Practices](../howto/exception-handling.md)
- [Hook System README](../claude/tools/amplihack/hooks/README.md)
- [Source: `src/amplihack/exceptions.py`](../../src/amplihack/exceptions.py)
