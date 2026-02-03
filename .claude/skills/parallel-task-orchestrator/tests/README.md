# Test Suite for Parallel Task Orchestrator

Comprehensive test suite following TDD methodology and testing pyramid principles.

## Test Structure

```
tests/
├── unit/                     # 60% - Fast, heavily mocked tests
│   ├── test_issue_parser.py           # GitHub issue parsing
│   ├── test_orchestration_config.py   # Configuration validation
│   ├── test_status_monitor.py         # Status polling and tracking
│   ├── test_agent_deployer.py         # Agent deployment and worktrees
│   ├── test_pr_creator.py             # PR generation and creation
│   └── test_models.py                 # Data models and serialization
├── integration/             # 30% - Multi-component tests
│   ├── test_orchestration_flow.py     # End-to-end component flows
│   └── test_github_integration.py     # GitHub CLI interactions
└── e2e/                     # 10% - Complete workflows
    ├── test_simple_orchestration.py   # Basic scenarios (3-5 sub-issues)
    └── test_simserv_integration.py    # Validated pattern (SimServ)
```

## Running Tests

### All Tests
```bash
pytest
```

### By Category
```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests (slow)
pytest tests/e2e/
```

### By Marker
```bash
# Skip slow tests (good for development)
pytest -m "not slow"

# Run SimServ validation tests only
pytest -m simserv

# Run specific test category
pytest -m unit
pytest -m integration
pytest -m e2e
```

### Individual Test Files
```bash
pytest tests/unit/test_issue_parser.py
pytest tests/integration/test_orchestration_flow.py -v
```

### With Coverage
```bash
pytest --cov=parallel_task_orchestrator --cov-report=html
```

## Test Philosophy

### TDD Approach
All tests are written **before** implementation following Test-Driven Development:

1. Write failing tests that define expected behavior
2. Implement code to make tests pass
3. Refactor while keeping tests green

### Testing Pyramid (60/30/10)

**Unit Tests (60%)**
- Fast execution (<100ms per test)
- Heavy use of mocks/fixtures
- Test single components in isolation
- Focus on behavior, not implementation

**Integration Tests (30%)**
- Multiple components working together
- Some mocking, but real interactions
- Test realistic workflows
- Verify component contracts

**E2E Tests (10%)**
- Complete orchestration workflows
- Minimal mocking (mostly subprocess)
- Slow but comprehensive
- Validate real-world scenarios

## Test Coverage Requirements

### Unit Test Coverage
- **IssueParser**: Parse formats, error handling, edge cases
- **OrchestrationConfig**: Validation, defaults, serialization
- **StatusMonitor**: Polling, timeouts, completion detection
- **AgentDeployer**: Worktree creation, agent launching
- **PRCreator**: PR body generation, gh CLI invocation
- **Models**: Serialization, validation, state transitions

### Integration Test Coverage
- Issue parsing → config creation
- Agent deployment → status monitoring
- Agent completion → PR creation
- Error handling and recovery

### E2E Test Coverage
- Simple orchestration (3 sub-issues, 100% success)
- Complex orchestration (5+ sub-issues, partial failures)
- SimServ validation (replicate proven pattern)

## Key Test Patterns

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("case1", result1),
    ("case2", result2),
])
def test_multiple_cases(input, expected):
    assert function(input) == expected
```

### Fixture Usage
```python
def test_with_fixtures(temp_dir, mock_gh_cli):
    # Use shared fixtures from conftest.py
    pass
```

### Mocking Subprocess
```python
@patch("subprocess.run")
def test_with_gh_cli(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="output")
    # Test gh CLI interactions
```

## Test Data

All test data is defined in `conftest.py`:
- `sample_issue_body`: GitHub issue with sub-issues
- `sample_agent_status`: Agent status data
- `mock_worktree_structure`: Temporary worktree setup
- `sample_orchestration_config`: Config parameters

## Expected Test Results

**All tests should FAIL initially** (TDD - tests before code):

```bash
$ pytest
================================ test session starts =================================
collected 150 items

tests/unit/test_issue_parser.py::TestGitHubIssueParser::test_parse_sub_issues_hash_format FAILED
tests/unit/test_issue_parser.py::TestGitHubIssueParser::test_parse_sub_issues_various_formats FAILED
...

================================ 150 failed in 5.23s =================================
```

After implementation, all tests should PASS:

```bash
$ pytest
================================ test session starts =================================
collected 150 items

tests/unit/test_issue_parser.py ..................................... [ 23%]
tests/unit/test_orchestration_config.py ........................... [ 40%]
tests/unit/test_status_monitor.py ................................ [ 58%]
tests/unit/test_agent_deployer.py ................................ [ 72%]
tests/unit/test_pr_creator.py .................................... [ 85%]
tests/integration/test_orchestration_flow.py ..................... [ 95%]
tests/e2e/test_simple_orchestration.py ........................... [100%]

================================ 150 passed in 12.45s ================================
```

## Philosophy Alignment

These tests follow ruthless simplicity:
- Test behavior, not implementation details
- No stub tests (all tests executable)
- Clear test names describing what's validated
- Fast feedback loop (unit tests <5s total)

## Next Steps

1. Run tests: `pytest` (all should fail initially)
2. Implement components to make tests pass
3. Add more tests as edge cases discovered
4. Maintain 60/30/10 pyramid ratio
