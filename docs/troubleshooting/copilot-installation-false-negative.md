# Troubleshooting: Copilot CLI Installation False Negative

Quick solution for when `amplihack copilot` reports installation failure despite successful installation.

## Quick Diagnosis

Run this diagnostic to verify actual installation status:

```bash
# Check if Copilot CLI is actually installed
which github-copilot-cli

# Check npm global packages
npm list -g github-copilot-cli
```

Expected output if installed:

```bash
/home/user/.local/bin/github-copilot-cli
github-copilot-cli@1.0.0
```

---

## Issue: "Failed to install Copilot CLI" Despite Successful Installation

### Symptoms

- Installation completes successfully (npm returns exit code 0)
- Message displays: "Failed to install Copilot CLI"
- Command exits with error code 1
- Running `which github-copilot-cli` shows installation succeeded
- Subsequent runs work correctly

### Cause

**Fixed in version 0.3.2**

The `launch_copilot()` function performed redundant verification after installation that failed due to PATH propagation timing. The code trusted the initial `shutil.which()` check but then re-checked after installation, catching a race condition where the PATH hadn't propagated yet.

### Technical Details

The bug occurred in this flow:

```python
# 1. Initial check passes (Copilot not installed)
if not shutil.which("github-copilot-cli"):

    # 2. install_copilot() runs and succeeds
    success = install_copilot()  # Returns True, installation worked

    # 3. Redundant verification fails (PATH timing issue)
    if not shutil.which("github-copilot-cli"):
        print("Failed to install...")  # FALSE NEGATIVE
        sys.exit(1)
```

The redundant verification in step 3 would fail because:

- npm's global installation completes successfully
- Binary is written to disk
- Shell PATH hasn't propagated to current process yet
- `shutil.which()` can't find the binary immediately

### Solution

**The fix removes the redundant verification and trusts the installer's return value:**

```python
# Now correctly trusts the installer
if not shutil.which("github-copilot-cli"):
    success = install_copilot()  # Validates via npm exit code
    if not success:
        print("Failed to install Copilot CLI")
        sys.exit(1)
    print("Successfully installed Copilot CLI")
```

Changes:

1. Removed redundant `shutil.which()` check after installation
2. Trust `install_copilot()` return value (already validates via npm exit code)
3. Display success message when installation completes
4. Exit with code 0 on success, code 1 only on actual failure

---

## Verification

After the fix, successful installation shows:

```bash
$ amplihack copilot
Installing Copilot CLI...
Successfully installed Copilot CLI
[Copilot CLI launches]
```

Failed installation shows:

```bash
$ amplihack copilot
Installing Copilot CLI...
Failed to install Copilot CLI
[Exit code 1]
```

---

## Testing

The fix includes comprehensive test coverage:

### Unit Tests

```python
def test_launch_copilot_installs_when_missing():
    """Verify installation triggers when CLI not found."""
    with patch('shutil.which', return_value=None), \
         patch('amplihack.launcher.install_copilot', return_value=True):
        # Should succeed after installation
        launch_copilot()

def test_launch_copilot_reports_install_failure():
    """Verify failure reported when installation actually fails."""
    with patch('shutil.which', return_value=None), \
         patch('amplihack.launcher.install_copilot', return_value=False):
        with pytest.raises(SystemExit) as exc:
            launch_copilot()
        assert exc.value.code == 1
```

### Integration Tests

Test on fresh system without Copilot CLI:

```bash
# Uninstall Copilot CLI
npm uninstall -g github-copilot-cli

# Test installation from scratch
amplihack copilot

# Verify success message appears and CLI launches
```

---

## Related Issues

- **PATH propagation timing**: Other tools that verify immediately after installation may hit similar issues
- **npm global installs**: Consider using `npm bin -g` to check installation location instead of PATH lookup
- **Subprocess environment**: Child processes inherit environment at spawn time, not dynamically

---

## Prevention

To avoid similar issues in other commands:

1. **Trust the installer**: If installation tool returns success, don't re-verify immediately
2. **Check exit codes**: npm/pip exit codes are reliable (0 = success, non-zero = failure)
3. **Document timing**: Note that PATH propagation isn't instant
4. **Test on fresh systems**: Integration tests should install from scratch

---

## Additional Resources

- [Copilot CLI Integration](../COPILOT_CLI_INTEGRATION_SUMMARY.md) - Complete integration guide
- [GitHub Copilot Documentation](../github-copilot-litellm-integration.md) - Using Copilot with amplihack
- [Platform Bridge](../platform-bridge/README.md) - Multi-platform support patterns

---

**Last Updated**: 2025-02-13
**Fixed In Version**: 0.3.2
**Affects**: `amplihack copilot` command on fresh installations
