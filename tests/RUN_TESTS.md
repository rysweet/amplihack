# How to Run Stop Hook Visibility Tests

## Quick Start

Run all tests with a single command:

```bash
# From project root
python tests/manual_test_stop_hook_visibility.py
```

Expected output: "🎉 ALL TESTS PASSED! The visibility fix is working correctly."

## Individual Test Suites

### 1. Unit Tests - Reflection Imports

Tests that reflection module imports work without errors.

```bash
python -m unittest tests.test_reflection_imports -v
```

**What it tests:**

- Reflection module can be imported
- analyze_session_patterns function exists
- process_reflection_analysis function exists
- All exported functions are callable
- Import paths work from different contexts

**Expected:** All tests pass, ~15 tests total

---

### 2. Critical Scenario Tests

Tests the exact bug scenarios that were broken.

```bash
python -m unittest tests.test_stop_hook_critical_scenarios -v
```

**What it tests:**

- CRITICAL: Empty learnings + existing decisions returns message
- CRITICAL: Output dict initialized before decision_summary
- CRITICAL: extract_learnings imports correctly from reflection
- Output dict structure validation (JSON serializable)
- Integration tests for complete flow

**Expected:** All tests pass, ~20 tests total

---

### 3. E2E Visibility Tests

Tests end-to-end user-facing visibility.

```bash
python -m unittest tests.test_stop_hook_e2e_visibility -v
```

**What it tests:**

- Decision records appear in hook output
- Output displays when stopping session
- Hook output serializes to JSON
- Decision file links are clickable
- Real-world user scenarios
- Regression prevention for all three bugs

**Expected:** All tests pass, ~15 tests total

---

### 4. Decision Summary Tests (Existing)

Comprehensive tests for display_decision_summary() method.

```bash
python -m unittest tests.test_stop_hook_decision_summary -v
```

**What it tests:**

- Valid DECISIONS.md file handling
- Empty file scenarios
- Malformed decision records
- File path generation
- Error handling (permissions, encoding)
- Execution order validation

**Expected:** All tests pass, ~20 tests total

---

## Run All Tests at Once

```bash
# Using unittest discovery
python -m unittest discover tests -p "test_*hook*.py" -v
python -m unittest discover tests -p "test_*reflection*.py" -v

# Or run specific test files
python -m unittest \
    tests.test_reflection_imports \
    tests.test_stop_hook_critical_scenarios \
    tests.test_stop_hook_e2e_visibility \
    tests.test_stop_hook_decision_summary \
    -v
```

---

## Run Specific Test Class

```bash
# Example: Run only critical scenario A tests
python -m unittest tests.test_stop_hook_critical_scenarios.TestStopHookCriticalScenarioA -v

# Example: Run only E2E visibility tests
python -m unittest tests.test_stop_hook_e2e_visibility.TestStopHookE2EVisibility -v
```

---

## Run Single Test Method

```bash
# Example: Test the exact bug scenario
python -m unittest tests.test_stop_hook_critical_scenarios.TestStopHookCriticalScenarioA.test_empty_learnings_with_existing_decisions_returns_message -v

# Example: Test reflection imports
python -m unittest tests.test_reflection_imports.TestReflectionImports.test_reflection_module_imports_without_error -v
```

---

## Manual Testing

The manual test script provides a user-friendly way to verify the fix:

```bash
python tests/manual_test_stop_hook_visibility.py
```

**Output includes:**

- ✅ Test 1: Reflection module imports
- ✅ Test 2: Decision summary visibility (with empty learnings)
- ✅ Test 3: Output dict initialization
- Summary with pass/fail count

---

## Test Coverage Report

See detailed coverage analysis:

```bash
cat tests/TEST_COVERAGE_ANALYSIS.md
```

**Coverage Metrics:**

- Unit Tests: ~65% (target: 60%)
- Integration Tests: ~30% (target: 30%)
- E2E Tests: ~5% (target: 10%)
- Critical Path Coverage: 100%
- Edge Case Coverage: 100%

---

## Troubleshooting

### Tests Timeout

Some tests may timeout if they trigger AI reflection analysis. This is expected.

**Solution:**

- Set environment variable to disable reflection during tests:
  ```bash
  export REFLECTION_ENABLED=false
  python -m unittest tests.test_stop_hook_critical_scenarios -v
  ```

### ImportError

If you get import errors, ensure you're in the project root:

```bash
cd /Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding
python -m unittest tests.test_reflection_imports -v
```

### pytest Not Found

These tests use unittest (Python standard library), not pytest:

```bash
# Don't use pytest
python -m unittest tests.test_reflection_imports -v  # ✅ Correct

# pytest is not required
pytest tests/test_reflection_imports.py  # ❌ Won't work without pytest
```

---

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Test Stop Hook Visibility Fix
  run: |
    python -m unittest tests.test_reflection_imports
    python -m unittest tests.test_stop_hook_critical_scenarios
    python -m unittest tests.test_stop_hook_e2e_visibility
```

---

## Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run critical tests before commit
python -m unittest tests.test_stop_hook_critical_scenarios || exit 1
```

---

## Expected Test Results

All tests should pass with output similar to:

```
----------------------------------------------------------------------
Ran 50 tests in 2.345s

OK
```

If any test fails, it indicates a regression of the visibility fix.

---

## Quick Verification

Just want to verify the fix works? Run the manual test:

```bash
python tests/manual_test_stop_hook_visibility.py
```

Expected output (< 5 seconds):

```
🎉 ALL TESTS PASSED! The visibility fix is working correctly.
```

---

## Test File Locations

All test files are in the `tests/` directory:

- `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/tests/test_reflection_imports.py`
- `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/tests/test_stop_hook_critical_scenarios.py`
- `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/tests/test_stop_hook_e2e_visibility.py`
- `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/tests/test_stop_hook_decision_summary.py`
- `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/tests/manual_test_stop_hook_visibility.py`

Documentation:

- `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/tests/TEST_COVERAGE_ANALYSIS.md`
- `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/tests/RUN_TESTS.md` (this file)
