# Test Fix Template

**Usage**: 18% of all fixes - Assertion errors, mock setup issues, test data problems, coverage issues

## Problem Pattern Recognition

### Triggers

- Test suite failures
- Assert statement errors
- Mock/stub configuration issues
- Test data setup problems
- Coverage drops
- Flaky test behavior

### Error Indicators

```bash
# Common test error patterns
"AssertionError"
"AttributeError in test"
"Mock object has no attribute"
"Test data not found"
"Timeout in test"
"Race condition"
"setUp/tearDown failure"
```

## Quick Assessment (45 seconds)

### Step 1: Failure Scope

```bash
# Single test or multiple?
pytest --tb=short  # See quick failure summary
npm test -- --verbose  # Detailed test output

# Check failure pattern
grep -E "(FAILED|ERROR)" test_output | wc -l
```

### Step 2: Error Category

```bash
# Categorize test failure:
# - Assertion failures (logic/expected values)
# - Setup/teardown issues (test environment)
# - Mock/stub problems (test isolation)
# - Data issues (fixtures/test data)
# - Timing issues (async/race conditions)
# - Environment issues (external dependencies)
```

### Step 3: Impact Assessment

- **Critical**: Core functionality broken
- **Regression**: Previously working tests failing
- **Flaky**: Intermittent failures
- **New**: Tests for new functionality

## Solution Steps by Category

### Assertion Failures

```python
# Debug assertion failures
def test_calculation():
    result = calculate_total([10, 20, 30])
    # Add debugging
    print(f"Expected: 60, Got: {result}")
    assert result == 60

# Common fixes:
# 1. Update expected values if logic changed
# 2. Fix calculation logic if test is correct
# 3. Check floating point precision issues
```

### Mock Setup Issues

```python
# Before - problematic mock
@patch('module.external_service')
def test_service_call(mock_service):
    mock_service.return_value = "response"  # Wrong setup
    result = my_function()

# After - proper mock setup
@patch('module.external_service')
def test_service_call(mock_service):
    mock_service.return_value.json.return_value = {"status": "success"}
    mock_service.return_value.status_code = 200
    result = my_function()

    # Verify call was made correctly
    mock_service.assert_called_once_with(expected_params)
```

### Test Data Problems

```python
# Fix test data setup
@pytest.fixture
def sample_data():
    """Provide consistent test data"""
    return {
        "users": [
            {"id": 1, "name": "Test User", "email": "test@example.com"},
            {"id": 2, "name": "Another User", "email": "another@example.com"}
        ],
        "timestamp": datetime(2023, 1, 1, 12, 0, 0)  # Fixed timestamp
    }

def test_user_processing(sample_data):
    result = process_users(sample_data["users"])
    assert len(result) == 2
```

### Async/Timing Issues

```python
# Fix async test problems
import asyncio
import pytest

@pytest.mark.asyncio
async def test_async_function():
    # Use proper async testing
    result = await async_function()
    assert result == expected_value

# Fix timing issues
def test_with_delay():
    with patch('time.sleep'):  # Mock delays in tests
        result = function_with_delay()
        assert result == expected
```

### Environment Setup Issues

```python
# Fix test environment setup
class TestDatabaseOperations:
    def setup_method(self):
        """Setup fresh environment for each test"""
        self.db = create_test_database()
        self.db.create_tables()

    def teardown_method(self):
        """Clean up after each test"""
        self.db.drop_tables()
        self.db.close()

    def test_user_creation(self):
        user = self.db.create_user("test@example.com")
        assert user.email == "test@example.com"
```

## Validation Steps

### 1. Run Specific Test

```bash
# Test individual failure
pytest tests/test_specific.py::test_function -v
npm test -- --testNamePattern="specific test"

# Run with debugging
pytest tests/test_specific.py::test_function -s  # Show print statements
```

### 2. Run Related Tests

```bash
# Test the module/feature
pytest tests/test_module.py -v
npm test tests/module.test.js

# Check for side effects
pytest tests/ -k "related_functionality"
```

### 3. Full Test Suite

```bash
# Ensure no regressions
pytest
npm test

# Check coverage if relevant
pytest --cov=src tests/
npm run test:coverage
```

## Common Fix Patterns

### Pattern 1: Floating Point Precision

```python
# Before (fails due to precision)
assert result == 0.1 + 0.2

# After (proper comparison)
import math
assert math.isclose(result, 0.3, rel_tol=1e-9)
```

### Pattern 2: Test Isolation

```python
# Before (tests affect each other)
class TestCounter:
    counter = 0  # Shared state!

    def test_increment(self):
        self.counter += 1
        assert self.counter == 1

# After (proper isolation)
class TestCounter:
    def setup_method(self):
        self.counter = 0  # Fresh state

    def test_increment(self):
        self.counter += 1
        assert self.counter == 1
```

### Pattern 3: External Dependencies

```python
# Before (relies on external service)
def test_api_call():
    response = requests.get("https://api.example.com")
    assert response.status_code == 200

# After (mocked external dependency)
@patch('requests.get')
def test_api_call(mock_get):
    mock_get.return_value.status_code = 200
    response = requests.get("https://api.example.com")
    assert response.status_code == 200
```

### Pattern 4: Async/Await Issues

```javascript
// Before (incorrect async test)
test("async function", () => {
  const result = asyncFunction();
  expect(result).toBe(expected);
});

// After (proper async test)
test("async function", async () => {
  const result = await asyncFunction();
  expect(result).toBe(expected);
});
```

## Integration Points

### With Test Agent

- Use for complex test design issues
- Escalate when new test patterns needed
- Hand off test architecture problems

### With Fix Agent

- Apply QUICK mode for obvious assertion fixes
- Use DIAGNOSTIC mode for complex test failures
- Escalate to COMPREHENSIVE for test infrastructure

### With Main Workflow

- Use during Step 7 (Run Tests)
- Apply in Step 11 (Review Feedback)
- Integrate with Step 4 (TDD approach)

## Tool-Specific Guidance

### Python Testing (pytest)

```bash
# Debugging commands
pytest --pdb  # Drop into debugger on failure
pytest --lf  # Run last failed tests only
pytest -x  # Stop on first failure
pytest --tb=long  # Detailed traceback

# Test discovery
pytest --collect-only  # See what tests would run
```

### JavaScript Testing (Jest)

```bash
# Debugging commands
npm test -- --no-coverage  # Faster runs
npm test -- --watch  # Watch mode
npm test -- --updateSnapshot  # Update snapshots

# Specific test running
npm test -- --testPathPattern=specific
```

### Common Test Utilities

```python
# Python test helpers
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# JavaScript test helpers
const { jest } = require('@jest/globals');
const { mock, restore } = jest;
```

## Quick Reference

### 5-Minute Fix Checklist

- [ ] Identify failing test(s)
- [ ] Read error message carefully
- [ ] Check if test or code is wrong
- [ ] Apply appropriate fix pattern
- [ ] Run test to verify fix
- [ ] Check for side effects

### When to Escalate

- **Multiple test files affected**: Use test agent
- **Test architecture issues**: Use architect agent
- **Performance test failures**: Use optimizer agent
- **New testing patterns needed**: Use builder agent

## Success Patterns

### High-Success Scenarios

- Simple assertion errors (95% success)
- Mock setup issues (85% success)
- Test data problems (90% success)
- Environment variable issues (88% success)

### Challenging Scenarios

- Race condition tests (60% success)
- Complex async patterns (55% success)
- Integration test failures (45% success)
- Performance test issues (40% success)

## Test Quality Principles

### Good Test Characteristics

- **Independent**: Tests don't depend on each other
- **Repeatable**: Same result every time
- **Fast**: Quick execution
- **Self-validating**: Clear pass/fail
- **Timely**: Written close to production code

### Bad Test Smells

- **Flaky tests**: Inconsistent results
- **Slow tests**: Taking too long
- **Brittle tests**: Break with minor changes
- **Obscure tests**: Unclear purpose
- **Duplicate tests**: Testing same thing multiple ways

## Continuous Improvement

### Metrics to Track

- Test fix success rate by error type
- Time to fix test failures
- Test flakiness reduction
- Coverage maintenance

### Learning Points

- Common test failure patterns
- Effective debugging techniques
- Test isolation strategies
- Mock/stub best practices

Remember: Fix the root cause, not just the symptom. A good test fix improves both the test and understanding of the code being tested.
