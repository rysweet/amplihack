# Reference: Copilot CLI Installation Implementation

Technical reference for maintainers of the Copilot CLI installation system.

## Architecture

### Installation Flow

```
┌─────────────────────────────────────┐
│ launch_copilot()                    │
│                                     │
│ 1. Check if already installed      │
│    shutil.which("github-copilot-cli")│
│                                     │
│ 2. Install if needed               │
│    install_copilot()               │
│    - Runs npm install -g           │
│    - Returns True/False            │
│                                     │
│ 3. Report status                   │
│    - Trust installer return value  │
│    - Print success/failure         │
│    - Exit with appropriate code    │
│                                     │
│ 4. Launch CLI                      │
│    subprocess.run(["github-copilot-cli"])│
└─────────────────────────────────────┘
```

### Module Structure

**File**: `amplihack/launcher/__init__.py`

```python
def launch_copilot() -> None:
    """Launch GitHub Copilot CLI, installing if needed."""

def install_copilot() -> bool:
    """Install GitHub Copilot CLI via npm.

    Returns:
        True if installation succeeded, False otherwise
    """
```

## Implementation Details

### Installation Check

**Function**: `shutil.which("github-copilot-cli")`

**Purpose**: Check if Copilot CLI binary is in PATH

**Behavior**:

- Returns full path if found: `/home/user/.local/bin/github-copilot-cli`
- Returns `None` if not found
- Searches current process's PATH environment variable
- Does not search outside PATH

**Limitations**:

- Only sees PATH at process start time
- Does not detect binaries added after process starts
- Subprocess environment may differ from parent

### Installation Process

**Function**: `install_copilot()`

**Implementation**:

```python
def install_copilot() -> bool:
    """Install GitHub Copilot CLI via npm."""
    try:
        result = subprocess.run(
            ["npm", "install", "-g", "github-copilot-cli"],
            check=False,  # Don't raise on failure
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        # npm not found
        return False
    except Exception as e:
        print(f"Installation error: {e}")
        return False
```

**Validation**:

- Checks npm exit code (0 = success)
- Does NOT re-verify with `shutil.which()`
- Trusts npm's success indication

**Why trust npm exit code?**

- npm validates installation internally
- Exit code 0 guarantees success
- Binary is written before npm exits
- Avoids PATH propagation race condition

### Status Reporting

**Success Path**:

```python
if not shutil.which("github-copilot-cli"):
    success = install_copilot()
    if not success:
        print("Failed to install Copilot CLI")
        sys.exit(1)
    print("Successfully installed Copilot CLI")
```

**Failure Path**:

```python
# npm install failed
if not success:
    print("Failed to install Copilot CLI")
    sys.exit(1)
```

## Bug History

### Original Bug (v0.3.1)

**Code**:

```python
if not shutil.which("github-copilot-cli"):
    success = install_copilot()

    # Redundant verification (BUG)
    if not shutil.which("github-copilot-cli"):
        print("Failed to install Copilot CLI")
        sys.exit(1)
```

**Issue**: Redundant `shutil.which()` check after installation

**Root Cause**: PATH propagation timing

**Symptoms**: False negative when installation succeeded

### The Fix (v0.3.2)

**Change**: Remove redundant verification

**Code**:

```python
if not shutil.which("github-copilot-cli"):
    success = install_copilot()
    if not success:
        print("Failed to install Copilot CLI")
        sys.exit(1)
    print("Successfully installed Copilot CLI")
```

**Result**: Accurate status reporting

## PATH Propagation

### The Problem

**Scenario**: Install binary, check PATH immediately

**What happens**:

1. npm installs binary to `~/.local/bin/github-copilot-cli`
2. Binary exists on disk
3. Shell updates PATH (asynchronously)
4. Current process hasn't seen PATH update yet
5. `shutil.which()` can't find binary

**Timeline**:

```
T+0ms:  npm install starts
T+100ms: Binary written to disk
T+110ms: npm exits with code 0
T+120ms: Shell updates PATH
T+130ms: shutil.which() checks PATH (binary not visible yet)
T+200ms: PATH propagates to current process
```

**Solution**: Trust installer exit code, don't re-check PATH

### Platform Differences

**Linux/macOS**:

- PATH updates propagate to child processes
- Parent process sees stale PATH
- `shutil.which()` searches parent's PATH

**Windows**:

- Similar behavior with different timing
- Registry updates may be involved
- Environment blocks cached per process

## Testing Strategy

### Unit Tests

**Test**: Installation triggers when needed

```python
def test_launch_copilot_installs_when_missing(monkeypatch):
    """Verify installation happens when CLI not found."""
    with patch('shutil.which', return_value=None), \
         patch('amplihack.launcher.install_copilot', return_value=True), \
         patch('subprocess.run'):
        launch_copilot()
        # Should succeed without raising
```

**Test**: Failure reported accurately

```python
def test_launch_copilot_reports_install_failure(monkeypatch):
    """Verify failure message when installation fails."""
    with patch('shutil.which', return_value=None), \
         patch('amplihack.launcher.install_copilot', return_value=False):
        with pytest.raises(SystemExit) as exc:
            launch_copilot()
        assert exc.value.code == 1
```

**Test**: No installation when already present

```python
def test_launch_copilot_skips_install_when_present(monkeypatch):
    """Verify no installation when CLI already exists."""
    install_mock = Mock()
    with patch('shutil.which', return_value='/usr/bin/github-copilot-cli'), \
         patch('amplihack.launcher.install_copilot', install_mock), \
         patch('subprocess.run'):
        launch_copilot()
        install_mock.assert_not_called()
```

### Integration Tests

**Test**: Fresh installation

```bash
# Remove Copilot CLI
npm uninstall -g github-copilot-cli

# Verify not installed
! which github-copilot-cli

# Run amplihack
amplihack copilot

# Verify success
test $? -eq 0
which github-copilot-cli
```

**Test**: Existing installation

```bash
# Ensure installed
npm install -g github-copilot-cli

# Run amplihack (should skip install)
amplihack copilot

# Verify success
test $? -eq 0
```

## Error Handling

### npm Not Found

```python
try:
    result = subprocess.run(["npm", ...])
except FileNotFoundError:
    return False  # npm not installed
```

**User sees**: "Failed to install Copilot CLI"

**Solution**: Install npm: `sudo apt install npm`

### npm Install Failure

**Causes**:

- Network issues
- Permissions problems
- Disk space exhausted
- Package not found

**Detection**: `result.returncode != 0`

**User sees**: "Failed to install Copilot CLI"

**Solution**: Check npm logs: `npm install -g github-copilot-cli`

### Permission Denied

**Cause**: Global npm install requires write access

**Detection**: npm exit code, stderr contains "EACCES"

**Solution**: Use `sudo` or configure npm prefix:

```bash
npm config set prefix ~/.local
export PATH=~/.local/bin:$PATH
```

## Design Decisions

### Why Trust npm Exit Code?

**Options considered**:

1. Trust npm exit code (chosen)
2. Re-verify with `shutil.which()`
3. Check binary exists on disk
4. Test execution with `--version`

**Decision**: Trust npm exit code

**Rationale**:

- npm validates internally before exiting
- Avoids PATH propagation timing issues
- Simplest implementation
- npm exit codes are reliable (industry standard)

### Why Not Test Execution?

**Alternative**: Run `github-copilot-cli --version` to verify

**Rejected because**:

- Adds complexity (parse version output)
- Same PATH propagation issue
- Unnecessary overhead
- npm validation is sufficient

### Why No Retry Logic?

**Alternative**: Retry if verification fails

**Rejected because**:

- Masks real installation failures
- Delays feedback to user
- npm should succeed or fail definitively
- Retries won't fix PATH timing (not a transient error)

## Maintenance Notes

### When to Modify

**Change installer if**:

- npm package name changes
- Installation method changes (not npm)
- Different global vs. local install needed

**Don't change if**:

- Seeing "PATH not propagated" issues (by design)
- Want to verify installation (trust npm)
- Need to support alternative install methods (use separate function)

### Testing Checklist

Before releasing changes:

- [ ] Unit tests pass
- [ ] Integration test on fresh system
- [ ] Test with Copilot already installed
- [ ] Test with npm not installed
- [ ] Test with permission denied errors
- [ ] Test on Linux, macOS, Windows
- [ ] Exit codes correct (0 success, 1 failure)
- [ ] Messages clear and accurate

### Code Review Focus

**Check these during review**:

1. **No redundant verification**: Don't re-check after installation
2. **Trust installer**: Use return value, not PATH lookup
3. **Exit codes correct**: 0 for success, 1 for failure
4. **Messages accurate**: Match actual result
5. **Error handling**: Catch npm not found, install failures

## Related Code

**Files**:

- `amplihack/launcher/__init__.py` - Main implementation
- `tests/test_launcher.py` - Unit tests
- `scripts/install.sh` - Installation script

**Dependencies**:

- `shutil.which()` - PATH lookup
- `subprocess.run()` - Execute npm, launch CLI
- `sys.exit()` - Exit with status code

## Future Improvements

### Potential Enhancements

1. **Verbose mode**: Show npm output on failure
2. **Offline install**: Support installing from cache
3. **Version check**: Verify minimum version requirements
4. **Auto-upgrade**: Detect outdated installation
5. **Alternative installers**: Support pip, brew, etc.

### Not Recommended

1. **Retry verification**: Masks real issues
2. **PATH manipulation**: Fragile, platform-specific
3. **Binary download**: npm handles this better
4. **Version pinning**: Users may want latest

---

**Audience**: Maintainers and contributors
**Scope**: Implementation details
**Last Updated**: 2025-02-13
**Version**: 0.3.2
