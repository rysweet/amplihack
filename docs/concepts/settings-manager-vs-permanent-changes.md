# SettingsManager vs Permanent Changes

Understanding when to use backup/restore patterns versus direct configuration writes.

## The Backup/Restore Pattern

SettingsManager implements a classic backup/restore pattern:

```python
class SettingsManager:
    def __enter__(self):
        self.backup = read_current_settings()
        return self

    def __exit__(self):
        restore_settings(self.backup)
```

This pattern is **correct** for temporary changes that should revert.

## The Problem

Using SettingsManager for permanent changes creates a bug:

```python
# BUGGY CODE (pre-v0.9.1)
with SettingsManager() as settings:
    # 1. SettingsManager creates backup WITHOUT hooks
    backup = read_settings()  # No hooks yet

    # 2. ensure_settings_json() adds hooks
    ensure_settings_json()    # Hooks added

    # 3. User works in Claude Code session
    # ... hooks work fine ...

    # 4. On exit: SettingsManager restores backup WITHOUT hooks
    # BUG: Hooks are wiped out!
```

**Result:** Hooks must be reinstalled every session.

## When to Use Each Pattern

### Use Backup/Restore (SettingsManager) For:

**Temporary Changes:**

- Testing with experimental configurations
- Preview modes that should revert on exit
- One-off modifications for debugging
- Session-specific overrides

**Example - Testing temporary feature:**

```python
with SettingsManager() as settings:
    settings.enable_experimental_feature()
    run_tests()
    # On exit: experimental feature disabled
```

### Use Direct Writes For:

**Permanent Changes:**

- Installing hooks that should persist
- User preferences
- System-wide configuration
- Setup and installation operations

**Example - Installing hooks (v0.9.1+):**

```python
# CORRECT CODE (v0.9.1+)
def launch_interactive():
    ensure_settings_json()  # Direct write
    # No backup/restore - hooks persist
```

## Real-World Analogy

### Backup/Restore (Temporary)

Like a sandbox or staging environment:

```
Production State
    ↓ (create sandbox)
Sandbox State ← Make temporary changes here
    ↓ (destroy sandbox)
Production State (unchanged)
```

### Direct Write (Permanent)

Like production deployment:

```
Production State
    ↓ (apply changes)
New Production State (changes persist)
```

## Decision Matrix

| Question                           | Backup/Restore | Direct Write |
| ---------------------------------- | -------------- | ------------ |
| Should changes persist after exit? | No             | Yes          |
| Is this for testing/preview?       | Yes            | No           |
| Should revert on error?            | Yes            | No           |
| Is this user configuration?        | No             | Yes          |
| Is this part of installation?      | No             | Yes          |

## The Fix (Issue #2335)

**Before (Buggy):**

```python
def launch_interactive():
    with SettingsManager() as settings:  # Creates backup WITHOUT hooks
        ensure_settings_json()           # Adds hooks
        # ... session ...
        # On exit: restores backup WITHOUT hooks (BUG)
```

**After (Fixed):**

```python
def launch_interactive():
    ensure_settings_json()  # Direct write - hooks persist
    # ... session ...
    # On exit: hooks remain in settings.json
```

**Impact:**

- Hooks persist across sessions
- No more "hook not found" errors
- Simpler code (removed ~15 lines)
- Correct abstraction usage

## Architecture Principle

**Use abstractions for their intended purpose:**

- SettingsManager = Temporary changes with automatic revert
- Direct writes = Permanent configuration changes

**Don't force-fit abstractions to wrong use cases.**

## Related Patterns

### Context Managers (Python)

Context managers (with statements) are inherently designed for cleanup:

```python
with open(file) as f:    # Open
    process(f)           # Use
    # Automatic close on exit

with transaction:        # Begin transaction
    modify_data()        # Make changes
    # Automatic commit/rollback on exit
```

SettingsManager follows this pattern - it's **supposed to** revert changes.

### Persistent Configuration

For permanent changes, use direct operations:

```python
config = load_config()
config.update(permanent_changes)
save_config(config)
# Changes persist - no automatic revert
```

## Future Considerations

If temporary hook configuration is needed:

```python
# Hypothetical future use case
def test_with_temporary_hooks():
    with SettingsManager() as settings:  # OK for temporary testing
        settings.add_test_hooks()
        run_integration_tests()
        # On exit: test hooks removed automatically
```

Key difference: Explicitly intended as temporary, clearly documented as such.

## Related Documentation

- [Changelog v0.9.1](../CHANGELOG_v0.9.1.md) - Complete fix details
- [Hook Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) - Hook setup and persistence
- [Troubleshoot Hooks](../howto/troubleshoot-hooks.md) - Diagnosing hook issues
