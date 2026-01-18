# Test Suite for check-broken-links

Comprehensive TDD test suite following amplihack testing philosophy.

## Overview

- **33 tests total** (4 more than target - extra error handling coverage)
- **60% unit tests** - Fast, heavily mocked
- **30% integration tests** - Multiple components
- **10% E2E tests** - Complete workflows (skipped for MVP)

## Files

- `test_link_checker.py` - Main test suite (33 tests)
- `TEST_COVERAGE_SUMMARY.md` - Detailed test breakdown
- `BUILDER_GUIDE.md` - Implementation guide for builder
- `__init__.py` - Package marker

## Quick Start

```bash
# Install pytest (if needed)
uv add --dev pytest

# Run all tests
pytest .claude/scenarios/check-broken-links/tests/ -v

# Run fast tests only (skip E2E)
pytest .claude/scenarios/check-broken-links/tests/ -v -k "not e2e"

# Run with coverage
pytest .claude/scenarios/check-broken-links/tests/ --cov
```

## Test Structure

```
tests/
├── __init__.py                      # Package marker
├── test_link_checker.py            # Main test suite (33 tests)
├── TEST_COVERAGE_SUMMARY.md        # Detailed breakdown
├── BUILDER_GUIDE.md                # Implementation guide
└── README.md                       # This file
```

## Test Categories

### Unit Tests (18 tests - 60%)

- Prerequisite checking (3 tests)
- Subprocess wrapper (4 tests)
- Report parsing (4 tests)
- Report formatting (3 tests)
- Data structures (2 tests)
- Exit codes (3 tests)

### Integration Tests (8 tests - 30%)

- check_site() integration (4 tests)
- check_local() integration (3 tests)
- End-to-end report flow (1 test)

### E2E Tests (3 tests - 10%)

- Real linkinator tests (all skipped for MVP)

### Error Handling (4 tests)

- Error boundaries and edge cases

## Expected Behavior (TDD)

### Before Implementation

```bash
$ pytest .claude/scenarios/check-broken-links/tests/ -v
======================== 30 failed, 3 skipped ========================
```

All tests fail because functions not implemented (TDD approach).

### After Implementation

```bash
$ pytest .claude/scenarios/check-broken-links/tests/ -v
======================== 30 passed, 3 skipped ========================
```

All unit/integration tests pass. E2E tests remain skipped until real linkinator integration.

## Key Patterns

Following amplihack PATTERNS.md:

1. **Safe Subprocess Wrapper** (PATTERNS.md lines 206-245)
   - Comprehensive error handling
   - User-friendly error messages
   - Standard exit codes

2. **Fail-Fast Prerequisites** (PATTERNS.md lines 254-300)
   - Check dependencies at startup
   - Clear installation instructions
   - Platform-specific guidance

3. **TDD Testing Pyramid** (PATTERNS.md lines 337-382)
   - 60/30/10 distribution
   - Strategic mocking
   - Fast execution

## Running Tests

### Development Workflow

```bash
# Run tests frequently during implementation
pytest .claude/scenarios/check-broken-links/tests/ -v

# Stop on first failure (useful during TDD)
pytest .claude/scenarios/check-broken-links/tests/ -v -x

# Run specific test class
pytest .claude/scenarios/check-broken-links/tests/test_link_checker.py::TestDataStructures -v

# Watch mode (re-run on file changes - requires pytest-watch)
ptw .claude/scenarios/check-broken-links/tests/
```

### CI/CD Integration

```bash
# Run with coverage for CI
pytest .claude/scenarios/check-broken-links/tests/ --cov --cov-report=html

# Generate JUnit XML for CI systems
pytest .claude/scenarios/check-broken-links/tests/ --junitxml=test-results.xml
```

## Test Documentation

For detailed information, see:

- **TEST_COVERAGE_SUMMARY.md** - Complete test breakdown with implementation notes
- **BUILDER_GUIDE.md** - Step-by-step implementation guide
- **test_link_checker.py** - Inline docstrings explain each test

## Philosophy Compliance

- ✓ **Zero-BS Implementation** - No stubs, all tests fail initially
- ✓ **Ruthless Simplicity** - Clear, focused tests
- ✓ **Testing Pyramid** - 60/30/10 distribution maintained
- ✓ **Strategic Mocking** - External dependencies mocked
- ✓ **Fast Execution** - All tests run in < 5 seconds

## Success Criteria

- [x] 30+ tests written
- [x] Tests fail initially (TDD)
- [x] 60/30/10 pyramid maintained
- [x] Comprehensive error handling
- [x] Strategic mocking
- [x] Clear documentation
- [ ] Tests pass after implementation
- [ ] E2E tests work with real linkinator

## Next Steps

1. Builder reads BUILDER_GUIDE.md
2. Implements functions to make tests pass
3. Runs tests frequently to track progress
4. All tests should pass after implementation

---

**Questions?** Check BUILDER_GUIDE.md or TEST_COVERAGE_SUMMARY.md for detailed guidance.
