# Test Fix Template

> **Coverage**: ~18% of all fixes
> **Target Time**: 30-60 seconds assessment, 2-10 minutes resolution

## Problem Pattern Recognition

### Trigger Indicators

```
Error patterns:
- "FAILED", "AssertionError"
- "fixture", "setup", "teardown"
- "mock", "patch", "MagicMock"
- "flaky", "intermittent", "sometimes passes"
- "pytest", "unittest", "test_"
```

### Error Categories

| Category | Frequency | Indicators |
|----------|-----------|------------|
| Assertion Failures | 35% | AssertionError, expected vs actual |
| Fixture Issues | 25% | fixture not found, scope error |
| Mock Problems | 25% | wrong return, not called, spec mismatch |
| Flaky Tests | 15% | passes sometimes, timing, order-dependent |

## Quick Assessment (30-60 sec)

### Step 1: Identify Test Type

```bash
# What kind of test is failing?
# - Unit test: Tests single function in isolation
# - Integration test: Tests multiple components together
# - End-to-end test: Tests full flow

# Look at the test name and file location
# tests/unit/test_utils.py → unit test
# tests/integration/test_api.py → integration test
```

### Step 2: Run in Isolation

```bash
# Run just the failing test
pytest tests/test_file.py::test_specific_function -v

# With more output
pytest tests/test_file.py::test_specific_function -v --tb=long

# With print statements shown
pytest tests/test_file.py::test_specific_function -v -s
```

## Solution Steps by Category

### Assertion Failures

**Diagnose the Mismatch**
```python
# Get detailed assertion info
pytest --tb=long -v

# The output shows:
# - Expected value
# - Actual value
# - Where they differ
```

**Common Assertion Fixes**

```python
# WRONG: Exact match when approximate needed
assert result == 0.3  # Float comparison fails
assert calculated == expected_complex_dict  # Dict order

# RIGHT: Use appropriate comparisons
import pytest
assert result == pytest.approx(0.3, rel=1e-9)
assert calculated == expected_complex_dict  # dicts compare fine
# For unordered: 
assert set(result) == set(expected)
```

**Type Mismatches**
```python
# WRONG: Comparing different types
assert get_id() == "123"  # Returns int, comparing str

# Check types first
result = get_id()
print(f"Result: {result!r}, Type: {type(result)}")

# RIGHT: Convert or fix source
assert str(get_id()) == "123"
# Or fix the function to return correct type
```

**Order Issues**
```python
# WRONG: List order matters but shouldn't
assert get_items() == ["b", "a", "c"]  # Order varies

# RIGHT: Compare as sets or sort
assert set(get_items()) == {"a", "b", "c"}
assert sorted(get_items()) == ["a", "b", "c"]
```

### Fixture Issues

**Fixture Not Found**
```python
# Error: fixture 'my_fixture' not found

# Check 1: Is fixture defined?
@pytest.fixture
def my_fixture():
    return "data"

# Check 2: Is it in conftest.py? (for sharing)
# conftest.py in tests/ directory

# Check 3: Scope correct?
@pytest.fixture(scope="module")  # session, module, function
def db_connection():
    ...
```

**Fixture Scope Errors**
```python
# Error: ScopeMismatch - using function-scoped fixture in module scope

# WRONG: Mismatched scopes
@pytest.fixture(scope="module")
def module_fixture(function_scoped_fixture):  # Error!
    ...

# RIGHT: Match or broaden scope
@pytest.fixture(scope="module")
def module_fixture(module_scoped_fixture):  # Same scope
    ...
```

**Fixture Not Cleaned Up**
```python
# WRONG: Resources leak
@pytest.fixture
def db():
    conn = create_connection()
    return conn  # Never closed!

# RIGHT: Use yield for cleanup
@pytest.fixture
def db():
    conn = create_connection()
    yield conn
    conn.close()  # Runs after test
```

**Async Fixtures**
```python
# For async tests, use pytest-asyncio
import pytest

@pytest.fixture
async def async_client():
    client = await create_client()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_something(async_client):
    result = await async_client.fetch()
    assert result
```

### Mock Problems

**Mock Not Applied**
```python
# WRONG: Patching wrong path
# File: myapp/module.py imports requests
# from requests import get  # Imports into module namespace

# This won't work:
@patch('requests.get')  # Patches wrong location

# RIGHT: Patch where it's used
@patch('myapp.module.get')  # Patch in the module's namespace
def test_something(mock_get):
    mock_get.return_value = Mock(status_code=200)
    ...
```

**Mock Return Value**
```python
# WRONG: Mock returns MagicMock, not expected value
@patch('myapp.db.fetch_user')
def test_user(mock_fetch):
    # Forgot to set return_value!
    result = get_user_name(1)
    assert result == "Alice"  # Fails: got MagicMock

# RIGHT: Set return value
@patch('myapp.db.fetch_user')
def test_user(mock_fetch):
    mock_fetch.return_value = User(name="Alice")
    result = get_user_name(1)
    assert result == "Alice"
```

**Async Mocks**
```python
# WRONG: Regular mock for async function
@patch('myapp.api.fetch_data')
async def test_async(mock_fetch):
    mock_fetch.return_value = data  # Won't work with await

# RIGHT: Use AsyncMock
from unittest.mock import AsyncMock

@patch('myapp.api.fetch_data', new_callable=AsyncMock)
async def test_async(mock_fetch):
    mock_fetch.return_value = data
    result = await function_under_test()
```

**Verify Mock Calls**
```python
# Check mock was called correctly
def test_notification(mock_send):
    process_order(order)
    
    # Verify it was called
    mock_send.assert_called_once()
    
    # Verify arguments
    mock_send.assert_called_with(
        to="user@example.com",
        subject="Order Confirmed"
    )
    
    # Check call count
    assert mock_send.call_count == 1
```

### Flaky Tests

**Diagnose Flakiness**
```bash
# Run test multiple times
pytest tests/test_flaky.py -v --count=10

# Run with different random seed
pytest tests/test_flaky.py -v -p randomly

# Run in isolation
pytest tests/test_flaky.py::test_specific -v --forked
```

**Timing Issues**
```python
# WRONG: Depends on timing
def test_cache_expires():
    cache.set("key", "value", ttl=1)
    time.sleep(1)  # Might not be enough!
    assert cache.get("key") is None

# RIGHT: Use freezegun or mock time
from freezegun import freeze_time

def test_cache_expires():
    with freeze_time() as frozen:
        cache.set("key", "value", ttl=60)
        frozen.tick(61)  # Advance time precisely
        assert cache.get("key") is None
```

**Order-Dependent Tests**
```python
# WRONG: Test depends on previous test's state
def test_create_user():
    create_user("alice")  # Creates in shared db
    
def test_get_user():
    user = get_user("alice")  # Depends on previous test!
    assert user.name == "alice"

# RIGHT: Each test sets up its own state
def test_get_user():
    create_user("alice")  # Own setup
    user = get_user("alice")
    assert user.name == "alice"
    delete_user("alice")  # Own cleanup

# BETTER: Use fixtures
@pytest.fixture
def user(db):
    user = create_user("alice")
    yield user
    delete_user(user.id)

def test_get_user(user):
    result = get_user(user.name)
    assert result == user
```

**Random Data Issues**
```python
# WRONG: Uses random data without seed
def test_process():
    data = generate_random_data()  # Different each run
    result = process(data)
    assert result.valid  # Might fail on edge cases

# RIGHT: Use seed or fixed data
def test_process():
    random.seed(42)  # Reproducible
    data = generate_random_data()
    result = process(data)
    assert result.valid
```

## Isolation Debugging

### Run Single Test

```bash
# Specific test
pytest tests/test_file.py::TestClass::test_method -v

# With maximum verbosity
pytest tests/test_file.py::test_name -vvv --tb=long

# Stop on first failure
pytest -x

# Start debugger on failure
pytest --pdb
```

### Check for Test Pollution

```bash
# Run in random order
pip install pytest-randomly
pytest --randomly-seed=12345

# Run in reverse order
pytest tests/ --reverse

# Run specific test in isolation
pytest tests/test_file.py::test_name --forked
```

## Common Pytest Issues

### Parametrized Tests

```python
# Proper parametrization
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert input.upper() == expected

# IDs for clarity
@pytest.mark.parametrize("input,expected", [
    pytest.param("hello", "HELLO", id="simple_word"),
    pytest.param("", "", id="empty_string"),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

### Skipping Tests

```python
# Skip with reason
@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature():
    ...

# Skip conditionally
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Does not work on Windows"
)
def test_unix_feature():
    ...

# Expected failure
@pytest.mark.xfail(reason="Known bug #123")
def test_known_bug():
    ...
```

### Capturing Output

```python
# Capture stdout/stderr
def test_print(capsys):
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"

# Capture logs
def test_logging(caplog):
    with caplog.at_level(logging.WARNING):
        do_something()
    assert "warning message" in caplog.text
```

## Coverage Gaps

### Check Coverage

```bash
# Run with coverage
pytest --cov=myapp --cov-report=html

# See what's missing
open htmlcov/index.html

# Specific file coverage
pytest --cov=myapp.module --cov-report=term-missing
```

### Add Missing Tests

```python
# Pattern: Test edge cases
def test_function_with_empty_input():
    assert function([]) == []

def test_function_with_none():
    with pytest.raises(ValueError):
        function(None)

def test_function_with_large_input():
    large = list(range(10000))
    assert function(large) == expected
```

## Validation Steps

### Quick Validation

```bash
# 1. Run failing test in isolation
pytest tests/test_file.py::test_name -v

# 2. See full output
pytest tests/test_file.py::test_name -v -s --tb=long
```

### Post-Fix Validation

```bash
# 1. Verify fixed test passes
pytest tests/test_file.py::test_name -v

# 2. Run related tests
pytest tests/test_file.py -v

# 3. Run full suite (check for regressions)
pytest

# 4. Run multiple times (if was flaky)
pytest tests/test_file.py::test_name --count=5
```

## Escalation Criteria

### Escalate When

- Test is testing the wrong thing (spec mismatch)
- Flakiness root cause is unclear
- Need to mock complex infrastructure
- Test architecture needs redesign
- Race conditions in test setup

### Information to Gather

```
1. Full test output with --tb=long
2. Does it pass in isolation?
3. Does it pass locally but fail in CI?
4. Is it flaky? How often does it fail?
5. What changed recently?
```

## Quick Reference

### Pytest Commands

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_file.py::test_name

# Verbose with full traceback
pytest -v --tb=long

# Stop on first failure
pytest -x

# Show print output
pytest -s

# Run failed tests from last run
pytest --lf

# Debug on failure
pytest --pdb
```

### Common Fixes

| Problem | Fix |
|---------|-----|
| Fixture not found | Check conftest.py, scope, import |
| Mock not working | Patch where imported, not where defined |
| Flaky test | Add proper waits, mock time, isolate state |
| Assertion diff unclear | Use -v --tb=long, add custom message |
| Async test fails | Add @pytest.mark.asyncio, use AsyncMock |

### Debug Template

```python
def test_debugging():
    # Add these temporarily
    import pdb; pdb.set_trace()  # Breakpoint
    
    # Or print debugging
    result = function_under_test()
    print(f"Result: {result!r}")
    print(f"Type: {type(result)}")
    print(f"Expected: {expected!r}")
    
    assert result == expected
```
