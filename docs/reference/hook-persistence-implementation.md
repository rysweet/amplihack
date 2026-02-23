# Hook Persistence Implementation Reference

Technical reference for the hook persistence fix implemented in v0.9.1.

## Overview

This document describes the implementation details of the fix for Issue #2335, which resolved the hook restoration bug where SettingsManager would wipe out hooks on exit.

## Problem Statement

### Symptom

```
Stop hook error: Failed with non-blocking status code: /bin/sh: 1: /home/azureuser/.claude/tools/amplihack/hooks/stop.py: not found
```

### Root Cause

The problematic execution flow was:

1. `launch_interactive()` creates `SettingsManager` context
2. `SettingsManager.__enter__()` backs up current settings.json (WITHOUT hooks)
3. `ensure_settings_json()` adds hooks to settings.json (WITH hooks)
4. User works in Claude Code session (hooks function correctly)
5. User exits Claude Code
6. `SettingsManager.__exit__()` restores backup (WITHOUT hooks)
7. Next launch: hooks missing from settings.json

## Implementation Details

### File Modified

`src/amplihack/launcher/core.py`

### Changes Made

**Before (Buggy Code):**

```python
def launch_interactive(
    proxy_manager: ProxyManager | None = None,
    append_system_prompt: Path | None = None,
    force_staging: bool = False,
    checkout_repo: str | None = None,
    claude_args: list[str] | None = None,
    verbose: bool = False,
) -> int:
    """Launch Claude Code interactively."""

    # Create settings manager for temporary changes
    settings_manager = SettingsManager(
        project_dir=Path.cwd(),
        backup_settings=True,
        restore_on_exit=True,
    )

    with settings_manager:  # ← BUG: Creates backup BEFORE hooks added
        # Ensure settings.json exists with hooks
        ensure_settings_json()  # ← Adds hooks AFTER backup created

        # Launch Claude Code
        launcher = ClaudeLauncher(
            proxy_manager=proxy_manager,
            append_system_prompt=append_system_prompt,
            force_staging=force_staging,
            checkout_repo=checkout_repo,
            claude_args=claude_args,
            verbose=verbose,
        )

        if not launcher.prepare_launch():
            return 1

        return launcher.launch_claude()
    # ← On exit: SettingsManager restores backup WITHOUT hooks (BUG)
```

**After (Fixed Code):**

```python
def launch_interactive(
    proxy_manager: ProxyManager | None = None,
    append_system_prompt: Path | None = None,
    force_staging: bool = False,
    checkout_repo: str | None = None,
    claude_args: list[str] | None = None,
    verbose: bool = False,
) -> int:
    """Launch Claude Code interactively."""

    # Ensure settings.json exists with hooks (permanent change)
    ensure_settings_json()  # ← Direct write - no backup/restore

    # Launch Claude Code
    launcher = ClaudeLauncher(
        proxy_manager=proxy_manager,
        append_system_prompt=append_system_prompt,
        force_staging=force_staging,
        checkout_repo=checkout_repo,
        claude_args=claude_args,
        verbose=verbose,
    )

    if not launcher.prepare_launch():
        return 1

    return launcher.launch_claude()
    # ← On exit: hooks persist in settings.json (FIXED)
```

### Lines Changed

- **Removed:** ~15 lines (SettingsManager initialization and context manager usage)
- **Added:** 0 lines (simpler solution)
- **Net change:** -15 lines (code simplification)

## ensure_settings_json() Behavior

The `ensure_settings_json()` function:

1. Checks if `~/.claude/settings.json` exists
2. If not, creates it with default configuration
3. Ensures hooks section contains amplihack hooks
4. Writes directly to settings.json (no backup)
5. Returns without cleanup

**Implementation location:** `src/amplihack/config/settings.py`

```python
def ensure_settings_json() -> None:
    """Ensure settings.json exists with amplihack hooks."""
    settings_path = Path.home() / ".claude" / "settings.json"

    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
    else:
        settings = {}

    # Add hooks if not present
    if "hooks" not in settings:
        settings["hooks"] = create_default_hooks()

    # Write back to file
    settings_path.write_text(json.dumps(settings, indent=2))
```

## Hook Path Fixing

Additionally, the launcher automatically fixes hook paths to use absolute paths:

**Implementation:** `src/amplihack/launcher/core.py` - `_fix_hook_paths_in_settings()`

```python
def _fix_hook_paths_in_settings(self, target_dir: Path) -> bool:
    """Fix relative hook paths to absolute in settings.json."""
    settings_path = target_dir / ".claude" / "settings.json"

    if not settings_path.exists():
        return True  # No settings to fix

    settings = json.loads(settings_path.read_text())

    if "hooks" not in settings:
        return True  # No hooks to fix

    # Convert relative paths to absolute
    for hook_type, hook_configs in settings["hooks"].items():
        for config in hook_configs:
            for hook in config.get("hooks", []):
                if "command" in hook:
                    cmd = hook["command"]
                    if not Path(cmd).is_absolute():
                        # Convert to absolute using target_dir
                        hook["command"] = str((target_dir / cmd).resolve())

    # Write back
    settings_path.write_text(json.dumps(settings, indent=2))
    return True
```

## Testing Verification

### Manual Test Procedure

```bash
# Step 1: Clean state
rm ~/.claude/settings.json

# Step 2: Launch amplihack
amplihack

# Step 3: Verify hooks added
cat ~/.claude/settings.json | grep -A10 hooks
# Expected: SessionStart, Stop, PostToolUse hooks present

# Step 4: Exit Claude Code
# (Use Claude Code's exit command)

# Step 5: Verify hooks persisted
cat ~/.claude/settings.json | grep -A10 hooks
# Expected: Hooks still present (FIXED - previously would be missing)

# Step 6: Re-launch amplihack
amplihack
# Expected: No "hook not found" errors
```

### Automated Test

```python
def test_hook_persistence():
    """Test that hooks persist after launch."""
    # Setup
    settings_file = Path.home() / ".claude" / "settings.json"
    settings_file.unlink(missing_ok=True)

    # Execute launch
    launch_interactive()

    # Verify hooks added
    settings = json.loads(settings_file.read_text())
    assert "hooks" in settings
    assert "SessionStart" in settings["hooks"]

    # Simulate exit (settings_manager would restore here in old code)
    # In fixed code, nothing happens

    # Verify hooks still present
    settings = json.loads(settings_file.read_text())
    assert "hooks" in settings  # FIXED: hooks persist
```

## Impact Analysis

### Positive Impacts

1. **Hooks persist across sessions** - No more reinstallation required
2. **Simpler code** - Removed unnecessary abstraction
3. **Correct pattern usage** - SettingsManager only used for temporary changes
4. **Fewer errors** - Eliminates "hook not found" class of errors
5. **Better user experience** - Install once, works forever

### No Breaking Changes

The fix is fully backward compatible:

- Existing installations automatically benefit
- No user action required
- No API changes
- No configuration changes needed

### Performance Impact

**Negligible:** Removed ~15 lines of backup/restore code actually slightly improves launch performance (no backup creation or restoration).

## Related Files

- **Implementation:** `src/amplihack/launcher/core.py`
- **Hook Creation:** `src/amplihack/config/settings.py`
- **Tests:** `tests/test_launcher_core.py`
- **Issue:** GitHub Issue [#2335](https://github.com/rysweet/amplihack/issues/2335)

## Future Considerations

### If Temporary Hook Configuration Needed

For future use cases requiring temporary hooks:

```python
# Hypothetical future code
def test_with_temporary_hooks():
    """Test with temporary hooks that should revert."""
    with SettingsManager() as settings:  # OK for temporary testing
        settings.add_temporary_test_hooks()
        run_integration_tests()
        # On exit: temporary hooks automatically removed

def launch_interactive():
    """Launch with permanent hooks."""
    ensure_settings_json()  # Permanent hooks - no revert
    # ... launch ...
```

**Key distinction:** Clearly document intention (temporary vs permanent) and use appropriate pattern.

### SettingsManager Still Valid For

- Testing with experimental configurations
- Preview modes
- Debugging with temporary overrides
- Scenarios requiring automatic cleanup

**Just not for permanent installation operations.**

## See Also

- [Changelog v0.9.1](../CHANGELOG_v0.9.1.md) - Release notes
- [Hook Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) - User guide
- [SettingsManager vs Permanent Changes](../concepts/settings-manager-vs-permanent-changes.md) - Architecture concept
- [Troubleshoot Hooks](../howto/troubleshoot-hooks.md) - Diagnostic guide
