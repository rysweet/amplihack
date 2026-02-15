# Security Code Review Checklist

**Use this checklist when reviewing pre-commit manager code**

## Command Execution Review

### Subprocess Calls

- [ ] All `subprocess.run()` calls use list form: `["cmd", "arg"]`
- [ ] NO `shell=True` anywhere in the code
- [ ] All subprocess calls have `timeout` parameter (recommended: 30s)
- [ ] `cwd` parameter is validated before use
- [ ] Command arguments never come from unvalidated user input
- [ ] Error handling doesn't expose sensitive command details

**Check these files:**

- `precommit_installer.py` (lines 284-290, 164-169)
- Any new skill files that run external commands

**Test command:**

```bash
grep -n "shell=True" .claude/tools/amplihack/hooks/*.py
# Should return NOTHING
```

## Path Validation Review

### File Operations

- [ ] All file paths validated with `_validate_safe_path()` before use
- [ ] No direct concatenation: `path / user_input` without validation
- [ ] Symlink handling is secure (blocked or validated)
- [ ] Paths checked against forbidden directories
- [ ] Whitelist approach for allowed config files
- [ ] No `..` or `/` in user-provided filenames

**Check these patterns:**

```python
# ❌ BAD
config_file = self.project_root / user_input

# ✓ GOOD
config_file = self._validate_safe_path(
    self.project_root / user_input,
    self.project_root
)
```

**Test command:**

```bash
grep -n "project_root /" .claude/tools/amplihack/hooks/*.py
# Verify each has validation
```

## File Security Review

### File Writes

- [ ] All writes use atomic write pattern (temp + rename)
- [ ] File permissions set to 0o600 after creation
- [ ] Directory permissions set to 0o700
- [ ] `fsync()` called before rename
- [ ] Temp files created in same directory (same filesystem)
- [ ] Temp files cleaned up on error

**Check for:**

```python
# ❌ BAD
filepath.write_text(content)

# ✓ GOOD
self._atomic_write(filepath, content)
filepath.chmod(0o600)
```

### File Reads

- [ ] File locking used for concurrent access scenarios
- [ ] File size limits checked before reading
- [ ] Binary files not treated as text
- [ ] Permission errors handled gracefully

**Test command:**

```bash
# Check file permissions after creation
stat -c '%a' .claude/.precommit_preference
# Should be 600
```

## Input Validation Review

### User Inputs

- [ ] All external inputs validated before use
- [ ] Whitelist approach used (not blacklist)
- [ ] Length limits enforced
- [ ] Character set restrictions applied
- [ ] JSON parsing uses safe methods
- [ ] YAML parsing uses `safe_load()` not `load()`

**Critical inputs to validate:**

- Environment variables (`AMPLIHACK_AUTO_PRECOMMIT`)
- Preference file contents (JSON)
- Config file paths
- Template names
- Template variables

**Check for:**

```python
# ❌ BAD
data = yaml.load(config_file.read_text())

# ✓ GOOD
data = yaml.safe_load(config_file.read_text())
```

## Template Security Review

### Template Engine

- [ ] Using `string.Template` NOT `jinja2.Template`
- [ ] Template variables are whitelisted
- [ ] Template files come from trusted location only
- [ ] No user-provided template strings evaluated
- [ ] Variable values sanitized before substitution

**Check imports:**

```python
# ❌ BAD
from jinja2 import Template

# ✓ GOOD
from string import Template
```

**Test command:**

```bash
grep -n "from jinja2" .claude/tools/amplihack/hooks/*.py
# Should return NOTHING
```

## Configuration Security Review

### Config File Handling

- [ ] Config validation before installation
- [ ] User confirmation for NEW installations
- [ ] Audit logging of installations
- [ ] Config hash stored in audit log
- [ ] Size limits enforced (max 1MB)
- [ ] Structure validation (must have 'repos')

**User confirmation required when:**

- Installing hooks for first time
- Config has changed since last install
- Hooks appear corrupted

**Never require confirmation:**

- Re-installing same config
- Auto-repair of corrupted hooks

## Error Handling Review

### Fail-Secure Patterns

- [ ] Security exceptions always deny access
- [ ] Unknown errors fail to secure state
- [ ] Error messages don't leak sensitive info
- [ ] No secrets in log messages
- [ ] Stack traces sanitized in production
- [ ] User gets actionable error messages

**Check error handling:**

```python
# ✓ GOOD
try:
    result = risky_operation()
except SecurityError:
    log("Security violation", "ERROR")
    return False  # Fail secure
except Exception:
    log("Unknown error", "ERROR")
    return False  # Fail secure
```

## Environment Security Review

### Environment Variables

- [ ] Values validated against whitelist
- [ ] Case-insensitive comparison
- [ ] Invalid values treated as unset
- [ ] Never passed directly to shell
- [ ] Logged when invalid values found

**Whitelist:**

- `AMPLIHACK_AUTO_PRECOMMIT`: `0, 1, false, true, no, yes, off, on`

## Directory Security Review

### Forbidden Directories

- [ ] Check prevents operation in system dirs
- [ ] Forbidden list includes: `/root`, `/etc`, `/usr`, `/bin`, `/sbin`, `/tmp`, `/var`
- [ ] Both exact match and parent match checked
- [ ] Clear error message when blocked
- [ ] Metric logged for blocked attempts

**Test:**

```bash
cd /tmp && python -m hooks.precommit_installer
# Should refuse to operate
```

## Logging and Audit Review

### Security Logging

- [ ] All installations logged with timestamp
- [ ] Config hash included in audit log
- [ ] Security violations logged
- [ ] Log file has secure permissions (0o600)
- [ ] No secrets in logs
- [ ] Logs rotated/limited in size

**Check log locations:**

- `.claude/runtime/logs/precommit_installs.log`
- `.claude/runtime/logs/security_audit.log`

## Testing Review

### Security Tests Present

- [ ] Command injection tests
- [ ] Path traversal tests
- [ ] File permission tests
- [ ] Input validation tests
- [ ] Race condition tests
- [ ] Symlink attack tests
- [ ] Fuzzing tests for malformed input

**Minimum test coverage:**

- Command injection: 3+ test cases
- Path traversal: 5+ test cases
- File operations: 4+ test cases
- Input validation: 6+ test cases

## Code Patterns to Reject

### Automatic Rejection Triggers

**REJECT if code contains:**

```python
# 1. Shell injection risk
subprocess.run(..., shell=True)
subprocess.Popen(..., shell=True)
os.system(...)

# 2. Dangerous template engine
from jinja2 import Template

# 3. Unsafe YAML loading
yaml.load(...)  # Must be safe_load

# 4. Unvalidated path operations
some_path / user_input  # Without prior validation

# 5. World-readable files
chmod(0o644)  # Others can read
chmod(0o666)  # Others can read/write

# 6. Non-atomic writes
filepath.write_text(content)  # Race condition risk

# 7. Unvalidated environment variables
os.environ.get("VAR")  # Without validation
```

## Sign-off Checklist

**Before approving PR:**

### Code Review

- [ ] All subprocess calls use list form (no shell=True)
- [ ] All paths validated before use
- [ ] All file operations use atomic writes
- [ ] All files have secure permissions (0o600/0o700)
- [ ] string.Template used (not Jinja2)
- [ ] All inputs validated
- [ ] Error handling fails secure
- [ ] No secrets in logs or error messages

### Testing

- [ ] All security tests passing
- [ ] Command injection tests included
- [ ] Path traversal tests included
- [ ] File permission tests included
- [ ] Input validation tests included
- [ ] Test coverage > 80% for security-critical code

### Documentation

- [ ] Security mitigations documented in code comments
- [ ] Threat model understood by team
- [ ] Security testing documented

### Deployment

- [ ] Audit logging operational
- [ ] Metrics collection working
- [ ] Rollback plan exists

## Review Notes Template

```markdown
## Security Review - [Date]

**Reviewer:** [Name]
**Files Reviewed:** [List]

### Command Execution

- [ ] ✓ No shell=True found
- [ ] ✓ All subprocess calls have timeout
- [ ] ✓ All cwd parameters validated

### Path Validation

- [ ] ✓ All paths validated before use
- [ ] ✓ Symlink handling secure
- [ ] ✓ Forbidden directories blocked

### File Security

- [ ] ✓ Atomic writes used
- [ ] ✓ Permissions set to 0o600
- [ ] ✓ File locking implemented

### Input Validation

- [ ] ✓ Whitelist approach used
- [ ] ✓ Length limits enforced
- [ ] ✓ Character restrictions applied

### Template Security

- [ ] ✓ string.Template used
- [ ] ✓ No Jinja2 with user content
- [ ] ✓ Template variables whitelisted

### Testing

- [ ] ✓ Security tests passing
- [ ] ✓ Coverage > 80%
- [ ] ✓ Attack scenarios tested

### Issues Found

[List any security issues]

### Recommendation

- [ ] APPROVE - No security issues
- [ ] REQUEST CHANGES - Issues must be fixed
- [ ] BLOCK - Critical security issues

**Signature:** [Name], [Date]
```

## Quick Reference Commands

```bash
# Find security issues
grep -r "shell=True" .claude/
grep -r "from jinja2" .claude/
grep -r "yaml.load(" .claude/

# Check file permissions
find .claude -type f -exec stat -c '%a %n' {} \; | grep -v 600

# Run security tests
python -m pytest .claude/tools/amplihack/hooks/tests/ -k security

# Check audit logs
cat .claude/runtime/logs/security_audit.log
cat .claude/runtime/logs/precommit_installs.log
```

## Resources

- **Full Requirements**: `.claude/docs/SECURITY_REQUIREMENTS.md`
- **Quick Summary**: `.claude/docs/SECURITY_SUMMARY.md`
- **Issue**: #2281
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/

---

**Remember:** If you're unsure about any security aspect, BLOCK the PR and escalate to security agent for review.
