# Tests for amplihack Hooks

This directory contains comprehensive test suites for amplihack hook modules.

## Test Files

### test_settings_migrator.py

Comprehensive test suite for `settings_migrator.py` following TDD testing pyramid (60% unit, 30% integration, 10% E2E).

**Stats:**

- 44 tests (100% passing)
- 84% code coverage
- <0.2 second execution time

**Test Categories:**

- Unit Tests (27): Fast, isolated, heavily mocked
- Integration Tests (13): Real filesystem, multiple components
- E2E Tests (4): Complete user scenarios

See [TEST_SUMMARY.md](./TEST_SUMMARY.md) for detailed analysis.

## Running Tests

### Run All Tests

```bash
# From project root
python -m pytest .claude/tools/amplihack/hooks/tests/

# Verbose output
python -m pytest .claude/tools/amplihack/hooks/tests/ -v
```

### Run Specific Test File

```bash
python -m pytest .claude/tools/amplihack/hooks/tests/test_settings_migrator.py -v
```

### Run Specific Test Class

```bash
python -m pytest .claude/tools/amplihack/hooks/tests/test_settings_migrator.py::TestMigrationWorkflow -v
```

### Run Specific Test

```bash
python -m pytest .claude/tools/amplihack/hooks/tests/test_settings_migrator.py::TestMigrationWorkflow::test_migration_idempotency -v
```

### Coverage Report

```bash
# From hooks directory
cd .claude/tools/amplihack/hooks
pytest tests/test_settings_migrator.py --cov=. --cov-report=term-missing --cov-report=html

# View HTML report
# Opens htmlcov/index.html in browser
```

## Test Philosophy

All tests follow these principles:

1. **Zero-BS Implementation**: Every test works, no stubs or placeholders
2. **Fast Execution**: Unit tests complete in milliseconds
3. **Clear Assertions**: Single responsibility per test
4. **Realistic Fixtures**: Real-world scenarios
5. **TDD Pyramid**: 60% unit, 30% integration, 10% E2E

## Test Structure

```
tests/
├── README.md                    # This file
├── TEST_SUMMARY.md              # Detailed test analysis
├── test_settings_migrator.py    # Settings migration tests
└── (future test files...)
```

## Adding New Tests

When adding tests for new modules:

1. Follow the TDD pyramid (60/30/10)
2. Use descriptive test names
3. Create appropriate fixtures
4. Keep tests fast (<0.5s per file)
5. Document in TEST_SUMMARY.md

## Test Fixtures

Common fixtures used across tests:

- **tmp_project_root**: Temporary project with .claude marker
- **tmp_home**: Temporary home directory
- **global*settings_with*\***: Various global settings scenarios
- **project_settings_exists**: Project-local settings

See individual test files for fixture definitions.

## CI Integration

Tests run automatically in CI:

- All tests must pass before merge
- Coverage must remain >80%
- Execution time must be <1 second per file

## Troubleshooting

### Tests Fail Locally

```bash
# Ensure you're in the correct directory
cd /path/to/amplihack4

# Clear pytest cache
python -m pytest --cache-clear

# Re-run tests
python -m pytest .claude/tools/amplihack/hooks/tests/ -v
```

### Coverage Not Working

```bash
# Ensure pytest-cov is installed
pip install pytest-cov

# Run from hooks directory
cd .claude/tools/amplihack/hooks
pytest tests/ --cov=.
```

## Future Test Modules

Planned test files:

- `test_precommit_installer.py` - Pre-commit hook installer tests
- `test_hook_processor.py` - Hook processor tests
- `test_session_start.py` - Session start hook tests
- `test_session_stop.py` - Session stop hook tests

---

**Philosophy**: Every module should have comprehensive tests. No module ships without >80% coverage and full TDD pyramid implementation.
