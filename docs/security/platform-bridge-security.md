# Platform Bridge - Security Documentation

Security analysis and best practices fer the platform bridge module.

## Security Model

The platform bridge follows a **delegation security model** where authentication and authorization be handled by official CLI tools (gh and az), not by the bridge itself.

### Core Principles

1. **No Credential Storage**: Bridge never stores or handles credentials
2. **CLI Authentication**: Delegates all authentication to gh/az CLI tools
3. **Input Validation**: All user inputs be validated before subprocess calls
4. **Safe Subprocess**: Parameterized commands prevent shell injection
5. **Fail Secure**: Errors don't leak sensitive information

## Authentication Delegation

### GitHub Authentication

The bridge uses `gh` CLI fer all GitHub operations:

```python
# Bridge NEVER handles GitHub tokens directly
bridge = PlatformBridge()  # No tokens or credentials passed

# Authentication handled by gh CLI
issue = bridge.create_issue(title="Test", body="Body")
# Under the hood: gh uses credentials from ~/.config/gh/hosts.yml
```

**User Authentication Flow**:
1. User runs: `gh auth login`
2. GitHub CLI authenticates through OAuth
3. Credentials stored in `~/.config/gh/hosts.yml`
4. Bridge calls `gh` commands which use stored credentials

**Benefits**:
- Bridge code never sees tokens
- GitHub handles token refresh
- Standard gh security model applies

### Azure DevOps Authentication

The bridge uses `az` CLI fer all Azure DevOps operations:

```python
# Bridge NEVER handles Azure DevOps PATs directly
bridge = PlatformBridge()  # No tokens or credentials passed

# Authentication handled by az CLI
issue = bridge.create_issue(title="Test", body="Body")
# Under the hood: az uses credentials from ~/.azure/
```

**User Authentication Flow**:
1. User runs: `az login`
2. Azure CLI authenticates through browser
3. Credentials stored in `~/.azure/`
4. Bridge calls `az` commands which use stored credentials

**Benefits**:
- Bridge code never sees tokens or PATs
- Azure handles token refresh
- Standard az security model applies

## Input Validation

All user inputs be validated before bein' passed to subprocess calls.

### Title Validation

```python
def _validate_title(title: str) -> None:
    """Validate issue/PR title"""
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")

    if len(title) > 256:
        raise ValueError("Title too long (max 256 characters)")

    # No shell metacharacters in title
    dangerous_chars = ['$', '`', '$(', '|', '&', ';']
    if any(char in title for char in dangerous_chars):
        raise ValueError(f"Title contains invalid characters: {dangerous_chars}")
```

### Branch Name Validation

```python
def _validate_branch_name(branch: str) -> None:
    """Validate git branch name"""
    if not branch or not branch.strip():
        raise ValueError("Branch name cannot be empty")

    # Git branch name rules
    invalid_patterns = ['..',  '~', '^', ':', '\\', '*', '?', '[']
    if any(pattern in branch for pattern in invalid_patterns):
        raise ValueError(f"Branch name contains invalid patterns")

    if branch.startswith('/') or branch.endswith('/'):
        raise ValueError("Branch name cannot start or end with /")
```

### Body/Description Validation

```python
def _validate_body(body: str) -> None:
    """Validate issue/PR body"""
    if not body or not body.strip():
        raise ValueError("Body cannot be empty")

    # No null bytes (can confuse subprocess)
    if '\x00' in body:
        raise ValueError("Body contains null bytes")

    # Reasonable size limit (prevent DoS)
    if len(body) > 65536:  # 64KB
        raise ValueError("Body too large (max 64KB)")
```

## Safe Subprocess Usage

All subprocess calls use **parameterized commands** to prevent shell injection.

### Correct Pattern (Safe)

```python
# SAFE - Command and args as list
subprocess.run(
    ["gh", "issue", "create", "--title", title, "--body", body],
    capture_output=True,
    text=True,
    timeout=30
)
```

**Why this be safe**:
- Command and arguments passed as list
- No shell interpretation
- Arguments can't be interpreted as commands
- Even if title/body contain `; rm -rf /`, they be treated as literal strings

### Anti-Pattern (Unsafe)

```python
# UNSAFE - Don't do this!
subprocess.run(
    f"gh issue create --title '{title}' --body '{body}'",
    shell=True,  # ❌ Dangerous!
    capture_output=True
)
```

**Why this be dangerous**:
- Shell interprets the entire string
- Special characters in title/body can execute commands
- Example attack: `title = "test'; rm -rf /; echo '"`

### Timeout Protection

All subprocess calls have timeouts to prevent hangs:

```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=30  # 30 second timeout
)
```

**Timeout Values**:
- Standard operations: 30 seconds
- CI status checks: 60 seconds (can be slow)
- Large file uploads: 120 seconds

## Error Handling

Errors be handled to prevent information leakage:

### Safe Error Messages

```python
try:
    result = subprocess.run(cmd, ...)
    if result.returncode != 0:
        # Don't expose full command in error
        raise RuntimeError(f"Operation failed: {sanitize_error(result.stderr)}")

except subprocess.TimeoutExpired:
    # Don't expose what command timed out
    raise RuntimeError("Operation timed out after 30 seconds")

except Exception as e:
    # Don't expose internal details
    raise RuntimeError(f"Unexpected error: {type(e).__name__}")
```

### Information Leakage Prevention

**What we DON'T expose**:
- Full subprocess commands (might contain sensitive args)
- File system paths (might reveal directory structure)
- Internal stack traces (might reveal implementation details)

**What we DO expose**:
- Operation type (e.g., "create issue failed")
- User-actionable guidance (e.g., "run gh auth login")
- Error categories (e.g., "authentication required")

## Filesystem Security

The bridge reads git configuration but never writes to filesystem (except through CLI tools).

### Read-Only Operations

```python
# Bridge only reads git config
def _get_git_remote(repo_path: Path) -> str:
    """Read git remote URL (read-only)"""
    result = subprocess.run(
        ["git", "remote", "-v"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return result.stdout
```

### No Filesystem Writes

The bridge **never** writes to:
- Git configuration (`.git/config`)
- Credential files (`~/.config/gh/`, `~/.azure/`)
- System directories
- Temporary files with sensitive data

All writes be handled by official CLI tools which have their own security models.

## Threat Model

### Threats We Mitigate

1. **Shell Injection**: Parameterized commands prevent command injection
2. **Credential Theft**: No credentials stored or handled by bridge
3. **Information Leakage**: Error messages don't expose sensitive details
4. **DoS via Large Inputs**: Size limits on all inputs
5. **Path Traversal**: Repository paths validated

### Threats Out of Scope

These be handled by CLI tools or operating system:

1. **Network Security**: gh/az CLI handle HTTPS connections
2. **Token Refresh**: CLI tools manage token lifecycle
3. **Multi-Factor Auth**: Handled by GitHub/Azure DevOps
4. **Rate Limiting**: CLI tools handle API rate limits
5. **Audit Logging**: Platform services log all operations

### Trust Boundaries

```
User Code → PlatformBridge → gh/az CLI → GitHub/Azure DevOps API
   ↑            ↑                ↑              ↑
   |            |                |              |
   |            |                |              +-- Trusted (official API)
   |            |                +----------------- Trusted (official CLI)
   |            +---------------------------------- Trusted (our code)
   +----------------------------------------------- Untrusted (user input)
```

**Trust Assumptions**:
- User input be UNTRUSTED (validate everything)
- gh/az CLI tools be TRUSTED (official tools)
- Platform APIs be TRUSTED (GitHub/Azure)
- Operating system be TRUSTED (subprocess isolation)

## Security Best Practices

### For Users

1. **Keep CLI Tools Updated**:
   ```bash
   # GitHub CLI
   gh version  # Check current version
   brew upgrade gh  # Update (macOS)

   # Azure CLI
   az version  # Check current version
   brew upgrade azure-cli  # Update (macOS)
   ```

2. **Use Secure Authentication**:
   ```bash
   # GitHub - Use OAuth, not PATs
   gh auth login  # Follow OAuth flow

   # Azure - Use browser auth
   az login  # Opens browser
   ```

3. **Review Permissions**:
   ```bash
   # GitHub - Check token permissions
   gh auth status

   # Azure - Check account permissions
   az account show
   ```

4. **Rotate Credentials Regularly**:
   ```bash
   # GitHub - Refresh auth
   gh auth refresh

   # Azure - Re-login periodically
   az logout && az login
   ```

### For Developers

1. **Never Add Credential Parameters**:
   ```python
   # ❌ WRONG - Don't add token parameters
   def create_issue(self, title: str, token: str):
       ...

   # ✅ RIGHT - Delegate to CLI
   def create_issue(self, title: str):
       subprocess.run(["gh", "issue", "create", ...])
   ```

2. **Always Validate Inputs**:
   ```python
   # ✅ RIGHT - Validate before subprocess
   def create_issue(self, title: str, body: str):
       self._validate_title(title)
       self._validate_body(body)
       subprocess.run([...])
   ```

3. **Use Parameterized Commands**:
   ```python
   # ✅ RIGHT - List of args
   subprocess.run(["gh", "issue", "create", "--title", title])

   # ❌ WRONG - String with shell=True
   subprocess.run(f"gh issue create --title '{title}'", shell=True)
   ```

4. **Set Timeouts**:
   ```python
   # ✅ RIGHT - Always set timeout
   subprocess.run(cmd, timeout=30)

   # ❌ WRONG - No timeout (can hang forever)
   subprocess.run(cmd)
   ```

## Security Audit Checklist

When reviewin' platform bridge code:

- [ ] No credential storage or handling
- [ ] All subprocess calls use list (not string with shell=True)
- [ ] All user inputs validated before subprocess
- [ ] Timeouts set on all subprocess calls
- [ ] Error messages don't leak sensitive info
- [ ] No filesystem writes except through CLI tools
- [ ] Branch names validated against git rules
- [ ] Size limits enforced on all inputs
- [ ] No null bytes in string inputs
- [ ] Exception handling prevents info leakage

## Reporting Security Issues

If ye discover a security vulnerability in the platform bridge:

1. **Don't** open a public GitHub issue
2. **Do** email security@amplihack.dev with details
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if ye have one)

We'll respond within 48 hours and coordinate a fix.

## See Also

- [Platform Bridge Overview](../platform-bridge/README.md) - Feature documentation
- [API Reference](../reference/platform-bridge-api.md) - Complete API
- [GitHub CLI Security](https://cli.github.com/manual/gh_auth_login) - gh authentication
- [Azure CLI Security](https://learn.microsoft.com/cli/azure/authenticate-azure-cli) - az authentication
