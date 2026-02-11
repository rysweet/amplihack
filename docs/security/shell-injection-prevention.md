# Shell Injection Prevention Guide

## Overview

amplihack's ProcessManager prevents shell injection attacks by **never** using `shell=True` in subprocess calls. This guide explains the security fix, migration patterns, and best practices.

## Table of Contents

- [Security Background](#security-background)
- [What Changed](#what-changed)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)
- [Testing](#testing)

## Security Background

### What is Shell Injection?

Shell injection (CWE-78) occurs when untrusted input is passed to a shell for execution, allowing attackers to execute arbitrary commands.

```python
# VULNERABLE CODE (DO NOT USE)
user_input = "; rm -rf /"  # Attacker-controlled
subprocess.run(f"npm install {user_input}", shell=True)
# Result: npm install ; rm -rf /
# The semicolon terminates npm and executes rm -rf /
```

### Why `shell=True` is Dangerous

When `shell=True` is used, the command is passed to the system shell (`/bin/sh` on Unix, `cmd.exe` on Windows). The shell interprets special characters:

| Character | Behavior | Attack Example |
|-----------|----------|----------------|
| `;` | Command separator | `cmd1; malicious_cmd` |
| `\|` | Pipe output | `cmd1 \| malicious_cmd` |
| `&` | Background execution | `cmd1 & malicious_cmd` |
| `$()` | Command substitution | `$(malicious_cmd)` |
| `` ` `` | Command substitution | `` `malicious_cmd` `` |

### Real-World Impact

Shell injection is consistently in OWASP Top 10 and can lead to:

- Complete system compromise
- Data exfiltration
- Ransomware deployment
- Lateral movement in networks

## What Changed

### Previous Implementation (Vulnerable)

```python
def run_command(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Execute command."""
    kwargs = {"cwd": cwd, "env": env, "capture_output": capture_output, "text": True}

    # SECURITY ISSUE: shell=True on Windows
    if ProcessManager.is_windows() and command[0] in ["npm", "npx", "node"]:
        kwargs["shell"] = True  # ⚠️ DANGEROUS

    return subprocess.run(command, **kwargs)
```

**Problem**: On Windows, npm/npx/node commands used `shell=True`, enabling injection attacks.

### Current Implementation (Secure)

```python
def run_command(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Execute command safely without shell.

    Security:
        - NEVER uses shell=True (prevents shell injection)
        - On Windows, resolves full path to .cmd/.bat files using shutil.which()
        - Uses list[str] commands exclusively (no string interpolation)
    """
    kwargs: dict = {
        "cwd": cwd,
        "env": env,
        "capture_output": capture_output,
        "text": True,
    }

    # Windows: resolve npm/npx/node paths without shell
    if ProcessManager.is_windows() and command and command[0] in ["npm", "npx", "node"]:
        resolved_path = shutil.which(command[0])
        if resolved_path:
            command = [resolved_path] + command[1:]

    return subprocess.run(command, **kwargs)  # ✅ SAFE: No shell=True
```

**Solution**: Use `shutil.which()` to resolve Windows .cmd/.bat paths directly, avoiding shell interpretation.

## Migration Guide

### Pattern 1: Commands as Strings → Lists

**Before (BREAKS)**:
```python
ProcessManager.run_command("npm install express")
```

**After (CORRECT)**:
```python
ProcessManager.run_command(["npm", "install", "express"])
```

### Pattern 2: Shell Features → Python Alternatives

#### Pipes

**Before (BREAKS)**:
```python
ProcessManager.run_command(["cat", "file.txt", "|", "grep", "pattern"])
```

**After (CORRECT)**:
```python
# Use Python to connect processes
import subprocess

p1 = subprocess.Popen(["cat", "file.txt"], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["grep", "pattern"], stdin=p1.stdout, stdout=subprocess.PIPE)
p1.stdout.close()
output, _ = p2.communicate()
```

#### Wildcards

**Before (BREAKS)**:
```python
ProcessManager.run_command(["rm", "*.txt"])
```

**After (CORRECT)**:
```python
import glob
for file in glob.glob("*.txt"):
    ProcessManager.run_command(["rm", file])
```

#### Environment Variable Expansion

**Before (BREAKS)**:
```python
ProcessManager.run_command(["echo", "$HOME"])
```

**After (CORRECT)**:
```python
import os
home = os.environ.get("HOME", "/")
ProcessManager.run_command(["echo", home])
```

### Pattern 3: Dynamic User Input (Critical)

**Before (VULNERABLE)**:
```python
package_name = get_user_input()  # Could be "; rm -rf /"
ProcessManager.run_command(["npm", "install", package_name])
# With shell=True, this executes: npm install ; rm -rf /
```

**After (SAFE)**:
```python
package_name = get_user_input()  # Could be "; rm -rf /"
ProcessManager.run_command(["npm", "install", package_name])
# Without shell=True, npm tries to install package named "; rm -rf /"
# npm fails (invalid package name), but shell injection does NOT execute
```

**Additional Protection**:
```python
import re

def validate_package_name(name: str) -> bool:
    """Validate npm package name format."""
    # npm package names: lowercase letters, numbers, hyphens, underscores, @scope
    return bool(re.match(r'^(@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$', name))

package_name = get_user_input()
if not validate_package_name(package_name):
    raise ValueError(f"Invalid package name: {package_name}")

ProcessManager.run_command(["npm", "install", package_name])
```

## Best Practices

### 1. Always Use List Commands

```python
# ✅ CORRECT: List of strings
ProcessManager.run_command(["git", "commit", "-m", "message"])

# ❌ WRONG: Single string
ProcessManager.run_command("git commit -m message")
```

### 2. Never Concatenate User Input into Commands

```python
# ❌ DANGEROUS
user_branch = get_user_input()
ProcessManager.run_command(["git", "checkout", f"{user_branch}; rm -rf /"])

# ✅ SAFE (user input is separate argument)
user_branch = get_user_input()
ProcessManager.run_command(["git", "checkout", user_branch])
```

### 3. Validate Input Before Execution

```python
def safe_git_checkout(branch: str) -> None:
    """Checkout git branch with input validation."""
    # Validate branch name format
    if not re.match(r'^[a-zA-Z0-9/_-]+$', branch):
        raise ValueError(f"Invalid branch name: {branch}")

    # Safe to execute
    ProcessManager.run_command(["git", "checkout", branch])
```

### 4. Use Python Alternatives to Shell Features

| Shell Feature | Python Alternative |
|---------------|-------------------|
| Pipes (`\|`) | `subprocess.Popen` with `stdout=PIPE` |
| Wildcards (`*`) | `glob.glob()` |
| Variables (`$VAR`) | `os.environ.get()` |
| Conditionals | Python `if/else` |
| Loops | Python `for/while` |

## Testing

### Running Security Tests

```bash
# Run full security test suite
pytest tests/unit/test_process_security.py -v

# Run specific test class
pytest tests/unit/test_process_security.py::TestShellInjectionPrevention -v

# Test injection attack vectors
pytest tests/unit/test_process_security.py::TestShellInjectionAttackVectors -v
```

### Test Coverage

The security test suite verifies:

- `shell=True` is never used on any platform
- Windows npm/npx/node use `shutil.which()` resolution
- Shell injection payloads are passed as literal arguments
- Commands are always lists, never strings
- Empty command handling

### Example Test

```python
def test_injection_in_npm_install_argument():
    """Verify injection attempts in npm install arguments are safe."""
    with (
        patch.object(ProcessManager, "is_windows", return_value=True),
        patch("amplihack.utils.process.shutil.which", return_value="C:\\npm.cmd"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)

        # Attempt injection via package name
        ProcessManager.run_command(["npm", "install", "; rm -rf /"])

        # Verify shell=True was NOT used
        call_kwargs = mock_run.call_args.kwargs
        assert "shell" not in call_kwargs or call_kwargs.get("shell") is False

        # Verify malicious string passed as literal argument
        call_args = mock_run.call_args[0][0]
        assert "; rm -rf /" in call_args
```

## Related Documentation

- [Security Testing Guide](SECURITY_TESTING_GUIDE.md) - Comprehensive testing strategies
- [Windows CI Matrix Guide](../reference/windows-ci-matrix.md) - CI validation on Windows
- [Security API Reference](SECURITY_API_REFERENCE.md) - ProcessManager API documentation

## References

- [Python subprocess Security](https://docs.python.org/3/library/subprocess.html#security-considerations)
- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
