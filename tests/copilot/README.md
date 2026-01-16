Ahoy! Here be the complete Copilot CLI Integration Test Suite!

# Copilot CLI Integration Test Suite

Comprehensive test coverage fer Phases 1-9 of the Copilot CLI integration, followin' the testing pyramid philosophy.

## Test Structure

```
tests/copilot/
├── README.md (this file)
├── conftest.py                    # Shared fixtures
├── __init__.py                    # Test suite documentation
│
├── unit/                          # 60% - Fast, isolated tests
│   ├── __init__.py
│   ├── test_agent_converter.py   # 26 test cases
│   ├── test_copilot_launcher.py  # 15 test cases
│   └── test_copilot_session_hook.py # 23 test cases
│
├── integration/                   # 30% - Multi-component tests
│   ├── __init__.py
│   └── test_full_agent_sync.py   # 13 test cases
│
├── e2e/                          # 10% - Complete workflows
│   ├── __init__.py
│   └── test_copilot_scenarios.py # 10 scenarios
│
└── performance/                   # Performance validation
    ├── __init__.py
    └── test_performance.py       # 13 benchmarks
```

## Quick Start

```bash
# Install dependencies
pip install pytest pytest-cov pytest-asyncio

# Run all tests
pytest tests/copilot/ -v

# Run specific level
pytest tests/copilot/unit/ -v           # Unit tests (fast)
pytest tests/copilot/integration/ -v    # Integration tests
pytest tests/copilot/e2e/ -v            # E2E scenarios
pytest tests/copilot/performance/ -v    # Performance tests

# With coverage
pytest tests/copilot/ --cov=src/amplihack --cov-report=html
```

## Test Coverage

### Total Test Count: 90+ Tests

| Level | Tests | Execution Time | Focus |
|-------|-------|----------------|-------|
| Unit | 64 tests | < 10s | Fast, isolated, mocked |
| Integration | 13 tests | < 15s | Multi-component, real I/O |
| E2E | 10 scenarios | < 30s | Complete workflows |
| Performance | 13 benchmarks | < 20s | Performance validation |

### Coverage by Component

| Component | Unit Tests | Integration | E2E | Total |
|-----------|------------|-------------|-----|-------|
| Agent Converter | 26 | 5 | 3 | 34 |
| Launcher | 15 | - | 2 | 17 |
| Session Hook | 23 | 3 | 2 | 28 |
| Workflow Integration | - | 5 | 3 | 8 |
| Performance | - | - | - | 13 |

## Test Philosophy

Following the **Testing Pyramid**:

```
        /\
       /  \       10% E2E Tests
      /____\      Complete workflows
     /      \
    /        \    30% Integration Tests
   /__________\   Multiple components
  /            \
 /              \  60% Unit Tests
/________________\ Fast, isolated
```

### Core Principles

1. **Strategic Coverage** - Focus on critical paths and edge cases
2. **Fast Execution** - Unit tests < 100ms, total suite < 2 min
3. **Working Tests Only** - No stubs or incomplete tests
4. **Clear Purpose** - Each test has single, clear responsibility
5. **Fail-Fast** - Immediate feedback on issues

## Unit Tests (60%)

### Agent Converter Tests

File: `unit/test_agent_converter.py` (26 tests)

**Coverage:**
- Agent validation (valid, invalid, missing fields)
- Single agent conversion (success, skip, overwrite)
- Batch conversion (all agents, registry, errors)
- Sync checking (missing, stale, up-to-date)
- Edge cases (unicode, deep nesting, empty dirs)

**Run:**
```bash
pytest tests/copilot/unit/test_agent_converter.py -v
```

### Launcher Tests

File: `unit/test_copilot_launcher.py` (15 tests)

**Coverage:**
- Copilot detection (installed, missing, timeout)
- Installation (success, failure, npm missing)
- Launch execution (args, exit codes, filesystem)
- Error handling (installation fails, interrupts)

**Run:**
```bash
pytest tests/copilot/unit/test_copilot_launcher.py -v
```

### Session Hook Tests

File: `unit/test_copilot_session_hook.py` (23 tests)

**Coverage:**
- Environment detection (env vars, files)
- Staleness checking (fast < 500ms)
- Preference management (read, save, default)
- Sync triggers (when/when not to sync)
- Error handling (permissions, invalid JSON)
- Performance requirements

**Run:**
```bash
pytest tests/copilot/unit/test_copilot_session_hook.py -v
```

## Integration Tests (30%)

### Full Agent Sync Tests

File: `integration/test_full_agent_sync.py` (13 tests)

**Coverage:**
- End-to-end sync workflow
- Incremental sync (add agents)
- Directory structure preservation
- Registry integration
- Config integration
- Staleness lifecycle
- Error recovery
- Performance integration

**Run:**
```bash
pytest tests/copilot/integration/test_full_agent_sync.py -v
```

## E2E Tests (10%)

### Copilot Scenario Tests

File: `e2e/test_copilot_scenarios.py` (10 scenarios)

**Scenarios:**
1. Simple Agent Invocation
2. Multi-Step Workflow
3. Auto Mode Session
4. Hook Lifecycle
5. MCP Server Usage
6. Complete Setup Flow
7. Update and Resync
8. Error Recovery
9. Performance Validation
10. Backward Compatibility

**Run:**
```bash
pytest tests/copilot/e2e/test_copilot_scenarios.py -v
```

## Performance Tests

### Performance Test Suite

File: `performance/test_performance.py` (13 benchmarks)

**Performance Requirements:**

| Metric | Requirement | Tested |
|--------|-------------|--------|
| Staleness check | < 500ms | ✓ |
| Full sync (50 agents) | < 2s | ✓ |
| Agent conversion | < 100ms/agent | ✓ |
| Memory usage | < 10MB | ✓ |
| Scalability (100 agents) | < 5s | ✓ |

**Run:**
```bash
pytest tests/copilot/performance/test_performance.py -v
```

## Fixtures

### Shared Fixtures (`conftest.py`)

- `temp_project` - Isolated temporary project structure
- `sample_agent_markdown` - Valid agent markdown with frontmatter
- `sample_copilot_env` - Copilot environment variables
- `mock_config_file` - Mock configuration file
- `mock_agent_files` - Set of 6 mock agents
- `mock_registry_json` - Mock REGISTRY.json

## Running Tests

### All Tests

```bash
# Complete suite
pytest tests/copilot/ -v

# With coverage
pytest tests/copilot/ --cov=src/amplihack --cov-report=html

# Parallel execution (faster)
pytest tests/copilot/ -n auto
```

### By Level

```bash
# Unit tests (fastest)
pytest tests/copilot/unit/ -v

# Integration tests
pytest tests/copilot/integration/ -v

# E2E tests
pytest tests/copilot/e2e/ -v

# Performance tests
pytest tests/copilot/performance/ -v
```

### By Component

```bash
# Agent converter
pytest tests/copilot/ -k "converter" -v

# Launcher
pytest tests/copilot/ -k "launcher" -v

# Session hook
pytest tests/copilot/ -k "session" -v

# Performance
pytest tests/copilot/ -k "performance" -v
```

### Specific Test

```bash
# Single test
pytest tests/copilot/unit/test_agent_converter.py::TestAgentValidation::test_validate_valid_agent -v

# Test class
pytest tests/copilot/unit/test_agent_converter.py::TestAgentValidation -v
```

## CI Integration

### GitHub Actions

Tests run automatically on:
- Push to main/develop
- Pull requests
- Manual workflow trigger

**Configuration:** `.github/workflows/copilot-tests.yml`

### Pre-commit Hook

Unit tests run before each commit:

```bash
# Install pre-commit hook
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Coverage Reports

### Generate Reports

```bash
# HTML report
pytest tests/copilot/ --cov=src/amplihack --cov-report=html
open htmlcov/index.html

# Terminal report
pytest tests/copilot/ --cov=src/amplihack --cov-report=term-missing

# XML for CI
pytest tests/copilot/ --cov=src/amplihack --cov-report=xml
```

### Coverage Targets

| Component | Target | Notes |
|-----------|--------|-------|
| Agent Converter | 95% | Critical path |
| Launcher | 90% | High-value |
| Session Hook | 90% | High-value |
| Overall | 85% | Minimum |

## Debugging Tests

### Verbose Output

```bash
# Maximum verbosity
pytest tests/copilot/ -vv

# Show print statements
pytest tests/copilot/ -s

# Show locals on failure
pytest tests/copilot/ -l

# Combined
pytest tests/copilot/ -vvsl
```

### Debugger

```bash
# Drop into debugger on failure
pytest tests/copilot/ --pdb

# Drop into debugger on first failure
pytest tests/copilot/ -x --pdb
```

### Test Duration

```bash
# Show slowest 10 tests
pytest tests/copilot/ --durations=10

# Show all test durations
pytest tests/copilot/ --durations=0
```

## Test Maintenance

### Adding New Tests

1. Determine test level (unit, integration, E2E)
2. Create test file following naming convention
3. Write test with clear docstring
4. Add fixtures if needed
5. Run and verify
6. Update documentation

### Updating Tests

1. Read test docstring for purpose
2. Make minimal changes
3. Verify coverage maintained
4. Run full suite
5. Update documentation if needed

### Removing Tests

1. Verify test is obsolete
2. Check for dependencies
3. Remove test
4. Run full suite
5. Update documentation

## Troubleshooting

### Tests Failing

```bash
# Clear cache
pytest --cache-clear

# Clean temp directories
rm -rf /tmp/pytest-of-*

# Reinstall package
pip uninstall amplihack
pip install -e .

# Run with fresh environment
pytest tests/copilot/ --basetemp=/tmp/pytest-clean
```

### Import Errors

```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Check package installed
pip show amplihack

# Reinstall in editable mode
pip install -e .
```

### Slow Tests

```bash
# Identify slow tests
pytest tests/copilot/ --durations=10

# Run only fast tests
pytest tests/copilot/unit/ -v
```

## Documentation

### Test Documentation Files

- `tests/copilot/README.md` - This file
- `tests/copilot/__init__.py` - Test suite overview
- `docs/copilot/TESTING.md` - Detailed testing guide
- `docs/COPILOT_TESTING_GUIDE.md` - Master testing guide

### Component Documentation

Each component has documentation:
- Agent Converter: `src/amplihack/adapters/copilot_agent_converter.py`
- Launcher: `src/amplihack/launcher/copilot.py`
- Session Hook: `.claude/tools/amplihack/hooks/copilot_session_start.py`

## Success Criteria

### Automated Tests

- ✓ All tests pass consistently
- ✓ Execution time < 2 minutes
- ✓ Coverage > 85%
- ✓ Zero flaky tests
- ✓ CI pipeline green

### Quality Metrics

- ✓ Tests are fast (unit < 100ms)
- ✓ Tests are isolated (no dependencies)
- ✓ Tests are focused (single responsibility)
- ✓ Tests are clear (descriptive names)
- ✓ Tests are maintainable (good structure)

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Copilot CLI Documentation](https://github.com/github/copilot-cli)

Arrr! May yer tests always be green and yer coverage always be high!
