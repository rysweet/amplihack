# How-To: Implement Exception Handling

**Document Type**: How-To (Diátaxis)
**Audience**: Developers adding or modifying amplihack code
**Prerequisites**: Basic Python exception handling knowledge
**Last Updated**: 2026-02-19

## Goal

Learn how to implement proper exception handling in amplihack following project best practices established in PRs #2407 and #2409.

## Adding Exception Handling to New Code

### Step 1: Choose the Appropriate Exception Type

Import the relevant exception from `amplihack.exceptions`:

```python
from amplihack.exceptions import (
    ClaudeBinaryNotFoundError,  # For binary not found
    ConfigurationError,         # For config issues
    RecipeNotFoundError,        # For missing recipes
)
```

See [Exception Handling Reference](../reference/exception-handling.md) for the complete exception hierarchy.

### Step 2: Determine Fail-Open vs Fail-Safe Behavior

**Fail-Open** (continue on error):
- Non-critical operations
- Hooks and monitoring
- Metrics collection
- UI enhancements

**Fail-Safe** (halt on error):
- Critical configuration
- Data integrity operations
- Security checks
- Required dependencies

### Step 3: Implement Exception Handling

#### For Fail-Open Operations

```python
import logging

def collect_optional_metrics():
    """Collect metrics if possible, continue if not."""
    try:
        metrics = gather_system_metrics()
        save_metrics(metrics)
    except Exception as e:
        # Log at DEBUG level, continue operation
        logging.debug(f"Metrics collection failed: {e}")
        # No raise - fail-open behavior
```

#### For Fail-Safe Operations

```python
import sys
import logging
from amplihack.exceptions import ConfigurationError

def load_required_config():
    """Load critical configuration or exit."""
    try:
        config = parse_config_file("config.json")
        validate_config(config)
        return config
    except ConfigurationError as e:
        # Log at ERROR level, halt operation
        logging.error(f"Critical config failed: {e}")
        sys.exit(1)  # Fail-safe - cannot continue
```

## Fixing Silent Exception Blocks

### Before (Silent Failure)

```python
# Anti-pattern: Silent exception
def risky_operation():
    try:
        do_something()
    except Exception:
        pass  # Silent - no logging, no visibility
```

### After (Logged Failure)

```python
import logging

def risky_operation():
    try:
        do_something()
    except Exception as e:
        # Proper logging with context
        logging.debug(f"Operation failed: {e}")
        # Still fail-open, but now visible
```

## Hook Exception Handling Patterns

### Pattern 1: Standard Hook (Fail-Open)

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

def process_hook(input_data):
    """Process hook input with fail-open error handling."""
    try:
        # Hook processing logic
        result = process_data(input_data)
        return {"success": True, "result": result}
    except Exception as e:
        # Log to stderr, return empty dict
        print(f"Hook processing failed: {e}", file=sys.stderr)
        return {}  # Fail-open
```

### Pattern 2: Power Steering Hook (Sanitized Logging)

```python
import logging

def _log_sdk_error(operation: str, error: Exception):
    """Log SDK error with sanitized paths and tokens."""
    msg = str(error)
    # Sanitize sensitive information
    msg = sanitize_paths(msg)
    msg = sanitize_tokens(msg)
    logging.debug(f"SDK {operation} failed: {msg}")

def validate_sdk_response(response: str) -> bool:
    try:
        # Validation logic
        return is_valid(response)
    except Exception as e:
        # Sanitize before logging
        _log_sdk_error("validation", e)
        return False  # Fail-open
```

### Pattern 3: Stop Hook (Lock Check)

```python
class StopHook:
    def check_lock_flag(self):
        """Check if continuous work mode is active."""
        try:
            lock_file = Path("~/.amplihack/.claude/tools/amplihack/.lock_active")
            return lock_file.exists()
        except Exception as e:
            # Log but allow stop - fail-safe
            self.log(f"Lock check failed: {e}", level="DEBUG")
            return False  # Default: allow stop
```

## Common Scenarios

### Scenario 1: File Operations

```python
from pathlib import Path
import logging

def read_optional_config(config_path: Path):
    """Read config file if it exists, use defaults otherwise."""
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        # Expected case - use defaults
        logging.debug(f"Config file not found, using defaults: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        # Malformed file - warn and use defaults
        logging.warning(f"Invalid JSON in config: {e}")
        return {}
    except Exception as e:
        # Unexpected error - log and use defaults
        logging.error(f"Failed to read config: {e}")
        return {}
```

### Scenario 2: External Process Calls

```python
import subprocess
import logging
from amplihack.exceptions import LaunchError

def launch_claude_cli(args: list[str]):
    """Launch Claude CLI with error handling."""
    try:
        result = subprocess.run(
            ["claude"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except FileNotFoundError:
        # Claude CLI not installed
        raise ClaudeBinaryNotFoundError("Claude CLI not found in PATH")
    except subprocess.CalledProcessError as e:
        # Process failed
        raise LaunchError(f"Claude CLI failed: {e.stderr}")
    except Exception as e:
        # Unexpected error
        logging.error(f"Unexpected launch error: {e}")
        raise LaunchError(f"Failed to launch: {e}")
```

### Scenario 3: API/Network Calls

```python
import logging
import requests

def fetch_update_info():
    """Fetch update information with retry logic."""
    try:
        response = requests.get(
            "https://api.example.com/version",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logging.debug("Update check timed out")
        return None  # Fail-open
    except requests.RequestException as e:
        logging.debug(f"Update check failed: {e}")
        return None  # Fail-open
    except Exception as e:
        logging.warning(f"Unexpected update check error: {e}")
        return None  # Fail-open
```

## Testing Exception Handling

### Unit Test Example

```python
import pytest
from amplihack.exceptions import ConfigurationError

def test_config_loading_with_invalid_file():
    """Test that invalid config raises ConfigurationError."""
    with pytest.raises(ConfigurationError, match="Invalid JSON"):
        load_config("invalid.json")

def test_metrics_collection_fails_gracefully():
    """Test that metrics collection failure doesn't crash."""
    # Should not raise, even if metrics fail
    collect_optional_metrics()

    # Verify logging occurred
    # (use caplog fixture or mock logging)
```

### Outside-In Test Example

```python
# tests/outside-in/test_hook_error_handling.yaml
---
scenario: "Hook handles errors gracefully"
given:
  - Hook receives malformed input
when:
  - Hook is executed
then:
  - Hook logs error to stderr
  - Hook returns empty dict (not crash)
  - Claude Code continues normally
```

## Logging Best Practices

### Choose the Right Level

```python
import logging

# DEBUG - Expected failures, diagnostics
logging.debug("Cache miss, will fetch from API")

# WARNING - Degraded but functional
logging.warning("Config file missing, using defaults")

# ERROR - Operation failed, service continues
logging.error("Failed to save metrics, data lost")

# CRITICAL - Fatal error, service cannot continue
logging.critical("Database corruption detected")
```

### Include Context in Log Messages

```python
# Bad: No context
logging.error("Failed")

# Good: Context included
logging.error(f"Failed to load recipe '{recipe_name}': {e}")

# Better: Structured logging with exc_info
logging.error(
    f"Recipe load failed",
    extra={"recipe_name": recipe_name},
    exc_info=True
)
```

## Checklist

Before submitting code with exception handling:

- [ ] Appropriate exception type imported from `amplihack.exceptions`
- [ ] Fail-open vs fail-safe behavior chosen correctly
- [ ] All exception blocks log errors (no silent failures)
- [ ] Logging level appropriate for severity
- [ ] Log messages include relevant context
- [ ] Sensitive information (paths, tokens) sanitized in logs
- [ ] Unit tests cover exception cases
- [ ] Outside-in tests verify fail-open/fail-safe behavior

## See Also

- [Exception Handling Reference](../reference/exception-handling.md) - Complete exception hierarchy
- [Hook System README](../claude/tools/amplihack/hooks/README.md) - Hook-specific patterns
- [Testing Strategy](../testing/TEST_PLAN.md) - Testing exception handling
- [Source: PR #2407](https://github.com/rysweet/amplihack/pull/2407) - Hook exception handling fixes
- [Source: PR #2409](https://github.com/rysweet/amplihack/pull/2409) - CLI exception handling improvements
