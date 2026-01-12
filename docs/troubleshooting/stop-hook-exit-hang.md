# Stop Hook Exit Hang - Troubleshooting

**Problem**: amplihack hangs for 10-13 seconds on exit, blocking `sys.stdin.read()` during cleanup.

**Status**: ✅ Fixed in v0.9.1

## Quick Fix (If Running Old Version)

```bash
# Upgrade to v0.9.1 or later
pip install --upgrade amplihack

# Or force kill if already hung
Ctrl+C (may need to press multiple times)
pkill -9 amplihack
```

## Symptoms

**Before Fix (v0.9.0 and earlier)**:

- Exit takes 10-13 seconds instead of <3 seconds
- No visible output during hang
- Process appears frozen
- Pressing Ctrl+C eventually works but feels unresponsive

**After Fix (v0.9.1+)**:

- Exit completes in <3 seconds
- Clean shutdown behavior
- No hanging or blocking

## Root Cause

The stop hook (`power_steering.stop`) was calling `read_input()` during `atexit` cleanup, which blocked on `sys.stdin.read()`. During shutdown:

1. Python's `atexit` handlers run
2. Stop hook calls `read_input()`
3. `read_input()` blocks on `sys.stdin.read()`
4. stdin is closed/detached during shutdown
5. Read operation hangs until timeout (10-13 seconds)

## The Fix

Added centralized shutdown detection that:

1. Checks `AMPLIHACK_SHUTDOWN_IN_PROGRESS` environment variable
2. Skips stdin reads during shutdown
3. Returns safe defaults immediately
4. Completes cleanup in <3 seconds

See [Shutdown Detection Explanation](../concepts/shutdown-detection.md) for technical details.

## Verifying the Fix

```bash
# Check your version
amplihack --version

# Should be v0.9.1 or later for the fix

# Test exit behavior
amplihack
# ... do some work ...
# Type 'exit' or Ctrl+D

# Should exit cleanly in <3 seconds
```

## If Still Experiencing Issues

### Issue: Hangs persist after upgrade

**Check**:

```bash
# Verify you're running the new version
python -c "import amplihack; print(amplihack.__version__)"
# Should show 0.9.1 or later
```

**Solution**: Clear any cached installations

```bash
pip uninstall amplihack
pip cache purge
pip install amplihack
```

### Issue: Environment variable not being set

**Check**:

```bash
# During normal operation, this should be unset
echo $AMPLIHACK_SHUTDOWN_IN_PROGRESS
# (should be empty)

# If it's set to "1", that's blocking normal operations
unset AMPLIHACK_SHUTDOWN_IN_PROGRESS
```

### Issue: Custom hooks experiencing similar hangs

If you've written custom hooks that read stdin, see [How to Add Shutdown Detection to Custom Hooks](../howto/add-shutdown-detection-to-hooks.md).

## Related Issues

- GitHub Issue #1896: Stop hook exit hang
- [Power Steering Troubleshooting](../features/power-steering/troubleshooting.md)

## Need More Help?

1. Check [Shutdown Detection Reference](../reference/shutdown-detection-api.md) for API details
2. Review [DISCOVERIES.md](../DISCOVERIES.md) for known issues
3. [Report a bug](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues) if the issue persists
