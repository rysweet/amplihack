# Changelog - Version 0.9.1

Release Date: 2025-02-15

## Bug Fixes

### Hook Restoration Bug (Issue #2335)

**Problem:**

Stop hook was failing with "not found" error after each Claude Code exit because SettingsManager backed up settings.json BEFORE hooks were added, then restored the old backup (without hooks) on exit.

**Root Cause:**

The problematic flow was:

1. SettingsManager creates backup (WITHOUT hooks)
2. ensure_settings_json() adds hooks (WITH hooks)
3. User exits Claude
4. SettingsManager restores backup (WITHOUT hooks) ← **BUG**
5. Next launch: hooks missing

**Solution:**

Removed SettingsManager from launch_interactive() in src/amplihack/launcher/core.py because:

- SettingsManager is for TEMPORARY changes that should be restored
- amplihack launch makes PERMANENT changes (adding hooks)
- The backup/restore mechanism conflicted with permanent hook installation

**Impact:**

- Hooks now persist permanently across Claude Code sessions
- No more "hook not found" errors after exiting Claude
- Hook paths are automatically fixed to absolute paths during launch
- Simplified code by removing ~15 lines of backup/restore logic

**Files Modified:**

- src/amplihack/launcher/core.py (removed SettingsManager usage)

**Testing:**

```bash
# Manual verification process
1. Launch amplihack
2. Check ~/.claude/settings.json (hooks present)
3. Exit Claude Code
4. Check ~/.claude/settings.json (hooks still present)
5. Re-launch amplihack
6. Verify hooks execute successfully
```

**Related Documentation:**

- [Hook Configuration Guide](./HOOK_CONFIGURATION_GUIDE.md) - Updated with persistence information
- GitHub Issue [#2335](https://github.com/rysweet/amplihack/issues/2335)

---

## Technical Details

### Why SettingsManager Wasn't Appropriate

SettingsManager follows a backup/restore pattern designed for temporary configuration changes:

```python
# Backup/restore pattern (temporary changes)
1. Create backup of current state
2. Make changes
3. On exit: Restore backup
```

This pattern is correct for:

- Testing with temporary configurations
- Preview modes that should revert
- One-off experimental settings

But INCORRECT for:

- Installing hooks that should persist
- Permanent configuration changes
- System-wide setup modifications

### The Fix

Instead of using SettingsManager, hooks are now written directly during launch:

```python
# Before (BUGGY)
with SettingsManager() as settings:
    # SettingsManager creates backup WITHOUT hooks
    ensure_settings_json()  # Adds hooks
    # On exit: restores backup WITHOUT hooks

# After (CORRECT)
ensure_settings_json()  # Adds hooks directly
# No backup/restore - hooks persist
```

### Future Considerations

If temporary hook configuration is needed in the future:

1. Create a separate "preview mode" flag
2. Use SettingsManager ONLY when preview mode is active
3. Document clearly that preview mode reverts changes
4. Never mix permanent and temporary configuration mechanisms

---

## Philosophy Alignment

This fix demonstrates key amplihack principles:

**Ruthless Simplicity:**

- Removed unnecessary abstraction (SettingsManager)
- Direct solution: write settings, don't backup/restore

**Zero-BS Implementation:**

- Eliminated backup/restore code that didn't serve the use case
- Fixed root cause instead of working around symptoms

**Correct Tool for the Job:**

- SettingsManager is correct for temporary changes
- Direct writes are correct for permanent changes
- Don't force-fit abstractions to wrong use cases

---

## Upgrade Notes

No action required for users. The fix is automatic on next amplihack launch.

If hooks were previously missing after Claude Code exit, they will now persist correctly.
