# How to Configure Memory Consent Behavior

Step-by-step guide fer customizin' how amplihack handles memory configuration consent prompts.

## Quick Reference

| Task                        | Command                                     |
| --------------------------- | ------------------------------------------- |
| Skip prompt in CI/CD        | `export AMPLIHACK_MEMORY_AUTO_ACCEPT=true`  |
| Disable auto-updates        | `export AMPLIHACK_MEMORY_AUTO_REJECT=true`  |
| Change timeout              | `export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60` |
| Force interactive mode      | `export AMPLIHACK_FORCE_INTERACTIVE=true`   |
| Skip memory config entirely | `export AMPLIHACK_SKIP_MEMORY_CONFIG=true`  |

## Common Scenarios

### Scenario 1: Always Auto-Accept in CI/CD

**Goal**: Yer CI/CD pipeline should never wait fer user input.

**Steps**:

1. Add environment variable to yer CI configuration:

   ```yaml
   # GitHub Actions
   env:
     AMPLIHACK_MEMORY_AUTO_ACCEPT: true
   ```

   ```yaml
   # GitLab CI
   variables:
     AMPLIHACK_MEMORY_AUTO_ACCEPT: "true"
   ```

   ```groovy
   // Jenkins
   environment {
       AMPLIHACK_MEMORY_AUTO_ACCEPT = 'true'
   }
   ```

2. Verify the setting works:

   ```bash
   AMPLIHACK_MEMORY_AUTO_ACCEPT=true amplihack --version
   # Should complete without prompting
   ```

**Result**: No prompt appears, recommended settings applied automatically.

---

### Scenario 2: Increase Timeout for Slow Responders

**Goal**: Ye need more than 30 seconds to decide.

**Steps**:

1. Set custom timeout (in seconds):

   ```bash
   export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=120
   ```

2. Launch amplihack:

   ```bash
   amplihack
   ```

3. Ye now have 120 seconds to respond to the prompt.

**Permanent Setup** (add to yer shell profile):

```bash
# ~/.bashrc or ~/.zshrc
export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=120
```

**Result**: Prompt waits 120 seconds instead of default 30.

---

### Scenario 3: Disable Auto-Updates on Personal Machine

**Goal**: Ye want to keep current memory settings, no changes.

**Steps**:

1. Set rejection flag:

   ```bash
   export AMPLIHACK_MEMORY_AUTO_REJECT=true
   ```

2. Launch amplihack:

   ```bash
   amplihack
   ```

3. Memory configuration skipped, existing NODE_OPTIONS preserved.

**Permanent Setup**:

```bash
# ~/.bashrc or ~/.zshrc
export AMPLIHACK_MEMORY_AUTO_REJECT=true
```

**Result**: No prompt, no changes to memory settings.

---

### Scenario 4: Test Interactive Prompt in Docker

**Goal**: Force interactive mode even in Docker container.

**Steps**:

1. Create Dockerfile with interactive flag:

   ```dockerfile
   FROM python:3.11
   RUN pip install amplihack

   # Force interactive mode
   ENV AMPLIHACK_FORCE_INTERACTIVE=true

   CMD ["amplihack"]
   ```

2. Run container with stdin attached:

   ```bash
   docker build -t amplihack-test .
   docker run -it amplihack-test
   ```

3. Prompt appears even in Docker.

**Result**: Interactive prompt works in containerized environments.

---

### Scenario 5: Custom Default for Non-Interactive

**Goal**: In non-interactive mode, ye want to reject (not accept) by default.

**Steps**:

1. This requires code-level configuration. Create a wrapper script:

   ```bash
   #!/bin/bash
   # amplihack-wrapper.sh

   # Detect non-interactive mode
   if [ ! -t 0 ]; then
       # Non-interactive: reject updates
       export AMPLIHACK_MEMORY_AUTO_REJECT=true
   fi

   # Launch amplihack
   exec amplihack "$@"
   ```

2. Make executable:

   ```bash
   chmod +x amplihack-wrapper.sh
   ```

3. Use wrapper instead of direct amplihack:

   ```bash
   ./amplihack-wrapper.sh
   ```

**Result**: Non-interactive sessions reject updates; interactive sessions prompt normally.

---

## Advanced Configuration

### Per-Project Settings

Create a `.env` file in yer project:

```bash
# .env
AMPLIHACK_MEMORY_AUTO_ACCEPT=true
AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60
```

Load before runnin' amplihack:

```bash
export $(cat .env | xargs)
amplihack
```

Or use a tool like `direnv`:

```bash
# Install direnv
brew install direnv  # macOS
apt install direnv   # Ubuntu

# Create .envrc
echo 'export AMPLIHACK_MEMORY_AUTO_ACCEPT=true' > .envrc

# Allow direnv to load it
direnv allow

# Now amplihack picks up settings automatically
```

---

### Programmatic Configuration

If ye be buildin' tools that use amplihack:

```python
import os
from amplihack.launcher.memory_config import prompt_user_consent

# Set defaults programmatically
os.environ['AMPLIHACK_MEMORY_PROMPT_TIMEOUT'] = '45'

# Build configuration
config = {
    'system_ram_gb': 16,
    'current_limit_mb': None,
    'recommended_limit_mb': 8192
}

# Prompt with custom settings
consent = prompt_user_consent(config)

if consent:
    print("User consented to memory update")
    # Apply configuration
elif consent is None:
    print("Non-interactive mode detected")
    # Handle non-interactive case
else:
    print("User declined memory update")
    # Keep existing settings
```

---

### Environment Variable Priority

When multiple settings conflict, this be the priority order (highest to lowest):

1. `AMPLIHACK_SKIP_MEMORY_CONFIG` - Skip entirely
2. `AMPLIHACK_MEMORY_AUTO_REJECT` - Reject updates
3. `AMPLIHACK_MEMORY_AUTO_ACCEPT` - Accept updates
4. `AMPLIHACK_FORCE_INTERACTIVE` - Force prompting
5. Auto-detection - Default behavior

**Example**:

```bash
# These conflict - SKIP wins
export AMPLIHACK_SKIP_MEMORY_CONFIG=true
export AMPLIHACK_MEMORY_AUTO_ACCEPT=true

amplihack  # Memory config skipped entirely
```

---

## Testing Your Configuration

### Verify Environment Variables

```bash
# Check what's set
env | grep AMPLIHACK_MEMORY

# Expected output (example):
# AMPLIHACK_MEMORY_AUTO_ACCEPT=true
# AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60
```

### Test Prompt Behavior

```bash
# Test with verbose output
AMPLIHACK_DEBUG=true amplihack

# Watch for messages like:
# "Non-interactive mode detected - auto-accepting"
# "Timeout: 60 seconds"
# "User consent: True"
```

### Verify Memory Settings Applied

```bash
# After running amplihack, check NODE_OPTIONS
echo $NODE_OPTIONS

# Should show:
# --max-old-space-size=8192
```

---

## Troubleshooting

### Problem: Environment Variable Ignored

**Symptom**: Set `AMPLIHACK_MEMORY_AUTO_ACCEPT=true` but still prompted.

**Check**:

1. Verify variable is exported:

   ```bash
   echo $AMPLIHACK_MEMORY_AUTO_ACCEPT
   ```

2. Ensure it's set before launching:

   ```bash
   # WRONG - variable not in environment
   AMPLIHACK_MEMORY_AUTO_ACCEPT=true
   amplihack

   # RIGHT - exported to environment
   export AMPLIHACK_MEMORY_AUTO_ACCEPT=true
   amplihack
   ```

3. Check for typos in variable name (case-sensitive).

---

### Problem: Timeout Not Working

**Symptom**: Set longer timeout but still defaults after 30 seconds.

**Check**:

1. Verify timeout value is numeric:

   ```bash
   # WRONG
   export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=sixty

   # RIGHT
   export AMPLIHACK_MEMORY_PROMPT_TIMEOUT=60
   ```

2. Check for platform compatibility (Windows vs. Unix).

3. Verify no other process is interfering with stdin.

---

### Problem: Still Prompts in CI/CD

**Symptom**: CI/CD pipeline waits fer input despite auto-accept setting.

**Check**:

1. Verify environment variable in CI config:

   ```yaml
   # GitHub Actions - correct placement
   jobs:
     test:
       runs-on: ubuntu-latest
       env:
         AMPLIHACK_MEMORY_AUTO_ACCEPT: true # ✓ Correct
       steps:
         - run: amplihack
   ```

2. Check fer overridin' settings in yer code.

3. Verify amplihack version supports this feature:
   ```bash
   amplihack --version
   # Should be >= 0.9.0
   ```

---

## See Also

- [Memory Configuration Consent Feature](../features/memory-consent-prompt.md) - Complete feature documentation
- [Memory Management Overview](../reference/memory-management.md) - How memory system works
- [Environment Variables Reference](../reference/environment-variables.md) - All available variables
- [CI/CD Integration Guide](../howto/ci-cd-setup.md) - Complete CI/CD setup

---

**Last Updated**: 2026-01-17
**Version**: 1.0.0
**Status**: Production
