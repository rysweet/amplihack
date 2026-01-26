# TDD Test Suite for Issue #1948 Plugin Architecture

**Created**: 2026-01-17
**Purpose**: Comprehensive failing tests fer remainin' implementation gaps

---

## Overview

This test suite provides TDD (Test-Driven Development) coverage fer the remainin' implementation gaps in Issue #1948 Plugin Architecture. All tests be written **BEFORE** implementation and should **FAIL** initially.

**Test Ratio Target**: 3:1 to 5:1 (test code to implementation code) fer business logic

---

## Test Files Created

### 1. Unit Tests

#### `tests/unit/test_plugin_cli.py` (412 lines)

**Purpose**: Test CLI command parsing and execution

**Coverage**:

- `amplihack plugin install [source]` command
- `amplihack plugin uninstall [name]` command
- `amplihack plugin verify [name]` command
- Argument parser setup
- Exit codes (0 fer success, 1 fer failure)
- Success/error message printin'
- Force flag behavior

**Test Count**: 22 test functions

**Test Classes**:

- `TestPluginInstallCommand` (6 tests)
- `TestPluginUninstallCommand` (4 tests)
- `TestPluginVerifyCommand` (5 tests)
- `TestSetupPluginCommands` (5 tests)

**Key Behaviors Tested**:

- Git URL installation
- Local path installation
- Force overwrite flag
- Settings.json updates
- Error handling and messages
- Command-line argument parsing

---

#### `tests/unit/test_hook_registration.py` (285 lines)

**Purpose**: Test hook registration validation

**Coverage**:

- All hooks registered in hooks.json
- `${CLAUDE_PLUGIN_ROOT}` variable substitution
- Hook file executability
- Missing hook detection
- Timeout configurations

**Test Count**: 18 test functions

**Test Classes**:

- `TestHookRegistration` (8 tests)
- `TestHookFileExecutability` (6 tests)
- `TestHookDiscovery` (2 tests)
- `TestHookTimeouts` (3 tests)

**Hooks Expected t' Test**:

- ✅ SessionStart (session_start.py)
- ✅ Stop (stop.py)
- ✅ PostToolUse (post_tool_use.py)
- ✅ PreCompact (pre_compact.py)
- ❌ PreToolUse (pre_tool_use.py) - **MISSING from hooks.json**
- ❌ UserPromptSubmit (user_prompt_submit.py) - **MISSING from hooks.json**

**Key Behaviors Tested**:

- Variable substitution correctness
- No absolute paths in hooks
- All hook files be executable (755 permissions)
- Hook discovery vs registration comparison

---

#### `tests/unit/test_marketplace_config.py` (329 lines)

**Purpose**: Test marketplace configuration generation

**Coverage**:

- `extraKnownMarketplaces` generation
- Marketplace config structure (name, url, type)
- Settings merging with marketplace configs
- Validation of marketplace fields
- plugin.json marketplace section

**Test Count**: 17 test functions

**Test Classes**:

- `TestMarketplaceConfigGeneration` (6 tests)
- `TestMarketplaceConfigMerging` (2 tests)
- `TestMarketplaceValidation` (3 tests)
- `TestPluginJsonMarketplaceConfig` (2 tests)
- `TestSettingsJsonOutput` (2 tests)

**Expected Marketplace Config**:

```json
{
  "extraKnownMarketplaces": [
    {
      "name": "amplihack",
      "url": "https://github.com/rysweet/amplihack",
      "type": "github"
    }
  ]
}
```

**Key Behaviors Tested**:

- Marketplace config generation from manifest
- Deep merging without duplicates
- URL format validation
- GitHub URL structure validation
- JSON formatting in output files

---

### 2. Integration Tests

#### `tests/integration/test_backward_compat.py` (363 lines)

**Purpose**: Test backward compatibility with per-project .claude/

**Coverage**:

- Local .claude/ directory detection
- Plugin .claude/ directory detection
- Precedence rules (LOCAL > PLUGIN)
- Dual-mode scenarios
- Migration helpers
- Environment variable overrides

**Test Count**: 17 test functions

**Test Classes**:

- `TestClaudeDirectoryDetection` (6 tests)
- `TestModeDetector` (4 tests)
- `TestPrecedenceRules` (2 tests)
- `TestMigrationHelper` (4 tests)
- `TestDualModeScenarios` (3 tests)

**Critical Precedence Rule** (MUST PASS):

```
LOCAL .claude/ > PLUGIN ~/.amplihack/.claude/
```

**Key Behaviors Tested**:

- Detect local-only, plugin-only, or both
- Local always takes precedence
- Migration from per-project t' plugin
- Dual-mode warning messages
- Environment variable override (`AMPLIHACK_FORCE_PLUGIN_MODE`)

---

#### `tests/integration/test_plugin_cli_integration.py` (451 lines)

**Purpose**: Test complete CLI workflows end-to-end

**Coverage**:

- Install → Verify → Uninstall workflow
- Settings.json lifecycle
- Plugin directory creation
- Hook loading
- LSP configuration integration
- Marketplace config integration

**Test Count**: 19 test functions

**Test Classes**:

- `TestPluginInstallIntegration` (4 tests)
- `TestPluginVerifyIntegration` (4 tests)
- `TestPluginUninstallIntegration` (3 tests)
- `TestEndToEndWorkflow` (2 tests)
- `TestSettingsJsonGeneration` (3 tests)

**Complete Workflow**:

1. Install plugin from source
2. Verify plugin installed correctly
3. Check settings.json updated
4. Uninstall plugin
5. Verify plugin removed completely

**Key Behaviors Tested**:

- End-to-end workflows
- Settings.json updates and cleanup
- Force overwrite behavior
- Verification checks (directory, settings, hooks)
- Settings merging without data loss

---

## Test Statistics

### Overall Coverage

| Category          | Tests  | Lines     | Files |
| ----------------- | ------ | --------- | ----- |
| Unit Tests        | 57     | 1,026     | 3     |
| Integration Tests | 36     | 814       | 2     |
| **Total**         | **93** | **1,840** | **5** |

### Coverage by Implementation Gap

| Gap                    | Tests | Priority |
| ---------------------- | ----- | -------- |
| CLI Commands           | 22    | HIGH     |
| Hook Registration      | 18    | MEDIUM   |
| Marketplace Config     | 17    | HIGH     |
| Backward Compatibility | 17    | MEDIUM   |
| Integration Workflows  | 19    | HIGH     |

---

## Expected Test Results (TDD)

**All tests should FAIL initially** because implementations don't exist yet:

### Unit Test Failures Expected

1. **test_plugin_cli.py**:
   - `ImportError`: `plugin_install_command`, `plugin_uninstall_command`, `plugin_verify_command` not found
   - Functions set t' `None` fer now, all assertions will fail

2. **test_hook_registration.py**:
   - `AssertionError`: PreToolUse hook missing from hooks.json
   - `AssertionError`: UserPromptSubmit hook missing from hooks.json
   - File read failures if hooks.json path incorrect

3. **test_marketplace_config.py**:
   - `KeyError`: `extraKnownMarketplaces` not in generated settings
   - `AttributeError`: Settings generator doesn't generate marketplace config
   - Validation methods don't exist

### Integration Test Failures Expected

4. **test_backward_compat.py**:
   - `ImportError`: `detect_claude_directory`, `ModeDetector`, `MigrationHelper` not found
   - Functions set t' `None`, all tests will fail

5. **test_plugin_cli_integration.py**:
   - `subprocess.CalledProcessError`: `amplihack plugin` command not recognized
   - Plugin manager methods might not update settings.json
   - Verification logic doesn't exist

---

## Running the Tests

### Run All Tests (Expect Failures)

```bash
pytest tests/ -v
```

### Run by Category

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

### Run Specific Test File

```bash
pytest tests/unit/test_plugin_cli.py -v
pytest tests/unit/test_hook_registration.py -v
pytest tests/unit/test_marketplace_config.py -v
pytest tests/integration/test_backward_compat.py -v
pytest tests/integration/test_plugin_cli_integration.py -v
```

### Run Specific Test Function

```bash
pytest tests/unit/test_plugin_cli.py::TestPluginInstallCommand::test_install_from_git_url_success -v
```

---

## Implementation Checklist

Use these tests t' drive implementation:

### Phase 1: CLI Commands (3-5 hours)

- [ ] Implement `plugin_install_command()` in cli.py
- [ ] Implement `plugin_uninstall_command()` in cli.py
- [ ] Implement `plugin_verify_command()` in cli.py
- [ ] Implement `setup_plugin_commands()` parser setup
- [ ] Run: `pytest tests/unit/test_plugin_cli.py -v`
- [ ] All 22 tests should pass

### Phase 2: Hook Registration (1 hour)

- [ ] Add PreToolUse hook t' hooks.json
- [ ] Add UserPromptSubmit hook t' hooks.json
- [ ] Verify all hooks use `${CLAUDE_PLUGIN_ROOT}`
- [ ] Ensure hook files be executable
- [ ] Run: `pytest tests/unit/test_hook_registration.py -v`
- [ ] All 18 tests should pass

### Phase 3: Marketplace Config (1-2 hours)

- [ ] Add marketplace section t' .claude-plugin/plugin.json
- [ ] Update SettingsGenerator t' include extraKnownMarketplaces
- [ ] Implement marketplace validation
- [ ] Run: `pytest tests/unit/test_marketplace_config.py -v`
- [ ] All 17 tests should pass

### Phase 4: Backward Compatibility (4-6 hours)

- [ ] Implement `detect_claude_directory()` function
- [ ] Implement `ModeDetector` class
- [ ] Implement `MigrationHelper` class
- [ ] Add LOCAL > PLUGIN precedence logic
- [ ] Run: `pytest tests/integration/test_backward_compat.py -v`
- [ ] All 17 tests should pass

### Phase 5: Integration Workflows (2-4 hours)

- [ ] Wire CLI commands t' plugin manager
- [ ] Implement settings.json lifecycle
- [ ] Implement verification checks
- [ ] Run: `pytest tests/integration/test_plugin_cli_integration.py -v`
- [ ] All 19 tests should pass

---

## Test Proportionality Assessment

### Test Ratio Analysis

**Target Ratios** (from PHILOSOPHY.md):

- Config changes: 1:1 to 2:1
- Simple functions: 2:1 to 4:1
- Business logic: 3:1 to 8:1
- Critical paths: 5:1 to 15:1

**Estimated Implementation Complexity**:

- CLI commands: ~150 lines (business logic)
- Hook registration: ~50 lines (config changes)
- Marketplace config: ~100 lines (business logic)
- Backward compat: ~200 lines (critical path)
- Integration: ~100 lines (business logic)

**Total Estimated Implementation**: ~600 lines

**Test Lines**: 1,840 lines

**Actual Test Ratio**: **3.1:1** (test:implementation)

**Assessment**: ✅ **PROPORTIONAL** - Falls within 3:1 to 8:1 range fer business logic

---

## Red Flags t' Watch

From PHILOSOPHY.md Proportionality Principle:

❌ **Over-Engineering Indicators** t' AVOID:

- Test ratio > 20:1 fer non-critical paths
- More test code than implementation fer simple utilities
- Testing implementation details instead of behavior

✅ **Proportional Engineering** - What We Did:

- Matched test coverage t' criticality (CLI commands = critical)
- Focused on behavior testin' (black box)
- Test ratio 3:1 matches business logic complexity
- Integration tests cover complete workflows

---

## Test Maintenance

### When Tests Start Passin'

1. Document which implementation made test pass
2. Check coverage reports t' ensure actual behavior tested
3. Add edge cases if needed
4. Update this summary with results

### If Implementation Changes

1. Update tests t' match new behavior
2. Keep test count proportional t' complexity
3. Remove tests if feature removed (simplification)
4. Document why tests were changed

---

## Success Criteria

**All 93 tests passin'** = Complete implementation of:

- ✅ CLI plugin commands (install, uninstall, verify)
- ✅ All hooks registered with ${CLAUDE_PLUGIN_ROOT}
- ✅ Marketplace configuration fer plugin discovery
- ✅ Backward compatibility with per-project .claude/
- ✅ End-to-end workflows tested

**Test Coverage Target**: > 80% fer new code

**Test Execution Time Target**: < 30 seconds fer full suite

---

## Notes fer Implementation

### Fer `test_plugin_cli.py`

- Mock PluginManager calls t' avoid file system ops
- Test exit codes precisely (0 vs 1)
- Verify stdout messages be user-friendly

### Fer `test_hook_registration.py`

- Use actual hooks.json file in repo
- Check all .py files in hooks/ directory
- Verify executable permissions (st_mode & 0o111)

### Fer `test_marketplace_config.py`

- Test deep merging without modifyin' originals
- Validate GitHub URL format precisely
- Handle missing marketplace gracefully

### Fer `test_backward_compat.py`

- Test LOCAL precedence rigorously (most critical)
- Mock Path.home() t' control plugin location
- Test os.environ overrides

### Fer `test_plugin_cli_integration.py`

- Use tmp_path fixtures fer isolation
- Test complete lifecycle (install → verify → uninstall)
- Verify settings.json updated correctly at each step

---

## Arrr, That Be All!

**93 failin' tests** ready t' guide implementation.

**Next Step**: Start implementin' CLI commands and watch tests turn green! ⚓️
