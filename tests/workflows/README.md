# Workflow Tests for Issue #2353

Comprehensive test suite for mandatory workflow classification at session start with Recipe Runner.

## Test Structure

Following the **Testing Pyramid** principle (60% unit, 30% integration, 10% E2E):

```
tests/workflows/
├── __init__.py                          # Package marker
├── conftest.py                          # Shared fixtures
├── test_classifier.py                   # Unit tests (60%)
├── test_execution_tier_cascade.py       # Unit tests (60%)
├── test_session_start_integration.py    # Integration tests (30%)
├── test_e2e_acceptance_criteria.py      # E2E tests (10%)
├── test_performance.py                  # Performance tests
├── test_regression.py                   # Regression tests
└── README.md                            # This file
```

## Test Categories

### Unit Tests (60% of coverage)

**test_classifier.py** - 40 tests

- Classification logic for 4 workflows (Q&A, OPS, INVESTIGATION, DEFAULT)
- Keyword extraction and matching
- Confidence scoring
- Edge cases and error handling
- Performance (NFR2: <5 seconds)
- Configuration and customization

**test_execution_tier_cascade.py** - 35 tests

- Tier detection (Recipe Runner, Workflow Skills, Markdown)
- Execution via each tier
- Fallback chain logic
- Workflow-to-recipe mapping
- Error handling and recovery
- Metrics and logging

### Integration Tests (30% of coverage)

**test_session_start_integration.py** - 30 tests

- Session start detection
- Complete classification flow
- Recipe Runner integration
- Workflow Skills fallback
- Context passing through chain
- Announcements and user experience

### End-to-End Tests (10% of coverage)

**test_e2e_acceptance_criteria.py** - 18 tests

- All 6 acceptance criteria scenarios
- Full user experience flows
- Complete session-to-execution paths
- User experience quality validation

### Supporting Tests

**test_performance.py** - 20 tests

- NFR2: Classification <5 seconds
- Execution tier cascade performance
- Memory and resource usage
- Concurrent performance
- Performance regression detection

**test_regression.py** - 25 tests

- NFR1: Backward compatibility
- Existing workflows unaffected
- Existing commands unaffected
- API compatibility
- Data structure compatibility

## Total Test Count

**168 tests** covering:

- 75 unit tests (45%)
- 30 integration tests (18%)
- 18 E2E tests (11%)
- 45 support tests (27% - performance + regression)

**Test Ratio: 5:1** (Complex task - appropriate for COMPLEX classification)

## Running Tests

### Run All Tests

```bash
pytest tests/workflows/ -v
```

### Run by Category

```bash
# Unit tests only
pytest tests/workflows/ -m unit -v

# Integration tests only
pytest tests/workflows/ -m integration -v

# E2E tests only
pytest tests/workflows/ -m e2e -v

# Performance tests
pytest tests/workflows/ -m performance -v
```

### Run Specific Test Files

```bash
# Classification unit tests
pytest tests/workflows/test_classifier.py -v

# Execution cascade tests
pytest tests/workflows/test_execution_tier_cascade.py -v

# Session start integration
pytest tests/workflows/test_session_start_integration.py -v

# Acceptance criteria (E2E)
pytest tests/workflows/test_e2e_acceptance_criteria.py -v

# Performance tests
pytest tests/workflows/test_performance.py -v

# Regression tests
pytest tests/workflows/test_regression.py -v
```

### Run Acceptance Criteria Scenarios

```bash
# Scenario 1: Recipe Runner available
pytest tests/workflows/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario1 -v

# Scenario 2: Recipe Runner unavailable
pytest tests/workflows/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario2 -v

# Scenario 3: Q&A workflow
pytest tests/workflows/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario3 -v

# Scenario 4: Explicit command
pytest tests/workflows/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario4 -v

# Scenario 5: Recipe Runner disabled
pytest tests/workflows/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario5 -v

# Scenario 6: Recipe Runner failure
pytest tests/workflows/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario6 -v
```

## Test Coverage Goals

- **Line Coverage**: 90%+
- **Branch Coverage**: 85%+
- **Function Coverage**: 95%+

### Generate Coverage Report

```bash
pytest tests/workflows/ --cov=amplihack.workflows --cov-report=html --cov-report=term
```

## TDD Approach

These tests are written following **Test-Driven Development**:

1. **RED**: All tests should FAIL initially (no implementation exists)
2. **GREEN**: Implement minimal code to make tests pass
3. **REFACTOR**: Improve code while keeping tests green

### Current Status: RED Phase

All tests will fail with `ImportError` until implementation begins.

## Expected Test Behavior

### Before Implementation

```
FAILED tests/workflows/test_classifier.py::test_classifier_imports - ImportError: No module named 'amplihack.workflows.classifier'
FAILED tests/workflows/test_execution_tier_cascade.py::test_cascade_imports - ImportError: No module named 'amplihack.workflows.execution_tier_cascade'
FAILED tests/workflows/test_session_start_integration.py::test_detect_session_start_first_message - ImportError: No module named 'amplihack.workflows.session_start'
```

### After Implementation

```
PASSED tests/workflows/test_classifier.py::test_classify_default_add
PASSED tests/workflows/test_execution_tier_cascade.py::test_execute_tier1_recipe_runner
PASSED tests/workflows/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario1::test_scenario1_recipe_runner_available
```

## Test Fixtures

Shared fixtures in `conftest.py`:

- `mock_recipe_runner` - Mock Recipe Runner for testing
- `mock_workflow_skill` - Mock Workflow Skill for testing
- `sample_user_request` - Sample user requests for each workflow type
- `session_context` - Sample session context with metadata
- `mock_environment_vars` - Environment variable mocking
- `temp_recipe_dir` - Temporary directory for recipe files
- `mock_cli_subprocess_adapter` - Mock CLI subprocess adapter

## Non-Functional Requirements Testing

### NFR1: Backward Compatibility

- **File**: `test_regression.py`
- **Tests**: 25 tests ensuring no breaking changes
- **Coverage**: Existing workflows, commands, APIs, data structures

### NFR2: Performance (<5s classification)

- **File**: `test_performance.py`
- **Tests**: 20 tests measuring classification speed
- **Criteria**: Classification must complete in <5 seconds

### NFR3: User Experience

- **File**: `test_e2e_acceptance_criteria.py`
- **Tests**: Clear announcements, helpful messages, smooth flow

## Module Dependencies

Tests assume the following modules will be implemented:

```
src/amplihack/workflows/
├── __init__.py
├── classifier.py                    # 4-way workflow classification
├── execution_tier_cascade.py        # 3-tier execution fallback
├── session_start.py                 # Session start detection
└── session_start_skill.py           # Session start skill integration
```

## Edge Cases Covered

1. Empty/None inputs
2. Invalid workflow names
3. Ambiguous requests
4. Multiple keyword matches
5. Long/complex requests
6. Concurrent requests
7. Environment variable overrides
8. Recipe Runner failures
9. Workflow Skills failures
10. Markdown fallback scenarios

## Known Limitations

1. Recipe Runner must be separately tested (not mocked completely)
2. CLISubprocessAdapter requires real subprocess testing
3. Performance tests depend on system load
4. Memory tests may vary by Python version

## Future Test Additions

When implementation is complete, consider adding:

1. **Fuzz testing** for classification input validation
2. **Property-based testing** with hypothesis
3. **Load testing** for high-volume scenarios
4. **Chaos testing** for fallback chain resilience
5. **Integration with real Claude Code sessions**

## Test Maintenance

- Update tests when adding new workflow types
- Add new scenarios when user feedback identifies gaps
- Keep performance baselines current
- Review regression tests quarterly

## CI/CD Integration

These tests should run in CI:

- **PR checks**: Unit + Integration tests
- **Nightly**: All tests including E2E and performance
- **Release**: Full suite including regression

## References

- Issue #2353: Mandatory Workflow Classification at Session Start
- Architecture Design: `docs/architecture/*2353*.md`
- Requirements: `docs/requirements/*2353*.md`
- CLAUDE.md: Session Start Protocol section
