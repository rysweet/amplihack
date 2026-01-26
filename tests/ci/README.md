# CI Validators Test Suite

Comprehensive test coverage for the three CI validation scripts in `~/.amplihack/.claude/ci/`.

## Test Files

- **test_check_root_files.py** (328 lines, 20 tests) - Tests for root directory file validation
- **test_check_unrelated_changes.py** (420 lines, 27 tests) - Tests for unrelated changes detection
- **test_check_point_in_time_docs.py** (507 lines, 27 tests) - Tests for temporal documentation detection

## Running Tests

```bash
# Run all CI validator tests
pytest tests/ci/ -v

# Run specific test file
pytest tests/ci/test_check_root_files.py -v

# Run with coverage
pytest tests/ci/ --cov=.claude.ci --cov-report=html
```

## Test Coverage

Total: **74 tests**, all passing

### Coverage by Validator

| Validator                   | Tests | Focus Areas                                              |
| --------------------------- | ----- | -------------------------------------------------------- |
| check_root_files.py         | 20    | Pattern matching, allowlist/blocklist, report generation |
| check_unrelated_changes.py  | 27    | Scope classification, git integration, warning logic     |
| check_point_in_time_docs.py | 27    | Temporal detection, file scanning, report formatting     |

## Test Distribution

Following the testing pyramid principle:

- **Unit Tests**: ~60% (48 tests)
- **Integration Tests**: ~33% (22 tests)
- **E2E Tests**: ~7% (4 tests)

## Key Testing Patterns

1. **Fixtures**: Consistent test setup with `temp_repo` and `mock_config`
2. **Mocking**: Git operations mocked via `subprocess.run`
3. **Temporary Files**: Using pytest's `tmp_path` for file system isolation
4. **Edge Cases**: Empty configs, missing files, encoding errors, git failures

## Test Insights

Tests revealed implementation details:

- Pattern matching in `check_unrelated_changes.py` uses literal string matching (not glob)
- All validators implement proper git branch fallback (main → master)
- Error handling is comprehensive across all validators
