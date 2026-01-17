# Memory Configuration Consent Prompt

Intelligent user consent handling for memory configuration updates with timeout protection and non-interactive environment detection.

## Quick Start

When amplihack detects that yer system could benefit from adjusted Node.js memory settings, it presents a prompt like this:

```
============================================================
Memory Configuration Update
============================================================
System RAM: 16 GB
Current limit: Not set
Recommended limit: 8192 MB
============================================================

Update NODE_OPTIONS with recommended limit? (y/n):
```

Ye have 30 seconds to respond. If ye be in an automated environment (CI/CD, scripts), the system detects this and defaults to "yes" without hangin'.

## How It Works

### Interactive Mode (Default)

When runnin' amplihack in a normal terminal session:

1. **Detection**: System analyzes yer total RAM and calculates optimal memory limits
2. **Prompt**: Displays current vs. recommended settings
3. **Wait**: Gives ye 30 seconds to decide
4. **Apply**: Updates NODE_OPTIONS if ye consent

**Example Session**:

```bash
$ amplihack

============================================================
Memory Configuration Update
============================================================
System RAM: 64 GB
Current limit: 4096 MB
Recommended limit: 16384 MB
============================================================

Update NODE_OPTIONS with recommended limit? (y/n): y

Memory configuration updated successfully.
NODE_OPTIONS: --max-old-space-size=16384

[amplihack continues launching...]
```

### Non-Interactive Mode (CI/CD)

When runnin' in automated environments:

- **No Prompt**: Skips user input entirely
- **Auto-Accept**: Applies recommended settings by default
- **Silent**: Continues without delay

**Detected In**:
- GitHub Actions
- GitLab CI
- Jenkins
- Docker containers
- Any environment without stdin

**Example CI/CD Run**:

```bash
# CI environment detected - applying recommended memory settings
Memory configuration: 8192 MB (auto-applied in CI)
NODE_OPTIONS: --max-old-space-size=8192
```

### Timeout Protection

If ye don't respond within 30 seconds:

- **Interactive**: Defaults to "yes" (applies recommended settings)
- **Timeout Message**: "No response within 30 seconds, applying recommended settings."
- **Continues**: Launcher proceeds normally

**Why 30 Seconds?**

- Balances user convenience with workflow momentum
- Prevents indefinite hangs in edge cases
- Matches typical user decision time

## Configuration Options

### Environment Variables

Ye can control consent behavior through environment variables:

```bash
# Force accept memory configuration (skip prompt)
export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
amplihack

# Force reject memory configuration (skip prompt)
export AMPLIHACK_MEMORY_AUTO_REJECT=true
amplihack

# Custom timeout (in seconds)
export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60
amplihack
```

### Programmatic Usage

If ye be integrin' amplihack into yer own tools:

```python
from amplihack.launcher.memory_config import prompt_user_consent

# Basic usage
config = {
    'system_ram_gb': 16,
    'current_limit_mb': None,
    'recommended_limit_mb': 8192
}

consent = prompt_user_consent(config)
# Returns: True if consented, False otherwise

# With timeout (default 30s)
# Automatically handles non-interactive detection
# Returns None if non-interactive, True/False if interactive
```

## Memory Calculation Formula

The recommended memory limit follows this formula:

```
N = max(8192, total_ram_mb ÷ 4)
```

Capped at 32768 MB (32 GB) maximum.

**Examples**:

| System RAM | Recommended Limit | Reasoning |
|-----------|------------------|-----------|
| 4 GB | 8192 MB (8 GB) | Minimum safe limit |
| 16 GB | 8192 MB (8 GB) | Quarter of RAM (4 GB) < minimum |
| 32 GB | 8192 MB (8 GB) | Quarter of RAM equals minimum |
| 64 GB | 16384 MB (16 GB) | Quarter of RAM |
| 128 GB | 32768 MB (32 GB) | Capped at maximum |

## Behavior by Environment

### Local Development (Interactive)

```bash
$ amplihack
# Prompt appears, 30-second timeout
# User responds: y/n
# Settings applied based on response
```

### CI/CD Pipeline (Non-Interactive)

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run amplihack
        run: amplihack test
        # No prompt - auto-applies settings
        # Continues immediately
```

### Docker Container (Non-Interactive)

```dockerfile
FROM python:3.11
RUN pip install amplihack
CMD ["amplihack"]
# Detects non-interactive stdin
# Auto-applies recommended settings
```

### SSH Session (Interactive)

```bash
$ ssh user@server
$ amplihack
# Prompt appears normally
# 30-second timeout applies
# User can respond via SSH terminal
```

## Troubleshooting

### Prompt Never Appears

**Symptom**: Memory settings applied without askin'

**Cause**: System detected non-interactive environment

**Solutions**:

1. Verify stdin is connected:
   ```bash
   test -t 0 && echo "Interactive" || echo "Non-interactive"
   ```

2. Check environment variables:
   ```bash
   env | grep AMPLIHACK_MEMORY
   ```

3. Force interactive mode:
   ```bash
   export AMPLIHACK_FORCE_INTERACTIVE=true
   amplihack
   ```

### Timeout Too Short

**Symptom**: Prompt times out before ye can respond

**Cause**: 30-second default insufficient

**Solutions**:

1. Increase timeout:
   ```bash
   export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60
   amplihack
   ```

2. Pre-configure yer preference:
   ```bash
   export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
   amplihack
   ```

### Memory Settings Not Applied

**Symptom**: Responded "yes" but NODE_OPTIONS unchanged

**Cause**: Permissions issue or environment override

**Solutions**:

1. Check current NODE_OPTIONS:
   ```bash
   echo $NODE_OPTIONS
   ```

2. Verify memory config:
   ```python
   from amplihack.launcher.memory_config import get_memory_config
   config = get_memory_config()
   print(config)
   ```

3. Manually set if needed:
   ```bash
   export NODE_OPTIONS="--max-old-space-size=8192"
   amplihack
   ```

### Prompt Hangs Indefinitely

**Symptom**: Timeout protection not workin'

**Cause**: Edge case in input detection

**Solutions**:

1. Force non-interactive mode:
   ```bash
   export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
   amplihack
   ```

2. Skip memory configuration:
   ```bash
   export AMPLIHACK_SKIP_MEMORY_CONFIG=true
   amplihack
   ```

## Platform Compatibility

### Supported Platforms

| Platform | Interactive | Non-Interactive | Timeout |
|----------|------------|----------------|---------|
| Linux | ✅ | ✅ | ✅ |
| macOS | ✅ | ✅ | ✅ |
| Windows | ✅ | ✅ | ✅ |
| WSL | ✅ | ✅ | ✅ |
| Docker | ❌ | ✅ | N/A |
| GitHub Actions | ❌ | ✅ | N/A |
| GitLab CI | ❌ | ✅ | N/A |

### Platform-Specific Notes

**Windows**:
- Uses `select` module for timeout on Windows
- Fully compatible with Command Prompt and PowerShell
- Works in Git Bash and WSL terminals

**macOS**:
- Uses `select` module for stdin monitoring
- Compatible with Terminal.app and iTerm2
- Works via SSH sessions

**Linux**:
- Uses `select` module for stdin monitoring
- Compatible with all major terminals
- Works in tmux and screen sessions

## Integration Examples

### GitHub Actions Workflow

```yaml
name: Test with amplihack
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install amplihack
        run: pip install amplihack

      - name: Run tests
        run: amplihack test
        # Non-interactive detection automatic
        # Memory settings auto-applied
```

### Docker Compose

```yaml
version: '3.8'
services:
  amplihack:
    image: python:3.11
    volumes:
      - .:/workspace
    working_dir: /workspace
    environment:
      - AMPLIHACK_MEMORY_AUTO_ACCEPT=true
    command: sh -c "pip install amplihack && amplihack"
```

### Custom Script

```bash
#!/bin/bash
# setup-amplihack.sh

# Configure memory settings for CI
if [ -n "$CI" ]; then
    export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
    echo "CI detected - auto-accepting memory config"
fi

# Set custom timeout for interactive mode
if [ -t 0 ]; then
    export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60
    echo "Interactive mode - 60s timeout"
fi

# Launch amplihack
amplihack "$@"
```

## Technical Details

### Non-Interactive Detection

The system detects non-interactive environments by checkin':

1. **stdin availability**: Is standard input connected?
2. **Terminal presence**: Is this a TTY?
3. **CI environment variables**: `CI`, `GITHUB_ACTIONS`, `GITLAB_CI`, etc.

```python
import sys
import os

def is_interactive():
    # Check stdin is connected to terminal
    if not sys.stdin.isatty():
        return False

    # Check for CI environment
    ci_vars = ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_HOME']
    if any(os.getenv(var) for var in ci_vars):
        return False

    return True
```

### Timeout Implementation

Uses platform-appropriate timeout mechanisms:

**Unix/Linux/macOS**:
```python
import select

def prompt_with_timeout(timeout_seconds=30):
    print("Prompt message: ", end='', flush=True)

    # Wait for input with timeout
    ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)

    if ready:
        return input().strip().lower()
    else:
        return None  # Timeout occurred
```

**Windows**:
```python
import msvcrt
import time

def prompt_with_timeout(timeout_seconds=30):
    print("Prompt message: ", end='', flush=True)

    start_time = time.time()
    response = ""

    while True:
        if msvcrt.kbhit():
            char = msvcrt.getwche()
            if char == '\r':  # Enter key
                return response.strip().lower()
            response += char

        if time.time() - start_time > timeout_seconds:
            return None  # Timeout occurred

        time.sleep(0.1)
```

### Default Value Logic

When timeout occurs or non-interactive detected:

```python
def get_default_consent(config):
    """Determine default consent behavior"""

    # In CI/non-interactive: always accept
    if not is_interactive():
        return True

    # Timeout in interactive: accept recommended
    # (User had opportunity to respond)
    return True
```

**Reasoning**:
- **Non-interactive**: Automated systems expect smooth operation
- **Timeout**: User aware but chose not to respond = implicit consent
- **Safety**: Recommended settings are conservative and safe

## See Also

- [Memory Management Overview](../reference/memory-management.md) - Complete memory system documentation
- [Configuration Guide](../howto/configure-memory.md) - Step-by-step configuration
- [Launcher Architecture](../reference/launcher-architecture.md) - How the launcher works
- [Environment Variables](../reference/environment-variables.md) - All configuration options

---

**Last Updated**: 2026-01-17
**Version**: 1.0.0
**Status**: Production
