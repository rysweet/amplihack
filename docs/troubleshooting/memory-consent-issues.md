# Troubleshooting Memory Consent Issues

Quick solutions fer common problems with memory configuration consent prompts.

## Quick Diagnosis

Run this diagnostic command:

```bash
python3 -c "
from amplihack.launcher.memory_config import get_memory_config
import json
config = get_memory_config()
print(json.dumps(config, indent=2))
"
```

Expected output:

```json
{
  "system_ram_gb": 16,
  "recommended_limit_mb": 8192,
  "current_limit_mb": 4096,
  "node_options": "--max-old-space-size=8192",
  "user_consent": true
}
```

---

## Issue: Prompt Hangs Forever

### Symptoms

- Prompt appears but timeout never triggers
- Process doesn't respond to Ctrl+C
- Terminal hangs indefinitely

### Causes

1. **Edge case in input detection**
2. **Platform-specific stdin issue**
3. **Terminal emulator compatibility**

### Solutions

#### Solution 1: Force Non-Interactive Mode

```bash
export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
amplihack
```

#### Solution 2: Skip Memory Configuration

```bash
export AMPLIHACK_SKIP_MEMORY_CONFIG=true
amplihack
```

#### Solution 3: Check Platform Compatibility

```python
# Test stdin detection
import sys
print(f"stdin is TTY: {sys.stdin.isatty()}")
print(f"stdin fileno: {sys.stdin.fileno()}")

# Expected: stdin is TTY: True
```

If `stdin.isatty()` returns False in an interactive terminal, yer terminal emulator may have compatibility issues.

**Workaround**:

```bash
# Force interactive mode
export AMPLIHACK_FORCE_INTERACTIVE=true
amplihack
```

---

## Issue: Prompt Never Appears

### Symptoms

- Memory settings applied without askin'
- No prompt displayed
- Settings changed without consent

### Causes

1. **Non-interactive environment detected**
2. **Auto-accept flag set**
3. **CI/CD environment variables present**

### Solutions

#### Solution 1: Verify Environment

```bash
# Check if running in non-interactive mode
test -t 0 && echo "Interactive" || echo "Non-interactive"
```

If "Non-interactive", check why:

```bash
# Check for CI environment variables
env | grep -E 'CI|GITHUB_ACTIONS|GITLAB_CI|JENKINS|TRAVIS'
```

#### Solution 2: Check Environment Variables

```bash
# Look for auto-accept settings
env | grep AMPLIHACK_MEMORY
```

If ye see `AMPLIHACK_MEMORY_AUTO_ACCEPT=true`, that be why.

**To enable prompting**:

```bash
unset AMPLIHACK_MEMORY_AUTO_ACCEPT
amplihack
```

#### Solution 3: Force Interactive Mode

```bash
export AMPLIHACK_FORCE_INTERACTIVE=true
amplihack
```

---

## Issue: Timeout Too Short

### Symptoms

- Prompt disappears before ye can respond
- "No response within 30 seconds" message
- Settings applied without yer input

### Causes

1. **Default 30-second timeout too short**
2. **Slow to read/decide**
3. **Distraction during prompt**

### Solutions

#### Solution 1: Increase Timeout

```bash
# Set to 2 minutes
export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=120
amplihack
```

#### Solution 2: Make Permanent

Add to yer shell profile:

```bash
# ~/.bashrc or ~/.zshrc
echo 'export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=120' >> ~/.bashrc
source ~/.bashrc
```

#### Solution 3: Pre-Configure Choice

If ye always want the same answer:

```bash
# Always accept
export AMPLIHACK_MEMORY_AUTO_ACCEPT=true

# Or always reject
export AMPLIHACK_MEMORY_AUTO_REJECT=true
```

---

## Issue: Settings Not Applied

### Symptoms

- Responded "yes" to prompt
- NODE_OPTIONS unchanged
- Memory limit still at old value

### Causes

1. **Permissions issue**
2. **Conflicting NODE_OPTIONS**
3. **Environment not propagated**

### Solutions

#### Solution 1: Check Current NODE_OPTIONS

```bash
echo $NODE_OPTIONS
```

If empty or different from expected:

```bash
# Manually set
export NODE_OPTIONS="--max-old-space-size=8192"
```

#### Solution 2: Verify Memory Config

```python
from amplihack.launcher.memory_config import get_memory_config
config = get_memory_config()
print(f"Recommended: {config['recommended_limit_mb']} MB")
print(f"NODE_OPTIONS: {config['node_options']}")
```

#### Solution 3: Check for Overrides

```bash
# Check if NODE_OPTIONS is set elsewhere
grep -r "NODE_OPTIONS" ~/.bashrc ~/.zshrc ~/.profile
```

Remove conflictin' settings.

---

## Issue: Wrong Memory Limit Calculated

### Symptoms

- System has 64 GB RAM but only recommended 8 GB
- Calculation doesn't match formula
- Warning about low RAM on high-RAM system

### Causes

1. **RAM detection failure**
2. **Incorrect RAM reporting**
3. **Formula misunderstanding**

### Solutions

#### Solution 1: Verify RAM Detection

```python
from amplihack.launcher.memory_config import detect_system_ram_gb
ram_gb = detect_system_ram_gb()
print(f"Detected RAM: {ram_gb} GB")
```

If None or wrong value:

```bash
# Check system RAM manually
# Linux
free -h

# macOS
sysctl hw.memsize

# Windows
wmic ComputerSystem get TotalPhysicalMemory
```

#### Solution 2: Understand the Formula

Formula: `N = max(8192, total_ram_mb ÷ 4)` capped at 32768 MB

Examples:

| System RAM | Quarter RAM | Max(8192, Quarter) | Final (Capped) |
|-----------|-------------|-------------------|----------------|
| 16 GB | 4096 MB | 8192 MB | 8192 MB |
| 32 GB | 8192 MB | 8192 MB | 8192 MB |
| 64 GB | 16384 MB | 16384 MB | 16384 MB |
| 128 GB | 32768 MB | 32768 MB | 32768 MB |
| 256 GB | 65536 MB | 65536 MB | **32768 MB** (capped) |

#### Solution 3: Manual Override

If automatic detection be wrong:

```bash
# Set specific memory limit
export NODE_OPTIONS="--max-old-space-size=16384"
export AMPLIHACK_SKIP_MEMORY_CONFIG=true
amplihack
```

---

## Issue: Prompt Appears in CI/CD

### Symptoms

- CI/CD pipeline hangs waitin' fer input
- Build times out
- Job fails with "no input available"

### Causes

1. **Missing auto-accept flag**
2. **Interactive mode forced**
3. **Environment detection failure**

### Solutions

#### Solution 1: Add Auto-Accept to CI Config

**GitHub Actions**:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      AMPLIHACK_MEMORY_AUTO_ACCEPT: true
    steps:
      - run: amplihack
```

**GitLab CI**:

```yaml
variables:
  AMPLIHACK_MEMORY_AUTO_ACCEPT: "true"

test:
  script:
    - amplihack
```

**Jenkins**:

```groovy
environment {
    AMPLIHACK_MEMORY_AUTO_ACCEPT = 'true'
}
```

#### Solution 2: Check for Force Interactive

```bash
# In CI config, ensure this is NOT set:
env | grep AMPLIHACK_FORCE_INTERACTIVE
```

If present, remove it.

#### Solution 3: Verify CI Detection

CI environments should be auto-detected. Check fer these variables:

```bash
env | grep -E 'CI|GITHUB_ACTIONS|GITLAB_CI|JENKINS_HOME'
```

If none present, yer CI environment ain't recognized.

**Workaround**:

```bash
# Set CI flag manually
export CI=true
amplihack
```

---

## Issue: Different Behavior on Different Platforms

### Symptoms

- Works on macOS but not Linux
- Windows shows different prompts
- Timeout works locally but not in Docker

### Causes

1. **Platform-specific implementation differences**
2. **Terminal compatibility issues**
3. **Container stdin handling**

### Solutions

#### Solution 1: Platform-Specific Configuration

**Create platform-aware wrapper**:

```bash
#!/bin/bash
# amplihack-platform-wrapper.sh

case "$(uname -s)" in
    Darwin*)
        # macOS - use defaults
        ;;
    Linux*)
        # Linux - increase timeout
        export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60
        ;;
    CYGWIN*|MINGW*|MSYS*)
        # Windows - auto-accept
        export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
        ;;
esac

exec amplihack "$@"
```

#### Solution 2: Docker-Specific Setup

```dockerfile
FROM python:3.11
RUN pip install amplihack

# Non-interactive by default in containers
ENV AMPLIHACK_MEMORY_AUTO_ACCEPT=true

CMD ["amplihack"]
```

#### Solution 3: SSH Session Handling

When runnin' via SSH:

```bash
# Ensure proper terminal allocation
ssh -t user@host amplihack
```

The `-t` flag forces pseudo-terminal allocation, ensurin' interactive prompts work.

---

## Issue: Prompt in Background Job

### Symptoms

- Started amplihack in background (`amplihack &`)
- Process stopped waitin' fer input
- Can't bring to foreground

### Causes

1. **Background processes can't read stdin**
2. **Job control suspends on input**

### Solutions

#### Solution 1: Auto-Accept for Background Jobs

```bash
# Run in background with auto-accept
AMPLIHACK_MEMORY_AUTO_ACCEPT=true amplihack &
```

#### Solution 2: Use nohup

```bash
# Run detached with auto-accept
nohup amplihack > amplihack.log 2>&1 &
```

Ensure auto-accept is set:

```bash
export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
nohup amplihack > amplihack.log 2>&1 &
```

---

## Diagnostic Commands

### Full System Check

```bash
#!/bin/bash
# amplihack-diag.sh - Full diagnostic check

echo "=== Environment Check ==="
env | grep AMPLIHACK_MEMORY

echo "=== stdin Check ==="
test -t 0 && echo "Interactive" || echo "Non-interactive"

echo "=== RAM Detection ==="
python3 -c "from amplihack.launcher.memory_config import detect_system_ram_gb; print(f'{detect_system_ram_gb()} GB')"

echo "=== Current NODE_OPTIONS ==="
echo "$NODE_OPTIONS"

echo "=== Memory Config Test ==="
python3 -c "
from amplihack.launcher.memory_config import get_memory_config
import json
config = get_memory_config()
print(json.dumps(config, indent=2))
"
```

Run it:

```bash
chmod +x amplihack-diag.sh
./amplihack-diag.sh
```

---

## Getting Help

If these solutions don't work:

1. **Check version**:
   ```bash
   amplihack --version
   # Ensure >= 0.9.0
   ```

2. **Enable debug mode**:
   ```bash
   AMPLIHACK_DEBUG=true amplihack
   ```

3. **Collect diagnostic info**:
   ```bash
   # Save output
   ./amplihack-diag.sh > diagnostic-output.txt 2>&1
   ```

4. **Report issue** with:
   - Platform (OS and version)
   - Terminal emulator
   - amplihack version
   - Diagnostic output
   - Steps to reproduce

---

## See Also

- [Memory Configuration Consent Feature](../features/memory-consent-prompt.md) - Complete feature documentation
- [How to Configure Memory Consent](../howto/configure-memory-consent.md) - Configuration guide
- [Memory Management Overview](../reference/memory-management.md) - System architecture
- [Environment Variables](../reference/environment-variables.md) - All configuration options

---

**Last Updated**: 2026-01-17
**Version**: 1.0.0
**Status**: Production
