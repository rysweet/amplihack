# Module: Test Ordering Strategy

## Purpose

Ensure syntax validation tests run FIRST before any other tests. Fail fast on syntax errors to save CI time and provide immediate feedback.

## Contract

### Inputs
- **pytest configuration**: `pytest.ini` or `pyproject.toml`
- **Test marks**: Applied to test functions/classes

### Outputs
- **Test execution order**: Syntax tests → Performance → Edge cases → Integration → All others
- **Fast failure**: Exit on first syntax error (optional)

### Side Effects
- Modifies test execution order
- May add pytest plugin dependency (`pytest-order`)

## Dependencies

### Option 1: pytest-order (Recommended)
- **Package**: `pytest-order`
- **Install**: `pip install pytest-order`
- **Pros**: Explicit, clear, well-maintained
- **Cons**: Adds dependency

### Option 2: pytest built-in markers + naming
- **Package**: None (built-in)
- **Pros**: No dependency
- **Cons**: Less explicit, relies on naming conventions

**Recommendation**: Use pytest-order for explicit control and clarity.

## Implementation Notes

### Test Ordering Hierarchy

```python
# Order 1: Syntax Validation (Fail Fast)
@pytest.mark.order(1)
class TestSyntaxValidation:
    """Basic syntax checking - run first."""

    def test_valid_file_passes(self):
        pass

    def test_syntax_error_detected(self):
        pass

# Order 2: Performance Tests
@pytest.mark.order(2)
class TestSyntaxValidationPerformance:
    """Performance SLA tests - run after basic validation."""

    def test_50_files_under_500ms(self):
        pass

# Order 3: Edge Cases
@pytest.mark.order(3)
class TestSyntaxEdgeCases:
    """Edge case handling - run after performance."""

    def test_valid_code_with_equals(self):
        pass

    def test_valid_code_with_angle_brackets(self):
        pass

# Order 4: Integration Tests
@pytest.mark.order(4)
class TestPreCommitIntegration:
    """Full pre-commit integration - run last."""

    def test_pre_commit_hook_execution(self):
        pass
```

### Pytest Configuration

**In `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
# Run tests in order specified by @pytest.mark.order
addopts = [
    "--strict-markers",
    "--order-scope=session",  # Global ordering
]

markers = [
    "order: specify test execution order",
    "syntax: syntax validation tests",
    "performance: performance tests",
    "edge_case: edge case tests",
]
```

**Or in `pytest.ini`:**
```ini
[pytest]
addopts =
    --strict-markers
    --order-scope=session

markers =
    order: specify test execution order
    syntax: syntax validation tests
    performance: performance tests
    edge_case: edge case tests
```

### Fail-Fast Strategy (Optional)

**Option A: Exit on First Failure**
```bash
pytest -x  # Stop after first failure
```

**Option B: Exit on First Syntax Failure Only**
```python
# In conftest.py
def pytest_runtest_makereport(item, call):
    """Stop test run if syntax test fails."""
    if call.excinfo is not None:
        if "syntax" in item.keywords:
            pytest.exit("Syntax test failed - stopping test run")
```

**Recommendation**: Don't implement Option B initially. Let users use `-x` flag if desired. Keep it simple.

### Test Discovery Order

Ensure pytest discovers tests in correct order:

```
tests/
├── test_01_syntax.py           # Order 1
├── test_02_performance.py      # Order 2
├── test_03_edge_cases.py       # Order 3
├── test_04_integration.py      # Order 4
└── test_other.py               # No order (runs last)
```

Naming convention helps but `@pytest.mark.order()` is authoritative.

## Test Requirements

### Functional Tests
1. **Order verification**: Test that syntax tests run before others
2. **Marker presence**: Verify all syntax tests have `@pytest.mark.order(1)`
3. **Configuration**: Verify pytest.ini/pyproject.toml has correct settings

### Integration Tests
1. **Full test run**: Verify order is maintained in full suite run
2. **Subset run**: Verify order works with `pytest -k syntax`
3. **Parallel run**: Verify order works with `pytest -n auto` (pytest-xdist)

### Edge Cases
1. **No pytest-order**: Graceful degradation if dependency missing
2. **Order conflicts**: Two tests with same order number
3. **Filtered run**: `pytest tests/test_syntax.py` respects order

## Success Metrics

1. **Syntax tests always run first**: 100% of test runs
2. **Fast feedback**: Syntax errors found in < 1s
3. **Clear output**: Test order visible in pytest output
4. **No surprises**: Order behavior is predictable and documented

## Alternative: Built-in Approach (No Dependencies)

If avoiding pytest-order dependency:

```python
# Use alphabetical naming + session scope
# tests/test_a_syntax.py - runs first alphabetically
# tests/test_z_integration.py - runs last alphabetically

# Less explicit but works without dependencies
```

**Trade-off**: Less clear intent, harder to maintain, but zero dependencies.

## Rollout Strategy

1. **Phase 1**: Add pytest-order dependency
2. **Phase 2**: Add `@pytest.mark.order()` to existing tests
3. **Phase 3**: Update pytest configuration
4. **Phase 4**: Verify in CI
5. **Phase 5**: Document in README/CONTRIBUTING

## Documentation Requirements

### In test file docstrings:
```python
"""
Test Execution Order
--------------------
1. Syntax validation (fail fast)
2. Performance tests (SLA validation)
3. Edge cases (comprehensive coverage)
4. Integration tests (full workflow)

Tests are ordered using pytest-order plugin.
See: https://pytest-order.readthedocs.io/
"""
```

### In README:
```markdown
## Running Tests

Tests run in priority order:
1. **Syntax validation** - Catches basic errors fast
2. **Performance tests** - Ensures SLAs met
3. **Edge cases** - Comprehensive coverage
4. **Integration** - Full workflow validation

To run only syntax tests:
```bash
pytest -m syntax
```

To stop on first failure:
```bash
pytest -x
```
```
