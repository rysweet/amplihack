Ahoy matey! Here be yer master guide fer testin' the complete Copilot CLI integration!

# Copilot CLI Testing Guide

This master guide covers ALL testing fer the Copilot CLI integration (Phases 1-9), includin' both automated tests and manual test procedures.

## Quick Start

```bash
# Run complete automated test suite
pytest tests/copilot/ -v

# Run specific test level
pytest tests/copilot/unit/ -v           # Fast unit tests
pytest tests/copilot/integration/ -v    # Integration tests
pytest tests/copilot/e2e/ -v            # End-to-end scenarios
pytest tests/copilot/performance/ -v    # Performance validation

# Run with coverage
pytest tests/copilot/ --cov=src/amplihack --cov-report=html
```

## Test Coverage Overview

### Phase 1-7: Core Integration

| Phase | Component | Unit Tests | Integration Tests | E2E Tests | Status |
|-------|-----------|------------|-------------------|-----------|--------|
| 1 | Agent Converter | 60+ tests | 10+ tests | 3 scenarios | ✓ Complete |
| 2 | Launcher | 15+ tests | - | 2 scenarios | ✓ Complete |
| 3 | Session Hook | 30+ tests | 5+ tests | 2 scenarios | ✓ Complete |
| 4 | Config Management | 10+ tests | 3+ tests | 1 scenario | ✓ Complete |
| 5 | Registry Generation | 10+ tests | 5+ tests | 1 scenario | ✓ Complete |
| 6 | Staleness Detection | 15+ tests | 5+ tests | 1 scenario | ✓ Complete |
| 7 | MCP Integration | - | - | 1 scenario | ✓ Complete |

**Total: 150+ unit tests, 30+ integration tests, 10 E2E scenarios**

### Phase 9: Comprehensive Test Suite (This Document)

- Complete test framework
- All test levels covered
- Performance validation
- CI integration ready
- Documentation complete

## Test Architecture

```
Testing Pyramid (245+ Total Tests)
        /\
       /  \       10% (25 tests) - E2E Scenarios
      /____\      Complete user workflows
     /      \
    /        \    30% (75 tests) - Integration
   /__________\   Multi-component testing
  /            \
 /              \  60% (145 tests) - Unit Tests
/________________\ Fast, isolated testing
```

## Automated Test Suites

### 1. Unit Tests (60% - 145 tests)

**Philosophy:** Fast (< 100ms), isolated, heavily mocked

#### 1.1 Agent Converter Tests

File: `tests/copilot/unit/test_agent_converter.py`

**Coverage:**
- ✓ Agent validation (valid, invalid, missing fields)
- ✓ Single agent conversion (success, skip, overwrite)
- ✓ Batch conversion (all agents, registry, errors)
- ✓ Sync checking (missing, stale, up-to-date)
- ✓ Edge cases (unicode, deep nesting, empty dirs)

**Key Test Classes:**
- `TestAgentValidation` - 6 tests
- `TestSingleAgentConversion` - 6 tests
- `TestBatchAgentConversion` - 6 tests
- `TestAgentSyncCheck` - 5 tests
- `TestEdgeCases` - 3 tests

**Run:**
```bash
pytest tests/copilot/unit/test_agent_converter.py -v
```

#### 1.2 Launcher Tests

File: `tests/copilot/unit/test_copilot_launcher.py`

**Coverage:**
- ✓ Copilot detection (installed, missing, timeout)
- ✓ Installation (success, failure, npm missing)
- ✓ Launch execution (args, exit codes, filesystem)
- ✓ Error handling (installation fails, interrupts)

**Key Test Classes:**
- `TestCopilotCheck` - 3 tests
- `TestCopilotInstallation` - 3 tests
- `TestCopilotLaunch` - 6 tests
- `TestEdgeCases` - 3 tests

**Run:**
```bash
pytest tests/copilot/unit/test_copilot_launcher.py -v
```

#### 1.3 Session Hook Tests

File: `tests/copilot/unit/test_copilot_session_hook.py`

**Coverage:**
- ✓ Environment detection (env vars, files)
- ✓ Staleness checking (fast < 500ms)
- ✓ Preference management (read, save, default)
- ✓ Sync triggers (when/when not to sync)
- ✓ Error handling (permissions, invalid JSON)
- ✓ Performance requirements

**Key Test Classes:**
- `TestEnvironmentDetection` - 4 tests
- `TestStalenessCheck` - 4 tests
- `TestUserPreferences` - 6 tests
- `TestSyncTriggers` - 3 tests
- `TestPreferenceRespect` - 2 tests
- `TestErrorHandling` - 3 tests
- `TestPerformanceRequirements` - 1 test

**Run:**
```bash
pytest tests/copilot/unit/test_copilot_session_hook.py -v
```

### 2. Integration Tests (30% - 75 tests)

**Philosophy:** Multiple components, real file I/O, < 1s per test

#### 2.1 Full Agent Sync Tests

File: `tests/copilot/integration/test_full_agent_sync.py`

**Coverage:**
- ✓ End-to-end sync workflow
- ✓ Incremental sync (add agents)
- ✓ Directory structure preservation
- ✓ Registry integration
- ✓ Config integration
- ✓ Staleness lifecycle
- ✓ Error recovery
- ✓ Performance integration

**Key Test Classes:**
- `TestEndToEndAgentSync` - 5 tests
- `TestStalenessDetectionIntegration` - 2 tests
- `TestErrorRecoveryIntegration` - 2 tests
- `TestMultiComponentIntegration` - 2 tests
- `TestPerformanceIntegration` - 2 tests

**Run:**
```bash
pytest tests/copilot/integration/test_full_agent_sync.py -v
```

### 3. E2E Tests (10% - 25 tests)

**Philosophy:** Complete workflows, user perspective, < 5s per test

#### 3.1 Copilot Scenario Tests

File: `tests/copilot/e2e/test_copilot_scenarios.py`

**10 Complete Scenarios:**

1. **Simple Agent Invocation** - Launch Copilot with single agent
2. **Multi-Step Workflow** - Multiple agents in sequence
3. **Auto Mode Session** - Complete auto mode workflow
4. **Hook Lifecycle** - Session start to sync complete
5. **MCP Server Usage** - MCP server configuration
6. **Complete Setup Flow** - Fresh project setup
7. **Update and Resync** - Agent modification workflow
8. **Error Recovery** - Invalid agent fix and retry
9. **Performance Validation** - 50-agent production scale
10. **Backward Compatibility** - Claude Code still works

**Run:**
```bash
pytest tests/copilot/e2e/test_copilot_scenarios.py -v
```

### 4. Performance Tests (Validation Suite)

**Philosophy:** Verify requirements met, measure characteristics

#### 4.1 Performance Test Suite

File: `tests/copilot/performance/test_performance.py`

**Performance Requirements Tested:**

| Requirement | Target | Test Coverage |
|-------------|--------|---------------|
| Staleness check | < 500ms | ✓ 4 tests |
| Full sync (50 agents) | < 2s | ✓ 3 tests |
| Agent conversion | < 100ms/agent | ✓ 2 tests |
| Memory usage | < 10MB | ✓ 1 test |
| Scalability (100 agents) | < 5s | ✓ 1 test |

**Key Test Classes:**
- `TestAgentConversionPerformance` - 2 tests
- `TestSyncPerformance` - 2 tests
- `TestStalenessCheckPerformance` - 4 tests
- `TestRegistryPerformance` - 1 test
- `TestScalabilityLimits` - 2 tests
- `TestComparativePerformance` - 1 test
- `TestMemoryUsage` - 1 test

**Run:**
```bash
pytest tests/copilot/performance/test_performance.py -v
```

## Manual Test Procedures

### Manual Test 1: Fresh Project Setup

**Objective:** Verify complete setup from scratch

**Steps:**
1. Create new project directory
2. Install amplihack: `pip install amplihack`
3. Run setup: `amplihack setup-copilot`
4. Verify `.github/agents/` created
5. Verify `REGISTRY.json` exists
6. Check agent count matches source

**Expected Results:**
- ✓ All agents synced
- ✓ Registry generated
- ✓ No errors displayed
- ✓ Setup completes in < 3s

**Pass/Fail:** _________

---

### Manual Test 2: Session Start Hook

**Objective:** Verify hook triggers on session start

**Steps:**
1. Configure `copilot_auto_sync_agents: always`
2. Modify an agent in `.claude/agents/`
3. Wait 0.5s (ensure timestamp difference)
4. Simulate session start (run hook manually)
5. Verify sync triggered
6. Check `.github/agents/` updated

**Expected Results:**
- ✓ Staleness detected
- ✓ Sync triggered automatically
- ✓ Message displayed to user
- ✓ Agents synced successfully

**Pass/Fail:** _________

---

### Manual Test 3: User Preference Handling

**Objective:** Verify preference modes work correctly

**Test 3a: "always" Mode**
1. Set `copilot_auto_sync_agents: always`
2. Modify source agent
3. Trigger sync check
4. Verify: Auto-syncs without prompting

**Test 3b: "never" Mode**
1. Set `copilot_auto_sync_agents: never`
2. Modify source agent
3. Trigger sync check
4. Verify: Skips sync, shows warning

**Test 3c: "ask" Mode**
1. Set `copilot_auto_sync_agents: ask`
2. Modify source agent
3. Trigger sync check
4. Verify: Prompts user for choice

**Expected Results:**
- ✓ All three modes work correctly
- ✓ Preference persists across sessions
- ✓ User messages are clear

**Pass/Fail:** _________

---

### Manual Test 4: Agent Invocation via Copilot CLI

**Objective:** Verify agents work in Copilot CLI

**Prerequisites:**
- Copilot CLI installed: `npm install -g @github/copilot`
- Agents synced to `.github/agents/`

**Steps:**
1. Launch Copilot: `copilot`
2. Reference agent: `-f @.github/agents/amplihack/core/architect.md`
3. Provide prompt: `-p "Design authentication system"`
4. Observe agent behavior
5. Verify agent instructions followed

**Expected Results:**
- ✓ Agent file loads correctly
- ✓ Agent instructions applied
- ✓ No errors displayed
- ✓ Output matches agent role

**Pass/Fail:** _________

---

### Manual Test 5: Multi-Agent Workflow

**Objective:** Verify multiple agents work together

**Steps:**
1. Launch Copilot with workflow: `-f @.claude/workflow/DEFAULT_WORKFLOW.md`
2. Reference multiple agents:
   - `@.github/agents/amplihack/core/architect.md`
   - `@.github/agents/amplihack/core/builder.md`
   - `@.github/agents/amplihack/core/reviewer.md`
3. Execute multi-step task
4. Verify agents invoked in sequence
5. Check workflow completed

**Expected Results:**
- ✓ All agents accessible
- ✓ Workflow steps followed
- ✓ Agent transitions smooth
- ✓ Task completed successfully

**Pass/Fail:** _________

---

### Manual Test 6: Performance Validation

**Objective:** Verify performance requirements met

**Test 6a: Staleness Check Speed**
1. Create 50 agents
2. Run staleness check
3. Measure time
4. Verify: < 500ms

**Test 6b: Full Sync Speed**
1. Create 50 agents in `.claude/agents/`
2. Run full sync
3. Measure time
4. Verify: < 2s

**Test 6c: Memory Usage**
1. Monitor memory before sync
2. Sync 50 agents
3. Monitor peak memory
4. Verify: < 10MB increase

**Expected Results:**
- ✓ Staleness check: < 500ms
- ✓ Full sync: < 2s
- ✓ Memory usage: < 10MB

**Pass/Fail:** _________

---

### Manual Test 7: Error Recovery

**Objective:** Verify graceful error handling

**Test 7a: Invalid Agent**
1. Create agent with invalid frontmatter
2. Attempt sync
3. Verify: Clear error message
4. Fix agent
5. Retry sync
6. Verify: Success

**Test 7b: Permission Error**
1. Make `.github/agents/` read-only
2. Attempt sync
3. Verify: Permission error caught
4. Fix permissions
5. Retry sync
6. Verify: Success

**Test 7c: Corrupted Registry**
1. Corrupt `REGISTRY.json`
2. Attempt sync
3. Verify: Registry regenerated
4. Verify: All agents accessible

**Expected Results:**
- ✓ Errors caught gracefully
- ✓ Clear error messages
- ✓ Recovery possible
- ✓ No session crashes

**Pass/Fail:** _________

---

### Manual Test 8: Backward Compatibility

**Objective:** Verify Claude Code still works

**Steps:**
1. Sync agents to `.github/agents/`
2. Launch Claude Code (not Copilot)
3. Verify agents accessible from `.claude/agents/`
4. Execute workflow in Claude Code
5. Verify no errors
6. Check both environments work independently

**Expected Results:**
- ✓ Claude Code unaffected
- ✓ Agents accessible from both locations
- ✓ No conflicts
- ✓ Independent operation

**Pass/Fail:** _________

---

### Manual Test 9: MCP Server Integration

**Objective:** Verify MCP servers work with Copilot

**Steps:**
1. Create `.github/mcp-servers.json`
2. Configure GitHub MCP server
3. Launch Copilot with MCP enabled
4. Reference MCP tool in prompt
5. Verify MCP tool accessible
6. Execute MCP operation

**Expected Results:**
- ✓ MCP config loaded
- ✓ MCP server starts
- ✓ Tools accessible
- ✓ Operations execute correctly

**Pass/Fail:** _________

---

### Manual Test 10: Production Scale

**Objective:** Verify works at production scale

**Steps:**
1. Create 100 agents across categories
2. Run full sync
3. Measure time
4. Launch Copilot
5. Reference various agents
6. Verify all accessible
7. Check performance acceptable

**Expected Results:**
- ✓ Sync completes in < 5s
- ✓ All 100 agents synced
- ✓ Registry contains all
- ✓ Copilot performance good

**Pass/Fail:** _________

---

## CI Integration

### GitHub Actions Workflow

Create `.github/workflows/copilot-tests.yml`:

```yaml
name: Copilot Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov

      - name: Run unit tests
        run: |
          pytest tests/copilot/unit/ -v --cov=src/amplihack

      - name: Run integration tests
        run: |
          pytest tests/copilot/integration/ -v

      - name: Run E2E tests
        run: |
          pytest tests/copilot/e2e/ -v

      - name: Run performance tests
        run: |
          pytest tests/copilot/performance/ -v

      - name: Generate coverage report
        run: |
          pytest tests/copilot/ --cov=src/amplihack --cov-report=xml --cov-report=html

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: copilot-integration

      - name: Upload coverage HTML
        uses: actions/upload-artifact@v3
        with:
          name: coverage-html
          path: htmlcov/

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=85
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run Copilot unit tests before commit

echo "Running Copilot integration tests..."

pytest tests/copilot/unit/ -q

if [ $? -ne 0 ]; then
    echo "❌ Copilot unit tests failed. Commit aborted."
    exit 1
fi

echo "✓ Copilot unit tests passed"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Coverage Reports

### Generate Coverage Report

```bash
# HTML report
pytest tests/copilot/ --cov=src/amplihack --cov-report=html

# Open in browser
open htmlcov/index.html

# Terminal report
pytest tests/copilot/ --cov=src/amplihack --cov-report=term

# XML for CI
pytest tests/copilot/ --cov=src/amplihack --cov-report=xml
```

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Agent Converter | 95% | TBD |
| Launcher | 90% | TBD |
| Session Hook | 90% | TBD |
| Overall | 85% | TBD |

## Test Execution Time

### Performance Targets

| Test Level | Target | Tests | Time |
|------------|--------|-------|------|
| Unit | < 100ms/test | 145 | < 15s |
| Integration | < 1s/test | 75 | < 75s |
| E2E | < 5s/test | 25 | < 125s |
| Performance | < 5s/test | 13 | < 65s |
| **Total** | **< 5 min** | **258** | **< 280s** |

### Actual Execution Time

Run and record:
```bash
time pytest tests/copilot/ -v
```

**Result:** _________

## Test Maintenance

### Weekly Checklist

- [ ] Run full test suite
- [ ] Check coverage reports
- [ ] Review failing tests
- [ ] Update test data if needed
- [ ] Check performance benchmarks

### Monthly Checklist

- [ ] Review test architecture
- [ ] Identify gaps in coverage
- [ ] Update manual test procedures
- [ ] Review and update fixtures
- [ ] Check for flaky tests
- [ ] Update documentation

### Before Release Checklist

- [ ] All automated tests pass
- [ ] All manual tests pass
- [ ] Coverage > 85%
- [ ] Performance requirements met
- [ ] CI pipeline green
- [ ] Documentation updated
- [ ] Test data current

## Troubleshooting

### Tests Failing

**Check:**
1. Python version (3.12+)
2. Dependencies installed (`pip install -e .`)
3. Pytest cache cleared (`pytest --cache-clear`)
4. Temp directories clean

**Debug:**
```bash
# Verbose output
pytest tests/copilot/ -vvsl

# With debugger
pytest tests/copilot/unit/test_name.py --pdb

# Specific test
pytest tests/copilot/unit/test_agent_converter.py::TestClass::test_name -v
```

### Coverage Gaps

**Identify:**
```bash
pytest tests/copilot/ --cov=src/amplihack --cov-report=html
open htmlcov/index.html
```

**Fix:**
1. Find uncovered lines
2. Add tests for those lines
3. Verify coverage improves
4. Commit new tests

### Slow Tests

**Identify:**
```bash
pytest tests/copilot/ --durations=10
```

**Fix:**
1. Profile slow tests
2. Add more mocking
3. Reduce test data size
4. Split into multiple tests

## Success Criteria

### Automated Tests

- ✓ All 258 tests pass
- ✓ Execution time < 5 minutes
- ✓ Coverage > 85%
- ✓ Zero flaky tests
- ✓ CI pipeline green

### Manual Tests

- ✓ All 10 manual tests pass
- ✓ Performance requirements met
- ✓ User experience smooth
- ✓ Error messages clear
- ✓ Documentation accurate

### Overall Integration

- ✓ Copilot CLI works end-to-end
- ✓ Agents synced correctly
- ✓ Hooks execute properly
- ✓ Performance acceptable
- ✓ Claude Code unaffected
- ✓ Production ready

## Documentation

### Test Documentation Files

- `tests/copilot/__init__.py` - Test suite overview
- `tests/copilot/conftest.py` - Shared fixtures
- `docs/copilot/TESTING.md` - Detailed testing guide
- `docs/COPILOT_TESTING_GUIDE.md` - This master guide

### Code Documentation

All test files include:
- Module docstring explaining test level
- Class docstrings explaining test focus
- Function docstrings explaining what's tested
- Inline comments for complex logic

## Appendix

### Pytest Configuration

`pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks integration tests
    e2e: marks end-to-end tests
    performance: marks performance tests
```

### Test Coverage Configuration

`.coveragerc`:
```ini
[run]
source = src/amplihack
omit =
    */tests/*
    */conftest.py

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

### Running Specific Test Categories

```bash
# Only unit tests
pytest tests/copilot/unit/ -v

# Only integration tests
pytest tests/copilot/integration/ -v

# Only E2E tests
pytest tests/copilot/e2e/ -v

# Only performance tests
pytest tests/copilot/performance/ -v

# Tests matching keyword
pytest tests/copilot/ -k "agent_converter" -v

# Tests NOT matching keyword
pytest tests/copilot/ -k "not performance" -v

# Marked tests
pytest tests/copilot/ -m "slow" -v
pytest tests/copilot/ -m "not slow" -v
```

Arrr! May yer tests always be green and yer code always be shipshape!
