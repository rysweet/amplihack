# Security Requirements Summary

**Quick reference for pre-commit manager security requirements**

## Critical Vulnerabilities (MUST FIX)

### 1. Command Injection

- **Risk**: Arbitrary code execution
- **Mitigation**:
  - ALWAYS use `["pre-commit", "install"]` list form
  - NEVER use `shell=True`
  - Validate `cwd` parameter before subprocess calls
  - Add timeout to all subprocess calls

### 2. Path Traversal

- **Risk**: Read/write files outside project
- **Mitigation**:
  - Validate all paths with `_validate_safe_path()`
  - Whitelist allowed config files
  - Block symlinks or validate they stay in project
  - Sanitize template names (remove `../`)

## High Vulnerabilities (SHOULD FIX)

### 3. File Write Security

- **Risk**: Data corruption, race conditions
- **Mitigation**:
  - Use atomic writes with temp file + rename
  - Set permissions to 0o600 (owner-only)
  - Use file locking for concurrent access

### 4. Configuration Validation

- **Risk**: Malicious hooks executing code
- **Mitigation**:
  - Use `yaml.safe_load()` (not `load()`)
  - Validate config structure
  - User confirmation before NEW installations
  - Log all installations with config hash

### 5. Template Injection

- **Risk**: Code execution via templates
- **Mitigation**:
  - Use `string.Template` ONLY (not Jinja2)
  - Whitelist template variables
  - Validate template names

## Medium Vulnerabilities (GOOD TO FIX)

### 6. Environment Variable Injection

- **Risk**: Modified command behavior
- **Mitigation**:
  - Whitelist allowed env var values
  - Never pass env vars to shell

### 7. Privilege Escalation

- **Risk**: Operations in system directories
- **Mitigation**:
  - Block operations in `/root`, `/etc`, `/tmp`, etc.
  - Validate git repository structure

## Implementation Checklist

### Before Writing Code

- [ ] Read full security requirements doc
- [ ] Understand each vulnerability
- [ ] Plan mitigations into design

### While Writing Code

- [ ] Validate ALL file paths before use
- [ ] Use list form for subprocess (no shell=True)
- [ ] Set timeouts on subprocess calls (30s)
- [ ] Use atomic writes for files
- [ ] Set permissions 0o600 for files
- [ ] Use string.Template (not Jinja2)
- [ ] Validate all user inputs

### Testing Phase

- [ ] Test command injection attacks
- [ ] Test path traversal attacks
- [ ] Test file permission checks
- [ ] Test race conditions
- [ ] Test malformed inputs

### Code Review

- [ ] No `shell=True` in code
- [ ] No Jinja2 with user content
- [ ] All paths validated
- [ ] All files have secure permissions
- [ ] Fail-secure error handling

## Quick Code Templates

### Safe Subprocess Call

```python
result = subprocess.run(
    ["pre-commit", "install"],  # List form
    timeout=30,                 # Always timeout
    shell=False,                # Never True
    capture_output=True,
    text=True,
    cwd=validated_path          # Pre-validated
)
```

### Safe Path Validation

```python
def _validate_safe_path(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    base_resolved = base.resolve()

    # Must be within base
    resolved.relative_to(base_resolved)

    # Block symlinks (optional)
    if path.is_symlink():
        raise SecurityError("Symlinks not allowed")

    return resolved
```

### Safe File Write

```python
def _atomic_write(filepath: Path, content: str) -> None:
    # Create temp in same dir
    temp_fd, temp_path = tempfile.mkstemp(dir=filepath.parent)

    # Write with secure permissions
    os.chmod(temp_path, 0o600)
    with os.fdopen(temp_fd, 'w') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    # Atomic rename
    os.replace(temp_path, filepath)
```

### Safe Template Rendering

```python
from string import Template  # Not jinja2!

def _render_template(template_str: str, vars: Dict[str, str]) -> str:
    template = Template(template_str)
    return template.safe_substitute(vars)
```

## Anti-Patterns (NEVER DO THIS)

```python
# ❌ NEVER: Shell injection
subprocess.run(f"pre-commit {command}", shell=True)

# ❌ NEVER: Unvalidated paths
path = project_root / user_input

# ❌ NEVER: Jinja2 with user content
from jinja2 import Template
template = Template(user_content)

# ❌ NEVER: Non-atomic writes
filepath.write_text(content)

# ❌ NEVER: World-readable permissions
filepath.chmod(0o644)  # Others can read
```

## Security Testing Commands

```bash
# Test command injection
python -c "from hooks.precommit_installer import *; test_injection()"

# Test path traversal
python -c "from hooks.precommit_installer import *; test_traversal()"

# Check file permissions
find .claude -type f -name ".precommit_preference" -exec stat -c '%a %n' {} \;

# Check for shell=True usage
grep -r "shell=True" .claude/
```

## When in Doubt

1. **Read the full doc**: `.claude/docs/SECURITY_REQUIREMENTS.md`
2. **Ask security agent**: For complex scenarios
3. **Default to secure**: Deny by default, allow explicitly
4. **Test the attack**: If you can think of an attack, test it

## Contact

- **Full Requirements**: `.claude/docs/SECURITY_REQUIREMENTS.md`
- **Security Agent**: Invoke for reviews
- **Issue**: #2281

---

**Remember**: Security is worth the complexity. Never compromise security for convenience.
