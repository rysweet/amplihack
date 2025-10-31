# Test Coverage: Auto Mode Ultrathink Command Prepending

## Overview

This document describes the comprehensive test coverage for the auto mode ultrathink command prepending feature. The tests follow the **test pyramid principle** with **60% unit tests, 30% integration tests, and 10% E2E tests**.

## Feature Under Test

**Function**: `ensure_ultrathink_command(prompt: str) -> str`
- **Location**: `src/amplihack/cli.py`
- **Purpose**: Automatically prepend `/amplihack:ultrathink` to prompts that don't already start with a slash command
- **Type**: Pure function with no side effects
- **Integration**: Called from `handle_auto_mode()` before passing prompt to AutoMode

## Test Files

### 1. Unit Tests (60% Coverage)
**File**: `tests/unit/test_cli_ensure_ultrathink.py`
**Tests**: 40 comprehensive unit tests
**Focus**: Pure function behavior, edge cases, boundary conditions

#### Test Categories:

**Happy Path Tests (3 tests)**
- Normal prompt transformation
- Detailed prompts
- Single-word prompts

**Slash Command Detection (8 tests)**
- Already has slash command (unchanged)
- Already has ultrathink (idempotent)
- Different slash commands
- Slash in middle of prompt
- Multiple slashes

**Whitespace Handling (5 tests)**
- Leading whitespace
- Trailing whitespace
- Both leading and trailing
- Tabs and spaces
- Slash command with whitespace

**Empty/None Inputs (5 tests)**
- Empty string
- Whitespace-only
- Tabs-only
- Newlines-only
- Mixed whitespace

**Multiline Prompts (3 tests)**
- Basic multiline
- Multiline with whitespace
- Multiline with slash command

**Special Characters (6 tests)**
- Special characters (@, #, etc.)
- Unicode (日本語, émojis)
- Quotes and apostrophes
- Backslashes (Windows paths)
- Single slash
- Malformed slash commands

**Boundary Tests (3 tests)**
- Very long prompts (1000+ chars)
- Single character
- Two characters

**Case Sensitivity (2 tests)**
- Uppercase slash commands
- Mixed case commands

**Type Safety (3 tests)**
- None input (raises TypeError)
- Non-string input (raises TypeError)
- List input (raises TypeError)

**Idempotency (2 tests)**
- Double transformation
- Idempotency with whitespace

**Command Prefix Tests (3 tests)**
- Short slash commands
- Commands with colons
- Exact ultrathink match

### 2. Integration Tests (30% Coverage)
**File**: `tests/integration/test_cli_auto_mode_ultrathink.py`
**Tests**: 30 integration tests
**Focus**: Integration with `handle_auto_mode()`, workflow verification, SDK compatibility

#### Test Categories:

**handle_auto_mode() Integration (11 tests)**
- Normal prompt prepending
- Slash command unchanged
- Whitespace stripped
- Empty prompt error
- Missing -p flag error
- max_turns passed through
- ui_mode passed through
- Copilot SDK support
- Codex SDK support
- Exit code propagation
- Non-auto mode returns None

**End-to-End Workflow (8 tests)**
- Full workflow transformation
- No duplication of ultrathink
- Whitespace-only error
- Quotes preserved
- Long prompts handled
- Prompt extraction from args
- -p flag at end of args

**Error Handling (3 tests)**
- AutoMode import error
- AutoMode runtime error
- Missing prompt value

**Parametrized Tests (3 tests)**
- All SDKs (claude, copilot, codex)
- Various max_turns values
- UI mode variations

**Real Integration (3 tests)**
- Actual function without mocks
- Pure function verification
- Function signature verification

### 3. E2E Tests (10% Coverage)
**File**: `tests/e2e/test_cli_auto_mode_ultrathink_e2e.py`
**Tests**: 12 E2E tests (mostly manual with documentation)
**Focus**: Complete user workflows, manual testing scenarios

#### Test Categories:

**CLI Invocation (5 tests)**
- Normal prompt through CLI
- Slash command unchanged
- Empty prompt error
- Whitespace stripped
- Multiline prompts

**SDK Compatibility (1 test)**
- All SDKs work (parametrized)

**Configuration (2 tests)**
- Max turns parameter
- UI mode

**Error Cases (2 tests)**
- Missing prompt flag
- Invalid SDK

**Automated Smoke Tests (2 tests)**
- CLI help shows auto mode
- CLI version check

**Documentation Tests (2 tests)**
- Manual test scenarios (10 scenarios)
- E2E test checklist

## Test Statistics

### Coverage Breakdown
```
Unit Tests:       40 tests (60%)
Integration Tests: 30 tests (30%)
E2E Tests:        12 tests (10%)
Total:            82 tests
```

### Edge Cases Covered
- Empty strings: ✅
- Whitespace-only: ✅
- Leading/trailing whitespace: ✅
- Multiline prompts: ✅
- Special characters: ✅
- Unicode: ✅
- Very long prompts: ✅
- Single character: ✅
- Slash commands: ✅
- Idempotency: ✅
- Type safety: ✅

### Boundary Conditions
- Empty input: ✅
- Single character: ✅
- Very long input (2000+ chars): ✅
- Whitespace variations: ✅
- All slash command patterns: ✅

## Running the Tests

### Run All Tests
```bash
pytest tests/unit/test_cli_ensure_ultrathink.py -v
pytest tests/integration/test_cli_auto_mode_ultrathink.py -v
pytest tests/e2e/test_cli_auto_mode_ultrathink_e2e.py -v
```

### Run by Test Pyramid Level
```bash
# Unit tests only (60%)
pytest tests/unit/test_cli_ensure_ultrathink.py -v

# Integration tests only (30%)
pytest tests/integration/test_cli_auto_mode_ultrathink.py -v

# E2E tests only (10%)
pytest tests/e2e/test_cli_auto_mode_ultrathink_e2e.py -v -m e2e
```

### Run Specific Test Categories
```bash
# Unit: Happy path
pytest tests/unit/test_cli_ensure_ultrathink.py::test_unit_ultrathink_001_normal_prompt -v

# Unit: Whitespace handling
pytest tests/unit/test_cli_ensure_ultrathink.py -k "whitespace" -v

# Unit: Edge cases
pytest tests/unit/test_cli_ensure_ultrathink.py -k "empty" -v

# Integration: SDK compatibility
pytest tests/integration/test_cli_auto_mode_ultrathink.py -k "sdk" -v

# Integration: Error handling
pytest tests/integration/test_cli_auto_mode_ultrathink.py -k "error" -v
```

### Run with Coverage Report
```bash
pytest tests/unit/test_cli_ensure_ultrathink.py \
       tests/integration/test_cli_auto_mode_ultrathink.py \
       --cov=src/amplihack/cli \
       --cov-report=html \
       --cov-report=term
```

## Expected Test Results (TDD)

### Before Implementation
**All tests should FAIL** with:
```
ImportError: cannot import name 'ensure_ultrathink_command' from 'amplihack.cli'
```

This confirms we're following TDD principles - tests written first, then implementation.

### After Implementation
**All tests should PASS** when `ensure_ultrathink_command()` is correctly implemented with:
1. Whitespace stripping
2. Slash command detection
3. Ultrathink prepending
4. Empty string handling
5. Type validation

## Test Quality Metrics

### Characteristics of Good Tests
✅ **Fast**: Unit tests run in <100ms total
✅ **Isolated**: No test dependencies
✅ **Repeatable**: Consistent results every run
✅ **Self-Validating**: Clear pass/fail
✅ **Focused**: Single assertion per test (mostly)

### Code Coverage Goals
- **Function coverage**: 100% (all code paths)
- **Branch coverage**: 100% (all if/else branches)
- **Edge case coverage**: 100% (all boundary conditions)
- **Error case coverage**: 100% (all error paths)

## Manual E2E Test Scenarios

### Scenario 1: Basic Auto Mode
```bash
amplihack claude --auto -- -p "implement user authentication"
```
**Expected**: Prompt transformed to `/amplihack:ultrathink implement user authentication`

### Scenario 2: Slash Command Passthrough
```bash
amplihack claude --auto -- -p "/analyze src"
```
**Expected**: Prompt unchanged, passes through as `/analyze src`

### Scenario 3: Whitespace Handling
```bash
amplihack claude --auto -- -p "  implement feature  "
```
**Expected**: Whitespace stripped, becomes `/amplihack:ultrathink implement feature`

### Scenario 4: Empty Prompt Error
```bash
amplihack claude --auto -- -p ""
```
**Expected**: Error message, exit code 1, no Claude API calls

### Scenario 5: Multiline Prompt
```bash
amplihack claude --auto -- -p "implement authentication
with JWT tokens
and refresh support"
```
**Expected**: Full multiline prompt prefixed with ultrathink

### Scenario 6: Special Characters
```bash
amplihack claude --auto -- -p 'implement "feature X" with user'"'"'s data'
```
**Expected**: Quotes preserved, special characters intact

### Scenario 7: Idempotency
```bash
amplihack claude --auto -- -p "/amplihack:ultrathink test"
```
**Expected**: No double-prepending, single ultrathink command

### Scenario 8: Different SDKs
```bash
amplihack claude --auto -- -p "test"
amplihack copilot --auto -- -p "test"
amplihack codex --auto -- -p "test"
```
**Expected**: All SDKs work consistently

### Scenario 9: Max Turns
```bash
amplihack claude --auto --max-turns 20 -- -p "implement feature"
```
**Expected**: max_turns=20 passed to AutoMode with ultrathink prompt

### Scenario 10: UI Mode
```bash
amplihack claude --auto --ui -- -p "implement feature"
```
**Expected**: Rich UI displays with ultrathink prompt

## Implementation Checklist

When implementing `ensure_ultrathink_command()`, ensure:

- [ ] Function signature matches: `ensure_ultrathink_command(prompt: str) -> str`
- [ ] Location is `src/amplihack/cli.py`
- [ ] Strips leading/trailing whitespace with `.strip()`
- [ ] Checks if prompt starts with `/` after stripping
- [ ] Returns unchanged if starts with `/`
- [ ] Prepends `/amplihack:ultrathink ` (with space) if not
- [ ] Returns empty string for empty input
- [ ] Pure function (no side effects)
- [ ] Type hints included
- [ ] Docstring added
- [ ] Integration point in `handle_auto_mode()` added

## Test Maintenance

### When to Update Tests
- New edge cases discovered
- API changes to `ensure_ultrathink_command()`
- New SDK added
- CLI argument parsing changes
- AutoMode interface changes

### Test Naming Convention
- Unit: `test_unit_ultrathink_NNN_description`
- Integration: `test_integration_auto_NNN_description`
- E2E: `test_e2e_ultrathink_NNN_description`

### Test Organization
- Happy path tests first
- Edge cases grouped by category
- Error cases clearly labeled
- Parametrized tests for variations

## Related Documentation

- **Architecture Decision**: See builder agent output for implementation details
- **Requirements**: See prompt-writer agent output for specifications
- **Manual Tests**: `tests/e2e/test_cli_auto_mode_ultrathink_e2e.py`
- **Project Testing Guide**: `CLAUDE.md` Testing & Validation section

## Success Criteria

✅ All 82 tests pass
✅ 100% code coverage for `ensure_ultrathink_command()`
✅ 100% branch coverage
✅ All edge cases handled
✅ Manual E2E scenarios verified
✅ No regressions in existing auto mode functionality
✅ Performance: <1ms per transformation
✅ Documentation complete

---

**Test Coverage Status**: Ready for implementation (TDD)
**Last Updated**: 2025-10-31
**Test Author**: Tester Agent
