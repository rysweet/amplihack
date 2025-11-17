# Neo4j Post-Session Prompt Fix

## Problem

Neo4j was prompting users for database setup AFTER the session ended, creating a confusing user experience where questions appeared after Claude Code had already terminated the session.

## Root Cause

The issue occurred due to a **defense-in-depth gap** in the cleanup flow:

1. ✅ `stop.py` sets `AMPLIHACK_CLEANUP_MODE=1` environment variable (line 227)
2. ✅ `container_selection.resolve_container_name()` checks for this flag and returns default without prompting (lines 336-346) - **Primary Protection**
3. ❌ **Gap Found**: At line 360, when calling `unified_container_and_credential_dialog()`, it hardcoded `auto_mode=False`
4. ❌ **Vulnerability**: If neo4j config is initialized from anywhere other than through `resolve_container_name()`, prompts could still appear

### Code Flow Analysis

```
stop.py:_handle_neo4j_cleanup()
  ↓
os.environ["AMPLIHACK_CLEANUP_MODE"] = "1"  ✅ Sets flag
  ↓
Neo4jConnectionTracker.__init__()
  ↓
get_config()  # May reinitialize config
  ↓
config.py:Neo4jConfig.from_environment()
  ↓
container_selection.resolve_container_name()
  ↓
Lines 336-346: Check cleanup mode → return default ✅ Primary protection
  ↓ (if bypassed)
Line 360: unified_container_and_credential_dialog(auto_mode=False) ❌ Gap!
  ↓
unified_startup_dialog.py: Shows interactive prompts 😱
```

## Solution: Defense-in-Depth

Added **secondary protection layer** at the dialog invocation point (line 360):

### Implementation

**File**: `src/amplihack/memory/neo4j/container_selection.py`

**Before (Vulnerable)**:

```python
container_name = unified_container_and_credential_dialog(default_name, auto_mode=False)
```

**After (Defense-in-Depth)**:

```python
# Defense-in-depth: Check cleanup mode again as secondary protection
# (Primary check at lines 336-346, this prevents prompts if that check is bypassed)
# This ensures no interactive prompts during session cleanup regardless of code path
cleanup_mode_check = os.getenv("AMPLIHACK_CLEANUP_MODE", "0") == "1"
dialog_auto_mode = context.auto_mode or cleanup_mode_check
container_name = unified_container_and_credential_dialog(default_name, auto_mode=dialog_auto_mode)
```

### Protection Layers

| Layer         | Location      | Purpose                                               |
| ------------- | ------------- | ----------------------------------------------------- |
| **Primary**   | Lines 336-346 | Early return when cleanup mode detected               |
| **Secondary** | Lines 363-365 | Force auto_mode=True when calling dialog              |
| **Tertiary**  | stop.py:227   | Set AMPLIHACK_CLEANUP_MODE flag before any operations |

## Testing

Comprehensive test suite added to `tests/memory/neo4j/test_container_selection.py`:

### Test Class: `TestCleanupModeIntegration` (9 tests)

1. **test_cleanup_mode_forces_auto_mode**: Verifies `AMPLIHACK_CLEANUP_MODE=1` forces auto_mode
2. **test_normal_mode_respects_interactive_setting**: Verifies normal interactive mode works
3. **test_context_auto_mode_true_always_non_interactive**: Verifies context.auto_mode respected
4. **test_cleanup_mode_unset_defaults_to_interactive**: Verifies default behavior
5. **test_cleanup_mode_and_auto_mode_both_true**: Verifies both flags work together
6. **test_cleanup_mode_with_cli_arg_skips_dialog**: Verifies CLI priority
7. **test_cleanup_mode_with_env_var_skips_dialog**: Verifies env var priority
8. **test_cleanup_mode_dialog_fallback_on_error**: Verifies graceful error handling
9. **test_cleanup_mode_dialog_returns_none**: Verifies None return handling

### Test Coverage Matrix

| cleanup_mode | context.auto_mode | Expected behavior              | Test coverage                                         |
| ------------ | ----------------- | ------------------------------ | ----------------------------------------------------- |
| False        | False             | Interactive dialog             | ✅ test_normal_mode_respects_interactive_setting      |
| False        | True              | Auto mode, no prompt           | ✅ test_context_auto_mode_true_always_non_interactive |
| True         | False             | No prompt (Layer 1 OR Layer 2) | ✅ test_cleanup_mode_forces_auto_mode                 |
| True         | True              | No prompt (both layers)        | ✅ test_cleanup_mode_and_auto_mode_both_true          |
| unset        | False             | Interactive dialog             | ✅ test_cleanup_mode_unset_defaults_to_interactive    |

## Verification

### Expected Behavior After Fix

| Scenario                          | Before Fix                                | After Fix                                   |
| --------------------------------- | ----------------------------------------- | ------------------------------------------- |
| Session exit with neo4j running   | 😱 Prompts user after session ends        | ✅ Silently checks/shuts down, no prompts   |
| Auto mode                         | ✅ No prompts                             | ✅ No prompts (unchanged)                   |
| Interactive mode (normal startup) | ✅ Shows dialog                           | ✅ Shows dialog (unchanged)                 |
| Cleanup mode + any code path      | ❌ Could show prompts if Layer 1 bypassed | ✅ Never shows prompts (Layer 2 protection) |

### User Preference Integration

The fix respects the user's neo4j_auto_shutdown preference:

- `always`: Auto-shutdown without prompt (already working)
- `never`: Skip shutdown without prompt (already working)
- `ask`: Check for cleanup mode, suppress prompt during cleanup ✅ FIXED

## Philosophy Compliance

- ✅ **Ruthless Simplicity**: Minimal change (3 lines), maximum protection
- ✅ **Zero-BS Implementation**: No placeholders, complete solution
- ✅ **Defense-in-Depth**: Multiple protection layers prevent failures
- ✅ **Clear Intent**: Comments explain purpose and protection strategy

## Related Issues

- User report: "neo4j is asking the user questions about database setup AFTER the session ends"
- User preference: neo4j_auto_shutdown = "always" (should never prompt)
- Expected behavior: No prompts during session cleanup

## Files Modified

1. `src/amplihack/memory/neo4j/container_selection.py` (lines 360-365) - Added defense-in-depth protection
2. `tests/memory/neo4j/test_container_selection.py` (9 new tests) - Comprehensive test coverage

## No Breaking Changes

✅ All existing functionality preserved:

- Interactive mode works normally when not in cleanup
- Auto mode works as before
- CLI and env var priority unchanged
- Error handling unchanged
- User preference system unchanged

## Summary

The fix adds a **secondary protection layer** that ensures no interactive prompts can occur during session cleanup, even if the primary protection layer is somehow bypassed. This defense-in-depth approach provides robust protection while maintaining backward compatibility with all existing functionality.

The user will no longer see database setup questions after the session ends, regardless of how the neo4j components are initialized during cleanup.
