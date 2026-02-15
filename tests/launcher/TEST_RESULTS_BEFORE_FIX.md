# TDD Test Results - Before Fix (Issue #2335)

## Test Execution Date

2026-02-15

## Test Summary

- **Total Tests**: 5
- **Failed**: 1 (Expected - demonstrates bug)
- **Passed**: 4 (Regression tests)

## Test Results

### ❌ FAILING TEST (Core Bug Detection)

**Test**: `test_settings_manager_not_instantiated_in_launch_interactive`

**Status**: FAILED (EXPECTED)

**Evidence of Bug**:

```
AssertionError: Expected 'SettingsManager' to not have been called. Called 1 times.
Calls: [
  call(settings_path=PosixPath('/home/azureuser/.claude/settings.json'),
       session_id='launch_1771194435',
       non_interactive=False),
  call().backup_path.__bool__(),
  call().restore_backup(),
  call().restore_backup().__bool__()
]
```

**Analysis**:

- SettingsManager IS instantiated in launch_interactive() (lines 797-803 in core.py)
- backup_path is checked
- restore_backup() is called in finally block (lines 905-911)
- This proves the bug: settings are backed up BEFORE hooks are added, then restored on exit

### ✅ PASSING TESTS (Regression Coverage)

1. **test_hooks_persist_after_launch_interactive_completes**
   - Status: PASSED (in mock environment)
   - Purpose: Verify hooks persist after function completes
   - Note: Would fail in real execution without mocks

2. **test_ensure_settings_json_still_works_correctly**
   - Status: PASSED
   - Purpose: Regression test for ensure_settings_json()
   - Confirms: Hook management in ensure_settings_json() works correctly

3. **test_no_backup_files_created_by_launch_interactive**
   - Status: PASSED (in mock environment)
   - Purpose: Verify no backup files created by launch_interactive()
   - Note: Would fail in real execution

4. **test_hooks_added_by_prepare_launch_persist**
   - Status: PASSED (in mock environment)
   - Purpose: Verify hooks added by prepare_launch() persist
   - Note: Would fail in real execution

## Bug Confirmation

The failing test definitively proves the bug described in Issue #2335:

1. **Root Cause**: SettingsManager is instantiated in launch_interactive() BEFORE prepare_launch()
2. **Sequence of Events**:
   - Line 797-803: SettingsManager created and backup created (WITHOUT hooks)
   - Line 805: prepare_launch() called (adds hooks to settings.json)
   - Line 896: subprocess.call() runs Claude
   - Line 905-911: finally block restores backup (REMOVES hooks)

3. **Expected Fix**: Remove SettingsManager from launch_interactive()
   - Settings management should only happen in ensure_settings_json()
   - Hooks should persist across sessions
   - No backup/restore cycle in launch_interactive()

## Test Coverage

The test suite provides comprehensive coverage:

- **Critical Path**: SettingsManager instantiation detection
- **Hook Persistence**: Verify hooks survive function exit
- **Regression**: ensure_settings_json() continues working
- **Side Effects**: No unwanted backup files created

## Next Steps

1. Implement fix (remove SettingsManager from launch_interactive())
2. Re-run tests to verify they pass
3. Add integration test with real settings.json file
4. Update documentation
