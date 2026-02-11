# How to Use Secure Subprocess Execution

This guide shows you how to safely execute subprocess commands in amplihack to prevent shell injection vulnerabilities (CWE-78).

## Quick Start

### ✅ DO: Use List Commands

```python
from amplihack.utils.process import ProcessManager

# CORRECT - Safe from shell injection
result = ProcessManager.run_command(["git", "status"])
result = ProcessManager.run_command(["npm", "install", "express"])
result = ProcessManager.run_command(["echo", "hello world"])
```

### ❌ DON'T: Use String Commands with shell=True

```python
import subprocess

# WRONG - Vulnerable to shell injection
subprocess.run("git status", shell=True)  # ❌ NEVER DO THIS
subprocess.run(f"git commit -m '{user_input}'", shell=True)  # ❌ CRITICAL VULNERABILITY
```

## Why This Matters

### The Vulnerability

When you use `shell=True`, special characters are interpreted by the shell:

```python
# Attacker provides: "file.txt; rm -rf /"
subprocess.run(f"cat {user_filename}", shell=True)
# Becomes: cat file.txt; rm -rf /
# Result: YOUR SYSTEM IS DELETED 💀
```

### The Fix

Without `shell=True`, special characters are literal arguments:

```python
# Attacker provides: "file.txt; rm -rf /"
ProcessManager.run_command(["cat", user_filename])
# Becomes: cat "file.txt; rm -rf /"
# Result: Safe - tries to read file literally named "file.txt; rm -rf /" ✅
```

## Common Patterns

### Pattern 1: Simple Command

```python
# Git status
result = ProcessManager.run_command(["git", "status"])
print(result.stdout)
```

### Pattern 2: Command with Arguments

```python
# Install npm package
result = ProcessManager.run_command(["npm", "install", "express", "--save"])
```

### Pattern 3: Command with User Input

```python
# SAFE - User input is a literal argument
user_file = input("Enter filename: ")
result = ProcessManager.run_command(["cat", user_file])
```

### Pattern 4: Windows npm/npx/node Commands

```python
# ProcessManager automatically resolves Windows .cmd paths
result = ProcessManager.run_command(["npm", "--version"])
# On Windows: Resolves to C:\Program Files\nodejs\npm.cmd
# On Unix: Uses npm from PATH
```

## Testing Your Code

### Unit Tests

```python
from unittest.mock import patch
from amplihack.utils.process import ProcessManager

def test_command_with_injection_attempt():
    """Verify injection attempts fail safely."""
    # Attempt injection - should be treated as literal
    result = ProcessManager.run_command(["echo", "test; echo pwned"])

    # Verify pwned command didn't execute
    assert "; echo pwned" in result.stdout  # Literal text
    assert "pwned\n" not in result.stdout  # Not executed separately
```

### Integration Tests

```python
import pytest
from amplihack.utils.process import ProcessManager

@pytest.mark.integration
def test_real_command_execution():
    """Test with actual command."""
    result = ProcessManager.run_command(["python", "--version"])
    assert result.returncode == 0
    assert "Python" in result.stdout
```

## Migrating Existing Code

### Step 1: Find Vulnerable Code

```bash
# Search for shell=True usage
rg "shell=True" --type py
```

### Step 2: Convert to List Format

```python
# BEFORE (VULNERABLE):
subprocess.run("git commit -m 'message'", shell=True)

# AFTER (SECURE):
ProcessManager.run_command(["git", "commit", "-m", "message"])
```

### Step 3: Handle Complex Commands

If your command uses shell features (pipes, wildcards):

```python
# BEFORE: Using shell pipe
subprocess.run("cat file.txt | grep error", shell=True)

# AFTER: Use Python instead
import subprocess
cat_result = ProcessManager.run_command(["cat", "file.txt"])
grep_result = ProcessManager.run_command(
    ["grep", "error"],
    input=cat_result.stdout,
    capture_output=True,
    text=True
)
```

## Common Mistakes

### Mistake 1: Using f-strings with shell=True

```python
# WRONG - f-string doesn't protect you
subprocess.run(f"echo {user_input}", shell=True)  # Still vulnerable!

# RIGHT - Use list arguments
ProcessManager.run_command(["echo", user_input])
```

### Mistake 2: Thinking Validation is Enough

```python
# WRONG - Validation is insufficient
if user_input.isalnum():  # Can still be bypassed
    subprocess.run(f"echo {user_input}", shell=True)

# RIGHT - Never use shell=True
ProcessManager.run_command(["echo", user_input])
```

### Mistake 3: Using shell=True for "Convenience"

```python
# WRONG - "I need wildcards"
subprocess.run("rm *.tmp", shell=True)

# RIGHT - Use glob module
import glob
import os
for tmpfile in glob.glob("*.tmp"):
    os.remove(tmpfile)
```

## Validation

### Check Your Code is Secure

```bash
# Run integration tests
pytest tests/integration/test_process_integration.py -v

# Verify no shell=True in your code
rg "shell=True" your_file.py && echo "❌ Found shell=True!" || echo "✅ Secure!"
```

## Further Reading

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [Python subprocess security](https://docs.python.org/3/library/subprocess.html#security-considerations)
- [Shell Injection Prevention Guide](../security/shell-injection-prevention.md) (comprehensive reference)

## Need Help?

- File an issue: https://github.com/rysweet/amplihack/issues
- Read the security guide: `docs/security/shell-injection-prevention.md`
- Check examples: `tests/integration/test_process_integration.py`
