# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

#### BREAKING CHANGE: Shell Injection Prevention in ProcessManager

**Impact**: ProcessManager.run_command() no longer uses `shell=True` on any platform.

**What Changed**:
- `ProcessManager.run_command()` now NEVER uses `shell=True` (previously used on Windows for npm/npx/node)
- Windows npm/npx/node commands now resolved via `shutil.which()` instead of shell interpretation
- All commands passed as `list[str]` with no string interpolation

**Migration Required**:

If your code passes commands as strings to ProcessManager:

```python
# BEFORE (will break)
ProcessManager.run_command("npm install express")

# AFTER (correct)
ProcessManager.run_command(["npm", "install", "express"])
```

If your code relies on shell features (pipes, wildcards, environment variable expansion):

```python
# BEFORE (will break - shell features no longer work)
ProcessManager.run_command(["echo", "$HOME/*.txt"])

# AFTER (use Python alternatives)
import os
import glob
home = os.environ.get("HOME")
files = glob.glob(f"{home}/*.txt")
for f in files:
    ProcessManager.run_command(["echo", f])
```

**Why This Change**:
- Shell injection is a critical security vulnerability (CWE-78)
- Previous implementation allowed arbitrary command execution through user input
- Example attack: `ProcessManager.run_command(["npm", "install", f"{user_package}"])` where `user_package = "; rm -rf /"`

**What Breaks**:
1. Commands passed as single strings instead of lists
2. Shell features (pipes `|`, wildcards `*`, variable expansion `$VAR`, command substitution `` `cmd` ``)
3. Batch scripts that relied on shell interpretation

**Verification**:
```python
# Safe command execution (injection attempt fails safely)
from amplihack.utils.process import ProcessManager

# This is now safe - the semicolon is treated as a literal package name
result = ProcessManager.run_command(["npm", "install", "; rm -rf /"])
# npm tries to install package named "; rm -rf /" (which fails), but shell injection does NOT execute
```

**Testing**:
- Added comprehensive security test suite in `tests/unit/test_process_security.py`
- Tests verify shell injection vectors are neutralized
- Windows CI matrix validates npm/npx/node resolution on Windows Server 2019/2022

**Related Issues**: #2010

**Documentation**:
- [Shell Injection Prevention Guide](docs/security/shell-injection-prevention.md)
- [Security Testing Guide](docs/security/SECURITY_TESTING_GUIDE.md)
- [Windows CI Matrix Guide](docs/reference/windows-ci-matrix.md)

---

## Historical Entries

(Previous changelog entries would be listed below)
