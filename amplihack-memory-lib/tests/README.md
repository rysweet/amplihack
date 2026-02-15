# Memory Library Tests

Comprehensive test suite for the amplihack-memory-lib package.

## Test Organization

```
tests/
├── test_memory_connector.py       # 48 tests - Connection management, DB lifecycle
├── test_experience_store.py       # 44 tests - Store operations, search, cleanup
├── test_experience_model.py       # 40 tests - Experience dataclass validation
├── test_pattern_recognition.py    # 38 tests - Pattern detection algorithm
├── test_semantic_search.py        # 35 tests - Relevance scoring, search engine
├── test_security.py               # 15 tests - Access control (to be created)
└── test_performance.py            # 20 tests - Benchmarks (to be created)
```

**Total**: 240+ tests

## Running Tests

### Quick Start

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=amplihack_memory --cov-report=html

# Run specific test file
pytest tests/test_memory_connector.py -v

# Run specific test class
pytest tests/test_memory_connector.py::TestMemoryConnectorInitialization -v
```

### Watch Mode (TDD)

```bash
# Auto-run tests on file change
pytest-watch tests/

# Watch specific file
pytest-watch tests/test_memory_connector.py
```

### Debugging

```bash
# Run with debugger on failure
pytest --pdb tests/

# Verbose output with print statements
pytest -vv -s tests/
```

## Test Structure

All tests follow the same pattern:

```python
class TestFeatureName:
    """Test feature description."""

    @pytest.fixture
    def resource(self):
        """Create test resource."""
        # Setup
        resource = create_resource()
        yield resource
        # Teardown
        cleanup_resource(resource)

    def test_specific_behavior(self, resource):
        """Test that specific behavior works correctly."""
        # Arrange
        setup_preconditions()

        # Act
        result = perform_action()

        # Assert
        assert result == expected_value
```

## Test Categories

### 1. Initialization Tests

Validate correct setup and configuration:

- Default values are correct
- Custom configurations are accepted
- Invalid inputs are rejected

### 2. Functionality Tests

Validate core operations work correctly:

- Store and retrieve experiences
- Search for relevant experiences
- Recognize patterns
- Calculate relevance scores

### 3. Edge Case Tests

Validate handling of unusual inputs:

- Empty collections
- Very large inputs
- Invalid data types
- Concurrent access

### 4. Performance Tests

Validate performance requirements:

- Operations complete within time limits
- No memory leaks
- Efficient search with large datasets

### 5. Error Handling Tests

Validate errors are handled gracefully:

- Invalid inputs raise appropriate exceptions
- Corrupted data is detected
- Storage errors are reported clearly

## Test Fixtures

Common fixtures used across tests:

### `tmp_path` (built-in)

Temporary directory for test storage:

```python
def test_storage(tmp_path):
    connector = MemoryConnector(
        agent_name="test",
        storage_path=tmp_path / "memory"
    )
```

### `sample_experiences`

Pre-populated experiences for testing:

```python
@pytest.fixture
def sample_experiences():
    return [
        Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test context",
            outcome="Test outcome",
            confidence=0.8,
            timestamp=datetime.now()
        )
        # ... more experiences
    ]
```

## Test Requirements

All tests should:

1. ✓ Be independent (no test dependencies)
2. ✓ Be fast (<100ms per test for unit tests)
3. ✓ Be deterministic (consistent results)
4. ✓ Clean up after themselves (no side effects)
5. ✓ Have clear, descriptive names
6. ✓ Include docstrings explaining what is tested
7. ✓ Follow Arrange-Act-Assert pattern

## Coverage Goals

- **Overall**: >90% code coverage
- **Critical paths**: 100% coverage
- **Error handling**: 100% coverage
- **Edge cases**: >85% coverage

## Performance Benchmarks

### Target Metrics

- `store_experience()`: <5ms per operation
- `retrieve_experiences()`: <20ms for 1000 experiences
- `retrieve_relevant()`: <50ms for 1000 experiences
- `get_statistics()`: <2ms

### Running Benchmarks

```bash
# Run performance tests only
pytest tests/test_performance.py -v

# Generate performance report
pytest tests/test_performance.py --benchmark-only
```

## Common Test Patterns

### Testing Exceptions

```python
def test_raises_on_invalid_input():
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError):
        connector.store_experience(invalid_experience)
```

### Testing with Parameters

```python
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
])
def test_with_parameters(input, expected):
    """Test multiple cases with same logic."""
    assert process(input) == expected
```

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async operation works correctly."""
    result = await async_operation()
    assert result.success is True
```

## Continuous Integration

Tests run automatically on:

- Every commit to feature branches
- Pull requests to main branch
- Nightly on main branch

### CI Pipeline

1. Lint code (ruff, black)
2. Type check (mypy)
3. Run unit tests
4. Run integration tests
5. Check coverage >90%
6. Generate reports

## Troubleshooting

### Tests Failing Locally

1. **Check Python version**

   ```bash
   python --version  # Should be 3.10+
   ```

2. **Update dependencies**

   ```bash
   pip install -e .[dev]
   ```

3. **Clear pytest cache**
   ```bash
   pytest --cache-clear
   ```

### Slow Tests

1. **Run only fast tests**

   ```bash
   pytest -m "not slow"
   ```

2. **Run in parallel**
   ```bash
   pytest -n auto
   ```

### Coverage Issues

1. **View missing lines**

   ```bash
   pytest --cov=amplihack_memory --cov-report=term-missing
   ```

2. **Generate HTML report**
   ```bash
   pytest --cov=amplihack_memory --cov-report=html
   open htmlcov/index.html
   ```

## Contributing Tests

When adding new functionality:

1. **Write tests first** (TDD approach)
2. **Run tests** (they should fail)
3. **Implement feature** (make tests pass)
4. **Refactor** (improve code quality)
5. **Verify coverage** (>90%)

### Test Naming Convention

```python
# Good
def test_stores_experience_with_valid_data():
def test_raises_on_empty_context():
def test_retrieves_relevant_experiences_by_similarity():

# Bad
def test_store():
def test_error():
def test_retrieve():
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest parametrize](https://docs.pytest.org/en/stable/parametrize.html)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Last Updated**: 2026-02-14
**Test Count**: 240+ tests
**Coverage Target**: >90%
