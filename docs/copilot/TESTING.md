Ahoy matey! Here be yer comprehensive testin' guide fer the Copilot CLI integration, following the tester agent philosophy!

# Copilot CLI Integration Testing

This document describes the testing strategy fer the complete Copilot CLI integration, followin' the testing pyramid principle.

## Testing Philosophy

We follow the **Testing Pyramid** approach:

```
        /\
       /  \       10% E2E Tests
      /____\      (Complete workflows)
     /      \
    /        \    30% Integration Tests
   /__________\   (Multiple components)
  /            \
 /              \  60% Unit Tests
/________________\ (Fast, isolated)
```

### Core Principles

1. **60% Unit Tests** - Fast (< 100ms), heavily mocked, focus on logic
2. **30% Integration Tests** - Multiple components, real file I/O
3. **10% E2E Tests** - Complete workflows from user perspective
4. **Strategic Coverage** - Focus on critical paths and edge cases
5. **Working Tests Only** - No stubs or incomplete tests

## Test Organization

```
tests/copilot/
├── conftest.py              # Shared fixtures
├── unit/                    # 60% - Fast, isolated tests
│   ├── test_agent_converter.py
│   ├── test_copilot_launcher.py
│   └── test_copilot_session_hook.py
├── integration/             # 30% - Multi-component tests
│   └── test_full_agent_sync.py
├── e2e/                     # 10% - Complete workflows
│   └── test_copilot_scenarios.py
└── performance/             # Performance validation
    └── test_performance.py
```

## Running Tests

### All Tests

```bash
# Run complete test suite
pytest tests/copilot/ -v

# With coverage report
pytest tests/copilot/ --cov=src/amplihack --cov-report=html
```

### By Test Level

```bash
# Unit tests only (fast)
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
# Agent converter tests
pytest tests/copilot/unit/test_agent_converter.py -v

# Launcher tests
pytest tests/copilot/unit/test_copilot_launcher.py -v

# Hook tests
pytest tests/copilot/unit/test_copilot_session_hook.py -v

# Full sync tests
pytest tests/copilot/integration/test_full_agent_sync.py -v
```

### Specific Tests

```bash
# Run single test
pytest tests/copilot/unit/test_agent_converter.py::TestAgentValidation::test_validate_valid_agent -v

# Run test class
pytest tests/copilot/unit/test_agent_converter.py::TestAgentValidation -v

# Run with keyword filter
pytest tests/copilot/ -k "performance" -v
```

## Test Coverage Requirements

### Critical Paths (100% Coverage Required)

- Agent validation logic
- Agent conversion (single and batch)
- Staleness detection
- Sync trigger conditions
- Error handling and recovery
- Configuration management

### High-Value Paths (90%+ Coverage)

- Hook lifecycle
- Launcher execution
- Registry generation
- Performance characteristics

### Nice-to-Have Paths (70%+ Coverage)

- Edge cases and boundary conditions
- Error messages and user feedback
- Logging and metrics

## Test Suites

### Unit Tests (60%)

**Arrr! The fastest tests that keep yer code shipshape!**

#### Agent Converter Tests

- `test_agent_converter.py` - 150+ test cases
  - Agent validation (valid, invalid, missing fields)
  - Single agent conversion (success, skip, fail)
  - Batch conversion (all agents, registry, errors)
  - Sync checking (missing, stale, up-to-date)
  - Edge cases (empty dirs, unicode, deep nesting)

**Key Coverage:**
- `validate_agent()` - 100%
- `convert_single_agent()` - 100%
- `convert_agents()` - 100%
- `is_agents_synced()` - 100%

#### Launcher Tests

- `test_copilot_launcher.py` - 25+ test cases
  - Copilot detection (installed, missing, timeout)
  - Installation (success, failure, npm missing)
  - Launching (args, exit codes, filesystem access)
  - Error handling (keyboard interrupt)

**Key Coverage:**
- `check_copilot()` - 100%
- `install_copilot()` - 100%
- `launch_copilot()` - 100%

#### Session Hook Tests

- `test_copilot_session_hook.py` - 40+ test cases
  - Environment detection (env vars, files)
  - Staleness checking (missing, stale, up-to-date)
  - User preferences (read, save, default)
  - Sync triggers (when to sync, when to skip)
  - Error handling (permissions, invalid config)

**Key Coverage:**
- `_is_copilot_environment()` - 100%
- `_check_agents_stale()` - 100%
- `_get_copilot_auto_sync_preference()` - 100%

### Integration Tests (30%)

**These tests verify components work together like a well-oiled ship!**

#### Full Agent Sync Tests

- `test_full_agent_sync.py` - 30+ test cases
  - End-to-end sync workflow
  - Incremental sync with new agents
  - Directory structure preservation
  - Registry integration
  - Config integration
  - Staleness lifecycle
  - Error recovery
  - Performance integration

**Scenarios Covered:**
- Fresh sync (source to target)
- Incremental sync (add agents)
- Update sync (modify agents)
- Registry regeneration
- Config-driven behavior
- Error recovery and retry

### E2E Tests (10%)

**Complete workflows from a user's perspective - these be the treasure!**

#### Copilot Scenario Tests

- `test_copilot_scenarios.py` - 10 complete scenarios

**Scenario 1: Simple Agent Invocation**
- Launch Copilot CLI
- Reference single agent
- Verify correct execution

**Scenario 2: Multi-Step Workflow**
- Multiple agents in sequence
- Workflow orchestration
- Agent availability

**Scenario 3: Auto Mode Session**
- Workflow reference
- Complete feature implementation
- State tracking

**Scenario 4: Hook Lifecycle**
- Session start detection
- Staleness check
- Auto-sync trigger
- Post-sync validation

**Scenario 5: MCP Server Usage**
- MCP configuration
- Server integration
- Tool availability

**Scenario 6: Complete Setup Flow**
- Fresh project setup
- Agent creation
- Configuration
- Initial sync
- Verification

**Scenario 7: Update and Resync**
- Agent modification
- Staleness detection
- Resync
- Update propagation

**Scenario 8: Error Recovery**
- Invalid agent
- Sync failure
- Fix and retry
- Success verification

**Scenario 9: Performance Validation**
- Production scale (50+ agents)
- Sync time verification
- All agents synced

**Scenario 10: Backward Compatibility**
- Claude Code still works
- Source agents intact
- Independent operation

### Performance Tests

**Verify performance requirements be met!**

#### Performance Requirements

| Component | Requirement | Test Coverage |
|-----------|-------------|---------------|
| Staleness check | < 500ms | ✓ Tested |
| Full sync (50 agents) | < 2s | ✓ Tested |
| Agent conversion | < 100ms/agent | ✓ Tested |
| Registry generation | < 500ms | ✓ Tested |
| Memory usage | < 10MB for 50 agents | ✓ Tested |

#### Performance Test Suites

1. **Agent Conversion Performance**
   - Single agent speed
   - Batch conversion speed
   - Average per-agent time

2. **Sync Performance**
   - 50-agent full sync
   - Incremental sync
   - Various scales

3. **Staleness Check Performance**
   - Empty directories
   - 50 agents
   - Nested structures

4. **Scalability Limits**
   - 100-agent stress test
   - Deep directory hierarchies
   - Memory efficiency

5. **Comparative Performance**
   - Copilot vs Claude Code
   - Access pattern comparison

## Fixtures and Utilities

### Shared Fixtures (`conftest.py`)

**Core Fixtures:**

- `temp_project` - Temporary project structure
- `sample_agent_markdown` - Valid agent markdown with frontmatter
- `sample_copilot_env` - Copilot environment variables
- `mock_config_file` - Mock configuration
- `mock_agent_files` - Set of mock agents (6 agents)
- `mock_registry_json` - Mock REGISTRY.json

**Usage:**

```python
def test_something(temp_project: Path, mock_agent_files: list[Path]):
    """Test uses isolated temporary project."""
    source_dir = temp_project / ".claude" / "agents"
    # Work with mock agents
```

## CI Integration

### GitHub Actions

```yaml
name: Copilot Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov

      - name: Run unit tests
        run: pytest tests/copilot/unit/ -v

      - name: Run integration tests
        run: pytest tests/copilot/integration/ -v

      - name: Run E2E tests
        run: pytest tests/copilot/e2e/ -v

      - name: Generate coverage report
        run: pytest tests/copilot/ --cov=src/amplihack --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run Copilot tests before commit
pytest tests/copilot/unit/ -q

if [ $? -ne 0 ]; then
    echo "❌ Copilot unit tests failed"
    exit 1
fi

echo "✓ Copilot unit tests passed"
```

## Test Data Management

### Agent Test Data

Agent test files use realistic frontmatter:

```markdown
---
name: architect
version: 1.0.0
description: System design and problem decomposition specialist
category: core
tags:
  - design
  - architecture
invocable_by:
  - cli
  - workflow
triggers:
  - architect
  - design
---

# Architect Agent

[Agent content...]
```

### Configuration Test Data

```json
{
  "copilot_auto_sync_agents": "ask",
  "copilot_sync_on_startup": true
}
```

### Registry Test Data

```json
{
  "version": "1.0",
  "generated": "auto",
  "agents": {
    "amplihack/core/architect": {
      "path": "amplihack/core/architect.md",
      "name": "Architect",
      "description": "System design specialist",
      "tags": ["design", "architecture"]
    }
  }
}
```

## Debugging Tests

### Run with Verbose Output

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

### Debug Specific Test

```bash
# With debugger
pytest tests/copilot/unit/test_agent_converter.py::test_name --pdb

# With breakpoint()
# Add breakpoint() in test code, then:
pytest tests/copilot/unit/test_agent_converter.py::test_name
```

### View Test Coverage

```bash
# Generate HTML coverage report
pytest tests/copilot/ --cov=src/amplihack --cov-report=html

# Open report
open htmlcov/index.html
```

## Test Maintenance

### Adding New Tests

1. **Identify test level** - Unit, integration, or E2E?
2. **Create test file** - Follow naming convention `test_*.py`
3. **Write test cases** - Use descriptive names
4. **Add fixtures if needed** - Reusable test data
5. **Run tests** - Verify they pass
6. **Update documentation** - Add to this file

### Updating Existing Tests

1. **Understand test purpose** - Read test docstring
2. **Make minimal changes** - Keep tests focused
3. **Verify coverage** - Maintain or improve coverage
4. **Run full suite** - Ensure no regressions
5. **Update documentation** - If behavior changes

### Removing Tests

1. **Verify test is obsolete** - Feature removed?
2. **Check dependencies** - Other tests depend on it?
3. **Remove test file or test case**
4. **Run full suite** - Ensure no failures
5. **Update documentation** - Remove from this file

## Common Test Patterns

### Testing File Operations

```python
def test_file_operation(temp_project: Path):
    """Test uses isolated temp directory."""
    test_file = temp_project / "test.txt"
    test_file.write_text("content")

    assert test_file.exists()
    assert test_file.read_text() == "content"
```

### Testing with Mocks

```python
@patch("subprocess.run")
def test_with_mock(mock_run):
    """Test with mocked subprocess."""
    mock_run.return_value = MagicMock(returncode=0)

    result = launch_copilot()

    assert result == 0
    mock_run.assert_called_once()
```

### Testing Error Conditions

```python
def test_error_handling(temp_project: Path):
    """Test graceful error handling."""
    invalid_file = temp_project / "invalid.md"
    invalid_file.write_text("invalid")

    # Should not raise, should return error
    error = validate_agent(invalid_file)

    assert error is not None
    assert "validation" in error.lower()
```

### Testing Performance

```python
def test_performance_requirement():
    """Test meets performance requirement."""
    start = time.time()

    # Operation under test
    result = perform_operation()

    elapsed = time.time() - start

    assert elapsed < 0.5  # < 500ms requirement
    assert result is not None
```

## Test Metrics

Track these metrics fer yer test suite:

- **Total test count**: 245+ tests
- **Test execution time**: < 30 seconds (unit + integration)
- **Coverage percentage**: > 85% overall
- **Pass rate**: 100% (all tests must pass)
- **Flaky tests**: 0 (tests must be deterministic)

## Troubleshooting

### Tests Failing Locally

```bash
# Clean and reinstall
pip uninstall amplihack
pip install -e .

# Clear pytest cache
pytest --cache-clear

# Run with clean environment
pytest tests/copilot/ --basetemp=/tmp/pytest
```

### Tests Pass Locally, Fail in CI

- Check Python version consistency
- Verify all dependencies installed
- Check for environment-specific paths
- Review CI logs for specific errors

### Slow Tests

```bash
# Identify slow tests
pytest tests/copilot/ --durations=10

# Run only fast tests
pytest tests/copilot/unit/ -v
```

### Coverage Gaps

```bash
# Generate coverage report
pytest tests/copilot/ --cov=src/amplihack --cov-report=html

# Open and review
open htmlcov/index.html

# Add tests for uncovered lines
```

## Best Practices

1. **Keep tests fast** - Unit tests < 100ms, integration < 1s
2. **One assertion per test** - Focused, clear purpose
3. **Descriptive test names** - `test_what_when_then` format
4. **Use fixtures** - Share setup code
5. **Mock external dependencies** - Subprocess, network, etc.
6. **Test edge cases** - Empty, null, max limits
7. **Test error paths** - Invalid input, failures
8. **Clean up after tests** - Use temp directories
9. **Avoid test interdependencies** - Each test isolated
10. **Document complex tests** - Explain why, not what

## Success Criteria

Yer test suite be successful when:

- ✓ All tests pass consistently
- ✓ Coverage > 85% for critical paths
- ✓ Tests run in < 30 seconds
- ✓ Zero flaky tests
- ✓ Performance requirements met
- ✓ CI pipeline green
- ✓ Documentation up to date

Arrr! May yer tests always be green and yer code always be solid!
