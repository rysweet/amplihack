# Module: Syntax Validation Performance Tests

## Purpose

Ensure syntax validation meets performance SLAs (< 500ms for 50 files, < 2s full codebase). Prevents performance regression.

## Contract

### Inputs
- **Test fixtures**: Generated Python files (valid syntax)
- **Sizes**: 1, 10, 50, 100 files
- **Environment**: CI and local dev machines

### Outputs
- **pytest pass/fail**: Based on timing assertions
- **Performance metrics**: Logged for monitoring

### Side Effects
- Creates temporary test files in pytest tmpdir
- Cleans up after test completion

## Dependencies

- `pytest` - Test framework
- `time` or `pytest-benchmark` - Timing measurements
- `tempfile` - Temporary file creation
- Built-in `check_syntax` module being tested

## Implementation Notes

### Test Structure

```python
import pytest
import time
from pathlib import Path

@pytest.mark.order(2)  # Run after basic syntax tests
@pytest.mark.performance
class TestSyntaxValidationPerformance:
    """Performance tests for syntax validation."""

    def test_single_file_performance(self, tmp_path):
        """Single file validation < 50ms."""
        # Create valid Python file
        # Validate and assert time < 50ms

    def test_50_files_performance(self, tmp_path):
        """50 files validation < 500ms (pre-commit SLA)."""
        # Create 50 valid Python files
        # Validate all and assert time < 500ms

    def test_full_codebase_performance(self):
        """Full codebase validation < 2s."""
        # Get all Python files in project
        # Validate all and assert time < 2s

    def test_performance_regression(self, benchmark):
        """Benchmark to detect performance regression."""
        # Optional: use pytest-benchmark for detailed metrics
```

### Performance Measurement Strategy

1. **Direct Timing** (Simple, no dependencies):
```python
start = time.perf_counter()
result = validate_files(files)
duration = time.perf_counter() - start
assert duration < threshold
```

2. **pytest-benchmark** (Advanced, optional):
```python
result = benchmark(validate_files, files)
assert benchmark.stats.mean < threshold
```

**Recommendation**: Start with direct timing (option 1). Add pytest-benchmark later if needed for regression tracking.

### Test File Generation

```python
def create_test_files(tmp_path: Path, count: int) -> list[Path]:
    """Create valid Python test files.

    Args:
        tmp_path: pytest temporary directory
        count: Number of files to create

    Returns:
        List of created file paths
    """
    files = []
    for i in range(count):
        file = tmp_path / f"test_file_{i}.py"
        file.write_text(f"""
def function_{i}():
    '''Valid function {i}.'''
    return {i}

class Class_{i}:
    '''Valid class {i}.'''
    pass
""")
        files.append(file)
    return files
```

### Performance Thresholds

| Test Scenario | Threshold | Rationale |
|--------------|-----------|-----------|
| Single file | 50ms | Imperceptible to user |
| 50 files | 500ms | Pre-commit tolerance limit |
| Full codebase | 2s | CI acceptable, user tolerable |

These thresholds are:
- Conservative (allow headroom for slower CI machines)
- User-focused (based on human perception)
- Measurable (clear pass/fail)

## Test Requirements

### Functional Tests
1. **Timing accuracy**: Verify timer measures correctly
2. **File generation**: Ensure test files are valid Python
3. **Cleanup**: Verify tmp files are cleaned up

### Edge Cases
1. **Large files**: Test with 1000+ line file
2. **Many small files**: Test with 200+ tiny files
3. **Mixed sizes**: Test realistic mix of file sizes
4. **Cold start**: First run (imports not cached)

### CI Integration
1. **Mark as slow**: `@pytest.mark.slow` for optional skipping
2. **Mark as performance**: `@pytest.mark.performance` for grouping
3. **Fail fast**: If basic syntax tests fail, skip performance tests

## Test Ordering Strategy

```python
# Order: 1 - Basic syntax validation tests
# Order: 2 - Performance tests (this suite)
# Order: 3 - Edge case tests
# Order: 4 - Integration tests

@pytest.mark.order(2)
class TestSyntaxValidationPerformance:
    pass
```

**Rationale**: Run basic functionality first. Only run performance tests if basic tests pass (no point timing broken code).

## Performance Monitoring

### Logging Performance Data

```python
import logging

logger = logging.getLogger(__name__)

def log_performance(test_name: str, duration: float, file_count: int):
    """Log performance metrics for monitoring."""
    logger.info(
        f"Performance: {test_name} | "
        f"Files: {file_count} | "
        f"Duration: {duration:.3f}s | "
        f"Per-file: {duration/file_count*1000:.1f}ms"
    )
```

Store in `.claude/runtime/logs/performance/` for trend analysis.

## Success Metrics

1. **All tests pass**: Performance meets SLAs
2. **No flakiness**: Tests pass consistently (99%+ pass rate)
3. **Fast execution**: Performance tests themselves run quickly (< 5s total)
4. **Clear failures**: When threshold exceeded, clear message about how much over
