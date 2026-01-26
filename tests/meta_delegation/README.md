# Meta-Delegation Test Suite

Comprehensive Test-Driven Development (TDD) test suite for the meta-agentic task delegation system (Issue #2030).

## Overview

This test suite validates all 7 modules of the meta-delegation system following TDD methodology. **All tests are designed to FAIL until the implementation is complete.**

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures and configuration
├── test_platform_cli.py             # Unit: Platform CLI Abstraction
├── test_state_machine.py            # Unit: Subprocess State Machine
├── test_persona.py                  # Unit: Persona Strategy Module
├── test_scenario_generator.py       # Unit: Gadugi Scenario Generator
├── test_success_evaluator.py        # Unit: Success Criteria Evaluator
├── test_evidence_collector.py       # Unit: Evidence Collector
├── test_orchestrator.py             # Unit: Meta-Delegator Orchestrator
├── integration/
│   ├── test_persona_integration.py  # Persona + Platform + Evidence + Evaluator
│   └── test_gadugi_integration.py   # Scenario Generator + Evidence + Evaluator
└── e2e/
    ├── test_guide_teaches_beginner.py    # Complete guide persona workflow
    └── test_qa_validates_feature.py      # Complete QA engineer workflow
```

## Test Categories

### Unit Tests (7 modules)

**test_platform_cli.py** - Platform CLI Abstraction

- Tests for ClaudeCodeCLI, CopilotCLI, AmplifierCLI implementations
- Platform registration and retrieval
- Prompt formatting for different personas
- Subprocess spawning and management
- Command validation and error handling
- **Total tests**: ~40

**test_state_machine.py** - Subprocess State Machine

- State transition validation (CREATED → STARTING → RUNNING → COMPLETING → COMPLETED)
- Failure state handling from any state
- Timeout detection
- Process polling and monitoring
- State history tracking
- **Total tests**: ~35

**test_persona.py** - Persona Strategy Module

- GUIDE, QA_ENGINEER, ARCHITECT, JUNIOR_DEV persona configurations
- Communication styles and thoroughness levels
- Evidence collection priorities
- Prompt template generation
- Persona registration and retrieval
- **Total tests**: ~30

**test_scenario_generator.py** - Gadugi Scenario Generator

- Scenario generation for different goal types
- Category coverage (happy_path, error_handling, boundary, security, performance)
- Priority assignment
- Preconditions and expected outcomes
- API-specific scenarios
- **Total tests**: ~25

**test_success_evaluator.py** - Success Criteria Evaluator

- Success criteria parsing
- Evidence-based scoring (0-100)
- Bonus scoring for tests and documentation
- Gap identification
- Test pattern recognition
- **Total tests**: ~20

**test_evidence_collector.py** - Evidence Collector

- File discovery and classification
- Content extraction and excerpt generation
- Evidence type organization
- Metadata extraction
- Incremental collection
- Persona-specific priorities
- **Total tests**: ~30

**test_orchestrator.py** - Meta-Delegator Orchestrator

- Complete delegation lifecycle
- Component initialization and coordination
- Monitoring and evidence collection phases
- Success evaluation
- Error handling (timeouts, crashes)
- Result serialization
- **Total tests**: ~25

### Integration Tests (2 suites)

**test_persona_integration.py** - Persona System Integration

- Persona strategies with platform CLI prompt generation
- Persona priorities with evidence collector
- Persona criteria with success evaluator
- Complete persona-driven workflows
- **Total tests**: ~15

**test_gadugi_integration.py** - Gadugi System Integration

- Scenario generation aligned with success criteria
- Scenarios validated against collected evidence
- Coverage measurement from evidence
- End-to-end scenario validation
- **Total tests**: ~12

### End-to-End Tests (2 scenarios)

**test_guide_teaches_beginner.py** - Guide Persona Complete Workflow

- Guide teaches REST API concepts to beginner
- Educational content generation (tutorial, examples, documentation)
- Beginner-friendly characteristics validation
- Complete evidence collection and evaluation
- **Total tests**: ~4

**test_qa_validates_feature.py** - QA Engineer Complete Workflow

- QA performs comprehensive feature validation
- Test suite generation (happy path, errors, security, edge cases, performance)
- Security vulnerability identification
- Validation report generation
- **Total tests**: ~4

## Running Tests

### Run All Tests

```bash
pytest src/amplihack/meta_delegation/tests/ -v
```

### Run Unit Tests Only

```bash
pytest src/amplihack/meta_delegation/tests/test_*.py -v
```

### Run Integration Tests

```bash
pytest src/amplihack/meta_delegation/tests/integration/ -v -m integration
```

### Run E2E Tests

```bash
pytest src/amplihack/meta_delegation/tests/e2e/ -v -m e2e
```

### Run Tests for Specific Module

```bash
# Platform CLI tests
pytest src/amplihack/meta_delegation/tests/test_platform_cli.py -v

# State Machine tests
pytest src/amplihack/meta_delegation/tests/test_state_machine.py -v

# Persona tests
pytest src/amplihack/meta_delegation/tests/test_persona.py -v
```

### Run with Coverage

```bash
pytest src/amplihack/meta_delegation/tests/ --cov=amplihack.meta_delegation --cov-report=html
```

### Skip Tests Requiring Platform Installation

```bash
pytest src/amplihack/meta_delegation/tests/ -v -m "not requires_platform"
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.integration` - Integration tests requiring multiple modules
- `@pytest.mark.e2e` - End-to-end tests (slower, full workflow)
- `@pytest.mark.requires_platform` - Requires platform CLI (Claude Code, Copilot, or Amplifier)

## Expected Test Results (Before Implementation)

**Current Status**: All tests skip with message "module not implemented yet"

**After Implementation Starts**: Tests will fail with specific assertion errors showing what needs to be implemented

**Target Coverage**: >80% code coverage across all modules

## Test Statistics

| Category    | Test Files | Test Count | Modules Tested            |
| ----------- | ---------- | ---------- | ------------------------- |
| Unit        | 7          | ~205       | All 7 modules             |
| Integration | 2          | ~27        | Cross-module interactions |
| E2E         | 2          | ~8         | Complete workflows        |
| **Total**   | **11**     | **~240**   | **All components**        |

## Fixtures (conftest.py)

Shared fixtures available to all tests:

- `temp_working_dir` - Temporary workspace for file operations
- `sample_code_files` - Pre-created Python modules
- `sample_test_files` - Pre-created test files
- `sample_documentation` - Pre-created markdown docs
- `sample_config_files` - Pre-created YAML/JSON configs
- `mock_subprocess` - Mock subprocess object
- `mock_platform_cli` - Mock platform CLI
- `sample_evidence_items` - Mock evidence collection
- `sample_test_scenarios` - Mock Gadugi scenarios
- `execution_log_with_success` - Sample successful execution log
- `execution_log_with_failure` - Sample failed execution log
- `sample_goal_and_criteria` - Sample delegation parameters
- `mock_persona_strategy` - Mock persona configuration
- `mock_evaluation_result` - Mock success evaluation

## Implementation Guidance

### TDD Workflow

1. **Run tests first** - All should skip or fail
2. **Implement minimal code** to pass first test
3. **Run tests again** - More tests should now fail with different errors
4. **Iterate** until all tests pass
5. **Refactor** with confidence (tests ensure no regression)

### Test Failure Analysis

When tests fail, they indicate what to implement:

**ImportError**: Module doesn't exist yet

```
ModuleNotFoundError: No module named 'amplihack.meta_delegation.platform_cli'
→ Create the platform_cli.py module
```

**AttributeError**: Class/function missing

```
AttributeError: module 'amplihack.meta_delegation.platform_cli' has no attribute 'ClaudeCodeCLI'
→ Implement the ClaudeCodeCLI class
```

**AssertionError**: Logic not implemented correctly

```
AssertionError: assert 'guide' == 'guide'
→ Implement the persona name property
```

### Implementation Order

Recommended implementation order (least to most complex):

1. **Data structures** (PersonaStrategy, EvidenceItem, TestScenario)
2. **Platform CLI abstraction** (interfaces, basic implementations)
3. **Persona strategies** (define the 4 personas)
4. **Evidence collector** (file discovery and classification)
5. **State machine** (subprocess lifecycle management)
6. **Success evaluator** (criteria parsing and scoring)
7. **Scenario generator** (Gadugi test generation)
8. **Orchestrator** (coordinate all components)

## Validation

### Test Coverage Target

- **Unit tests**: >90% coverage per module
- **Integration tests**: >80% coverage of module interactions
- **E2E tests**: Complete workflow validation
- **Overall**: >80% total coverage

### Quality Checks

Run all quality checks before considering implementation complete:

```bash
# Run all tests
pytest src/amplihack/meta_delegation/tests/ -v

# Check coverage
pytest src/amplihack/meta_delegation/tests/ --cov=amplihack.meta_delegation --cov-report=term-missing

# Type checking (if using mypy)
mypy src/amplihack/meta_delegation/

# Linting
ruff check src/amplihack/meta_delegation/
```

## References

- **Issue**: #2030 - Meta-Agentic Task Delegation System
- **Architecture**: `/docs/meta-delegation/concepts.md`
- **API Reference**: `/docs/meta-delegation/reference.md`
- **Tutorial**: `/docs/meta-delegation/tutorial.md`

## Contributing

When adding new tests:

1. Follow existing naming conventions (`test_<module>_<feature>.py`)
2. Add comprehensive docstrings
3. Use descriptive test names (`test_<what>_<condition>_<expected>`)
4. Include fixtures for reusable test data
5. Mark tests appropriately (`@pytest.mark.integration`, etc.)
6. Update this README with test counts

## Notes

- Tests use mocking extensively to isolate units under test
- E2E tests may require actual platform CLI installation (marked with `@pytest.mark.requires_platform`)
- Some tests simulate time-dependent behavior (timeouts, duration tracking)
- Binary file handling tests may be platform-specific

---

**Test Suite Version**: 1.0.0
**Created**: 2026-01-20
**Last Updated**: 2026-01-20
**Status**: Ready for implementation (all tests currently skipped/failing as expected)
