# End-to-End Integration Test Suite

[PLANNED - Implementation Pending]

Comprehensive end-to-end integration tests for the meta-delegation system with real subprocess execution, lifecycle management, and orchestration validation.

## Overview

The E2E test suite validates the complete meta-delegation system through real subprocess execution. Unlike unit and integration tests that use mocks, these tests spawn actual subprocesses, manage their lifecycle, handle errors, and verify multi-step orchestration.

**Architecture**: Three-layer testing strategy

- **Layer 1**: Subprocess spawning and lifecycle management
- **Layer 2**: Error handling and propagation
- **Layer 3**: Multi-step orchestration workflows

**Key Features**:

- Real subprocess execution via CLISubprocessAdapter
- Automatic cleanup with SubprocessLifecycleManager
- Isolated test environments with TestWorkspaceFixture
- CI/CD compatible with aggressive timeouts
- Comprehensive error propagation testing

## Quick Start

### Run All E2E Tests

```bash
# Run complete E2E suite
pytest tests/meta_delegation/e2e/ -v -m e2e

# Run with verbose subprocess output
pytest tests/meta_delegation/e2e/ -v -s --log-cli-level=DEBUG

# Run specific test layer
pytest tests/meta_delegation/e2e/test_real_subprocess_execution.py -v
```

### Run Single Test

```bash
# Test subprocess spawning
pytest tests/meta_delegation/e2e/test_real_subprocess_execution.py::test_spawn_python_subprocess -v

# Test error propagation
pytest tests/meta_delegation/e2e/test_error_propagation.py::test_timeout_kills_process -v

# Test orchestration
pytest tests/meta_delegation/e2e/test_multi_step_orchestration.py::test_guide_persona_workflow -v
```

## Test Architecture

### Three-Layer Testing Strategy

```
┌─────────────────────────────────────────────┐
│  Layer 3: Multi-Step Orchestration          │
│  - Complete workflows (guide, QA engineer)  │
│  - Evidence collection across steps         │
│  - Success evaluation                       │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Layer 2: Error Propagation                 │
│  - Timeout handling                         │
│  - Process crashes                          │
│  - Error message capture                    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Layer 1: Subprocess Lifecycle              │
│  - Spawn processes                          │
│  - Monitor execution                        │
│  - Automatic cleanup                        │
└─────────────────────────────────────────────┘
```

**Rationale**: Bottom-up validation ensures each layer works before testing higher abstractions. If Layer 1 fails (can't spawn processes), Layer 2 and 3 tests will skip with clear diagnostics.

### Test Files

| File                                | Layer | Focus                             | Test Count |
| ----------------------------------- | ----- | --------------------------------- | ---------- |
| `test_real_subprocess_execution.py` | 1     | Subprocess spawning and lifecycle | ~12        |
| `test_error_propagation.py`         | 2     | Error handling and timeouts       | ~10        |
| `test_multi_step_orchestration.py`  | 3     | Complete workflows                | ~8         |

## Layer 1: Subprocess Execution

**File**: `test_real_subprocess_execution.py`

Tests real subprocess spawning, monitoring, and cleanup.

### What It Tests

```python
# [PLANNED] - Example test structure
def test_spawn_python_subprocess(test_workspace):
    """Spawn Python subprocess and verify execution."""
    adapter = CLISubprocessAdapter()

    # Spawn process
    result = adapter.spawn(
        command=["python", "-c", "print('hello')"],
        working_dir=test_workspace.path
    )

    # Verify execution
    assert result.exit_code == 0
    assert "hello" in result.stdout
    assert result.duration < 5.0

def test_subprocess_cleanup_on_exit(test_workspace):
    """Verify subprocess cleanup on test completion."""
    lifecycle_mgr = SubprocessLifecycleManager()

    # Spawn long-running process
    proc = lifecycle_mgr.spawn(
        command=["python", "-c", "import time; time.sleep(100)"],
        working_dir=test_workspace.path
    )

    # Manager automatically kills on scope exit
    assert proc.is_alive()
    # Test cleanup verifies process terminated
```

### Key Features

- **Real execution**: Spawns actual Python/shell processes
- **Automatic cleanup**: SubprocessLifecycleManager kills processes on test exit
- **Isolated workspaces**: Each test gets temporary directory
- **Timeout handling**: Tests fail fast on hangs (default: 30s)

### Fixtures

#### `test_workspace`

Provides isolated temporary directory for each test:

```python
# [PLANNED] - Fixture implementation
@pytest.fixture
def test_workspace(tmp_path):
    """Create isolated test workspace with cleanup."""
    workspace = TestWorkspaceFixture(tmp_path / "workspace")
    workspace.setup()
    yield workspace
    workspace.teardown()  # Removes all files
```

**Provides**:

- `workspace.path`: Temporary directory path
- `workspace.write_file()`: Write test files
- `workspace.read_file()`: Read test output
- `workspace.list_files()`: List created files

#### `subprocess_lifecycle_manager`

Manages subprocess lifecycle with automatic cleanup:

```python
# [PLANNED] - Fixture implementation
@pytest.fixture
def subprocess_lifecycle_manager():
    """Subprocess manager with automatic cleanup."""
    manager = SubprocessLifecycleManager()
    yield manager
    manager.cleanup_all()  # Kills all spawned processes
```

**Provides**:

- `manager.spawn()`: Spawn process with tracking
- `manager.is_alive(pid)`: Check if process running
- `manager.kill(pid)`: Terminate specific process
- `manager.cleanup_all()`: Kill all tracked processes

### Tests

#### Subprocess Spawning

- `test_spawn_python_subprocess` - Basic Python execution
- `test_spawn_shell_command` - Shell command execution
- `test_spawn_with_environment_variables` - Custom env vars
- `test_capture_stdout_stderr` - Output capture

#### Process Monitoring

- `test_monitor_running_process` - Track execution state
- `test_detect_process_completion` - Completion detection
- `test_track_execution_duration` - Duration measurement

#### Lifecycle Management

- `test_subprocess_cleanup_on_exit` - Automatic cleanup
- `test_cleanup_multiple_processes` - Batch cleanup
- `test_cleanup_on_test_failure` - Cleanup after failures
- `test_kill_orphaned_processes` - Orphan detection

#### Working Directory

- `test_subprocess_uses_working_directory` - CWD configuration
- `test_isolated_workspace_per_test` - Isolation verification

## Layer 2: Error Propagation

**File**: `test_error_propagation.py`

Tests error handling, timeout management, and failure recovery.

### What It Tests

```python
# [PLANNED] - Example test structure
def test_timeout_kills_process(test_workspace):
    """Verify timeout kills long-running process."""
    adapter = CLISubprocessAdapter(timeout=5)

    # Spawn process that exceeds timeout
    with pytest.raises(SubprocessTimeoutError) as exc_info:
        adapter.spawn(
            command=["python", "-c", "import time; time.sleep(100)"],
            working_dir=test_workspace.path
        )

    # Verify timeout error details
    assert exc_info.value.timeout == 5
    assert exc_info.value.duration >= 5
    assert "exceeded timeout" in str(exc_info.value)

def test_capture_error_output(test_workspace):
    """Verify stderr capture on process failure."""
    adapter = CLISubprocessAdapter()

    # Spawn process that writes to stderr and fails
    result = adapter.spawn(
        command=["python", "-c", "import sys; sys.stderr.write('error'); sys.exit(1)"],
        working_dir=test_workspace.path
    )

    # Verify error capture
    assert result.exit_code == 1
    assert "error" in result.stderr
```

### Key Features

- **Timeout enforcement**: Processes killed after timeout
- **Error capture**: Full stderr/stdout preserved
- **Exit code tracking**: Non-zero exit codes detected
- **Graceful degradation**: Cleanup even on errors

### Tests

#### Timeout Handling

- `test_timeout_kills_process` - Basic timeout enforcement
- `test_timeout_cleans_up_resources` - Cleanup after timeout
- `test_custom_timeout_per_subprocess` - Per-process timeouts
- `test_no_timeout_for_quick_completion` - Fast processes succeed

#### Error Capture

- `test_capture_error_output` - Stderr capture
- `test_capture_mixed_stdout_stderr` - Combined output
- `test_preserve_error_messages` - Message preservation

#### Failure Recovery

- `test_cleanup_after_process_crash` - Crash cleanup
- `test_recover_from_spawn_failure` - Spawn error handling
- `test_continue_after_subprocess_error` - Workflow continuation

#### CI/CD Compatibility

- `test_aggressive_timeout_in_ci` - Fast failure in CI
- `test_no_hanging_processes_in_ci` - CI process cleanup

## Layer 3: Multi-Step Orchestration

**File**: `test_multi_step_orchestration.py`

Tests complete meta-delegation workflows with multiple subprocess steps.

### What It Tests

```python
# [PLANNED] - Example test structure
def test_guide_persona_workflow(test_workspace):
    """Complete guide persona workflow with multiple steps."""
    orchestrator = MetaDelegationOrchestrator(
        persona="guide",
        platform="claude_code"
    )

    # Run complete workflow
    result = orchestrator.run(
        goal="Teach REST API concepts",
        success_criteria="Has tutorial, working example, documentation",
        working_dir=test_workspace.path
    )

    # Verify workflow completion
    assert result.completed
    assert result.steps_executed == 3
    assert result.success_score >= 80

    # Verify evidence collected
    assert "tutorial.md" in result.evidence.files
    assert "example.py" in result.evidence.files
    assert "README.md" in result.evidence.files

def test_error_recovery_in_workflow(test_workspace):
    """Verify workflow continues after recoverable errors."""
    orchestrator = MetaDelegationOrchestrator(
        persona="qa_engineer",
        platform="claude_code"
    )

    # Simulate step failure
    with patch('amplihack.meta_delegation.CLISubprocessAdapter.spawn') as mock_spawn:
        # First step fails, second succeeds
        mock_spawn.side_effect = [
            SubprocessError("Connection lost"),
            SubprocessResult(exit_code=0, stdout="Success")
        ]

        result = orchestrator.run(
            goal="Validate feature",
            retry_on_failure=True,
            working_dir=test_workspace.path
        )

    # Verify recovery
    assert result.completed
    assert result.retry_count == 1
```

### Key Features

- **Multi-step execution**: Complete workflows (3-5 steps)
- **Evidence collection**: Files tracked across steps
- **Success evaluation**: Criteria validated after completion
- **Error recovery**: Retry failed steps

### Tests

#### Complete Workflows

- `test_guide_persona_workflow` - Guide teaching workflow
- `test_qa_engineer_workflow` - QA validation workflow

#### Step Coordination

- `test_sequential_step_execution` - Ordered execution
- `test_step_dependencies` - Dependency validation
- `test_evidence_accumulation_across_steps` - Evidence tracking

#### Error Recovery

- `test_error_recovery_in_workflow` - Retry on failure
- `test_partial_workflow_completion` - Graceful partial success
- `test_workflow_cleanup_on_error` - Cleanup on abort

#### Success Evaluation

- `test_success_criteria_validation` - Criteria checking
- `test_evidence_based_scoring` - Score calculation

## Fixtures Reference

### TestWorkspaceFixture

Isolated temporary workspace for each test.

**Usage**:

```python
def test_example(test_workspace):
    # Write test input
    test_workspace.write_file("input.txt", "test data")

    # Run subprocess
    run_subprocess(working_dir=test_workspace.path)

    # Read output
    output = test_workspace.read_file("output.txt")
    assert "expected" in output
```

**Methods**:

- `write_file(path, content)` - Write file in workspace
- `read_file(path)` - Read file from workspace
- `list_files(pattern="*")` - List files matching pattern
- `path` - Workspace directory path

### SubprocessLifecycleManager

Manages subprocess lifecycle with automatic cleanup.

**Usage**:

```python
def test_example(subprocess_lifecycle_manager):
    # Spawn process (tracked automatically)
    proc = subprocess_lifecycle_manager.spawn(
        command=["python", "script.py"],
        working_dir="/tmp/test"
    )

    # Manager cleans up on test exit
```

**Methods**:

- `spawn(command, working_dir, timeout=30)` - Spawn tracked process
- `is_alive(pid)` - Check if process running
- `kill(pid)` - Terminate process
- `cleanup_all()` - Kill all tracked processes

### CLISubprocessAdapter

Adapter for spawning and monitoring subprocesses.

**Usage**:

```python
def test_example():
    adapter = CLISubprocessAdapter(timeout=60)

    result = adapter.spawn(
        command=["python", "-c", "print('test')"],
        working_dir="/tmp"
    )

    assert result.exit_code == 0
    assert "test" in result.stdout
```

**Parameters**:

- `timeout` - Maximum execution time (seconds)
- `capture_output` - Capture stdout/stderr (default: True)
- `check` - Raise exception on non-zero exit (default: False)

**Returns**: `SubprocessResult`

- `exit_code` - Process exit code
- `stdout` - Standard output
- `stderr` - Standard error
- `duration` - Execution time (seconds)

## Running Tests

### Local Development

```bash
# Run all E2E tests
pytest tests/meta_delegation/e2e/ -v

# Run specific layer
pytest tests/meta_delegation/e2e/test_real_subprocess_execution.py -v

# Run with subprocess output
pytest tests/meta_delegation/e2e/ -v -s --log-cli-level=DEBUG

# Run single test
pytest tests/meta_delegation/e2e/test_real_subprocess_execution.py::test_spawn_python_subprocess -v
```

### CI/CD

E2E tests use aggressive timeouts in CI to prevent hanging:

```bash
# CI configuration (automatic detection)
export CI=true

# Run with strict timeouts
pytest tests/meta_delegation/e2e/ -v --timeout=300

# Skip slow tests
pytest tests/meta_delegation/e2e/ -v -m "not slow"
```

**CI Timeouts**:

- Subprocess default: 30s (vs 60s locally)
- Per-test: 60s (vs 120s locally)
- Total suite: 300s (5 minutes)

### Debugging

```bash
# Keep failed test workspaces
pytest tests/meta_delegation/e2e/ -v --keep-workspaces

# Show subprocess commands
pytest tests/meta_delegation/e2e/ -v --subprocess-verbose

# Disable cleanup (manual cleanup required)
pytest tests/meta_delegation/e2e/ -v --no-subprocess-cleanup
```

## Test Markers

E2E tests use pytest markers for categorization:

```python
@pytest.mark.e2e              # End-to-end test
@pytest.mark.subprocess       # Requires subprocess execution
@pytest.mark.slow             # Takes >10 seconds
@pytest.mark.requires_cleanup # Requires lifecycle manager
```

**Run by marker**:

```bash
# Only E2E tests
pytest -v -m e2e

# Skip slow tests
pytest -v -m "not slow"

# Only subprocess tests
pytest -v -m subprocess
```

## Troubleshooting

### Tests Hang

**Symptom**: Tests never complete, no output

**Cause**: Subprocess not terminated, missing timeout

**Solution**:

```bash
# Use aggressive timeouts
pytest tests/meta_delegation/e2e/ --timeout=60

# Check for orphaned processes
ps aux | grep python
kill -9 <PID>

# Enable subprocess cleanup debugging
pytest tests/meta_delegation/e2e/ -v --log-cli-level=DEBUG
```

### Cleanup Failures

**Symptom**: `ResourceWarning: subprocess still running`

**Cause**: SubprocessLifecycleManager not used or failed

**Solution**:

```python
# Always use lifecycle manager fixture
def test_example(subprocess_lifecycle_manager):
    proc = subprocess_lifecycle_manager.spawn(...)
    # Manager cleans up automatically

# Or use context manager
with SubprocessLifecycleManager() as manager:
    proc = manager.spawn(...)
# Cleanup on exit
```

### Workspace Collisions

**Symptom**: Tests interfere with each other

**Cause**: Shared workspace directory

**Solution**:

```python
# Use test_workspace fixture (isolated per test)
def test_example(test_workspace):
    # Each test gets unique directory
    test_workspace.write_file("test.txt", "data")
```

### Timeout Too Short

**Symptom**: `SubprocessTimeoutError` on valid operations

**Cause**: Operation legitimately takes longer than timeout

**Solution**:

```python
# Increase timeout for specific test
@pytest.mark.timeout(120)
def test_slow_operation(test_workspace):
    adapter = CLISubprocessAdapter(timeout=120)
    # Long-running operation
```

### CI vs Local Differences

**Symptom**: Tests pass locally, fail in CI

**Cause**: Different timeout settings, resource constraints

**Solution**:

```python
# Test with CI settings locally
export CI=true
pytest tests/meta_delegation/e2e/ -v

# Or adjust CI timeouts in conftest.py
if os.getenv("CI"):
    DEFAULT_TIMEOUT = 30
else:
    DEFAULT_TIMEOUT = 60
```

## Adding New Tests

### Step 1: Choose Layer

Determine which layer to extend:

- **Layer 1**: Testing subprocess spawn/cleanup mechanics
- **Layer 2**: Testing error/timeout handling
- **Layer 3**: Testing complete workflows

### Step 2: Create Test

```python
# [PLANNED] - Example test template
import pytest
from amplihack.meta_delegation import CLISubprocessAdapter

@pytest.mark.e2e
@pytest.mark.subprocess
def test_new_subprocess_feature(test_workspace, subprocess_lifecycle_manager):
    """Test description following convention: test_<what>_<condition>."""
    # Arrange
    adapter = CLISubprocessAdapter(timeout=30)
    test_workspace.write_file("input.txt", "test data")

    # Act
    result = adapter.spawn(
        command=["python", "process.py"],
        working_dir=test_workspace.path
    )

    # Assert
    assert result.exit_code == 0
    assert test_workspace.read_file("output.txt") == "expected"
```

### Step 3: Add Markers

Mark tests appropriately:

```python
@pytest.mark.e2e              # Required: Marks as E2E test
@pytest.mark.subprocess       # If spawns subprocesses
@pytest.mark.slow             # If takes >10 seconds
@pytest.mark.timeout(120)     # Custom timeout if needed
```

### Step 4: Update Counts

Update test counts in this README:

- Add to appropriate table
- Update total counts
- Document new test purpose

## CI/CD Integration

### GitHub Actions Configuration

```yaml
# [PLANNED] - Example CI configuration
- name: Run E2E Tests
  run: |
    pytest tests/meta_delegation/e2e/ \
      -v \
      --timeout=300 \
      --junitxml=test-results/e2e-results.xml \
      --cov=amplihack.meta_delegation \
      --cov-report=xml
  timeout-minutes: 10
  env:
    CI: true
```

### Test Artifacts

E2E tests generate artifacts for debugging:

- `test-results/e2e-results.xml` - JUnit test results
- `coverage.xml` - Coverage report
- `e2e-workspaces/` - Failed test workspaces (if `--keep-workspaces`)

## Performance Expectations

| Test Layer              | Test Count | Duration     | Subprocess Count |
| ----------------------- | ---------- | ------------ | ---------------- |
| Layer 1 (Subprocess)    | ~12        | 30-60s       | 12-20            |
| Layer 2 (Error)         | ~10        | 20-40s       | 10-15            |
| Layer 3 (Orchestration) | ~8         | 60-120s      | 24-40            |
| **Total**               | **~30**    | **110-220s** | **46-75**        |

**Note**: Times are for local development. CI runs faster with parallel execution.

## Best Practices

### DO

- ✅ Use `test_workspace` fixture for isolation
- ✅ Use `subprocess_lifecycle_manager` for cleanup
- ✅ Set reasonable timeouts (30-60s)
- ✅ Capture and assert on stdout/stderr
- ✅ Test both success and failure paths
- ✅ Mark slow tests with `@pytest.mark.slow`

### DON'T

- ❌ Spawn subprocesses without lifecycle manager
- ❌ Use shared working directories
- ❌ Skip timeout configuration
- ❌ Ignore cleanup in teardown
- ❌ Test without marking `@pytest.mark.e2e`
- ❌ Create tests that depend on external services

## References

- **Parent Suite**: `tests/meta_delegation/README.md`
- **Architecture**: Issue #2030 - Meta-Agentic Task Delegation
- **Subprocess Adapter**: `src/amplihack/meta_delegation/subprocess_adapter.py`
- **Lifecycle Manager**: `src/amplihack/meta_delegation/subprocess_lifecycle.py`

---

**Version**: 1.0.0
**Created**: 2026-02-15
**Status**: [PLANNED] - Retcon documentation for implementation guidance
**Maintainer**: Meta-Delegation Team
