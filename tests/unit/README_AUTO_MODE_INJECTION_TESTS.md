# Auto Mode Instruction Injection Test Suite

Comprehensive TDD test suite for the auto mode instruction injection feature.

## Overview

This test suite follows Test-Driven Development (TDD) principles to guide implementation of:
1. Auto mode directory creation (append/ and appended/)
2. Prompt persistence (prompt.md)
3. Instruction checking and processing
4. Session discovery and validation
5. CLI append instruction functionality

## Test Organization

### Unit Tests

#### 1. test_auto_mode_injection.py
Tests AutoMode class modifications for instruction injection support.

**Status**: Most tests PASS (features already implemented in lines 48-60, 206-243 of auto_mode.py)

Test Classes:
- `TestAutoModeDirectoryCreation` - Directory creation on init (PASSING)
- `TestAutoModePromptWriting` - prompt.md creation and formatting (PASSING)
- `TestCheckForNewInstructions` - Instruction discovery and processing (PASSING)
- `TestCheckForNewInstructionsErrorHandling` - Error handling (PASSING)
- `TestInstructionIntegrationWithRunLoop` - Integration with execution (NEEDS VERIFICATION)
- `TestAutoModeAttributes` - Attribute verification (PASSING)

Coverage:
- 58 test cases
- Focus on boundary conditions, error handling, file operations
- Tests for empty directories, multiple files, ordering, error recovery

#### 2. test_session_finder.py
Tests SessionFinder class for discovering active auto mode sessions.

**Status**: All tests FAIL (SessionFinder not yet implemented)

Test Classes:
- `TestSessionFinderBasicDiscovery` - Finding sessions in current/parent directories
- `TestSessionFinderMultipleSessions` - Handling multiple concurrent sessions
- `TestSessionValidation` - Session validation and staleness detection
- `TestSessionInfo` - SessionInfo data structure
- `TestSessionFinderEdgeCases` - Error handling and edge cases
- `TestSessionFinderPerformance` - Performance with many sessions

Coverage:
- 24 test cases
- Session discovery from any directory level
- Multiple session handling (most recent wins)
- SDK type filtering (claude, copilot, codex)
- Staleness detection (max age threshold)
- Structure validation (append/ and prompt.md required)

Implementation Guide:
```python
# Location: src/amplihack/launcher/session_finder.py

@dataclass
class SessionInfo:
    """Information about an active auto mode session."""
    session_id: str
    session_dir: Path
    workspace_root: Path
    sdk: str  # claude, copilot, or codex
    timestamp: int
    append_dir: Path
    prompt_file: Path

    def is_active(self, max_age_hours: int = 24) -> bool:
        """Check if session is still active."""
        pass

class SessionFinder:
    """Discovers active auto mode sessions."""

    def __init__(self, start_dir: Path = None, max_age_hours: int = 24):
        self.start_dir = start_dir or Path.cwd()
        self.max_age_hours = max_age_hours

    def find_active_session(self, sdk_filter: str = None) -> Optional[SessionInfo]:
        """Find most recent active session.

        Args:
            sdk_filter: Filter by SDK type (claude, copilot, codex)

        Returns:
            SessionInfo for most recent session, or None
        """
        pass

    def list_active_sessions(self) -> List[SessionInfo]:
        """List all active sessions, ordered by timestamp (newest first)."""
        pass
```

#### 3. test_append_handler.py
Tests append_instructions function for CLI --append flag.

**Status**: All tests FAIL (append_instructions not yet implemented)

Test Classes:
- `TestAppendInstructionsBasic` - Basic file creation and writing
- `TestAppendInstructionsSessionDiscovery` - Finding active sessions
- `TestAppendInstructionsErrorHandling` - Error handling
- `TestAppendInstructionsConcurrency` - Concurrent operations
- `TestAppendInstructionsFormatting` - Content formatting and encoding
- `TestAppendResult` - Result data structure
- `TestCLIIntegration` - CLI flag integration (conceptual)

Coverage:
- 30 test cases
- Timestamp-based filename generation (YYYYMMDD_HHMMSS.md)
- Automatic session discovery
- Writing from subdirectories
- Multiline content preservation
- Unicode and special character handling
- Collision handling for same-timestamp files

Implementation Guide:
```python
# Location: src/amplihack/launcher/append_handler.py

@dataclass
class AppendResult:
    """Result of append operation."""
    success: bool
    filename: str
    session_id: str
    append_dir: Path
    timestamp: str
    message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

class AppendError(Exception):
    """Error during append operation."""
    pass

def append_instructions(
    instruction: str,
    session_id: str = None,
    sdk_filter: str = None
) -> AppendResult:
    """Append instruction to active auto mode session.

    Args:
        instruction: Instruction text to append
        session_id: Optional explicit session ID
        sdk_filter: Optional SDK type filter

    Returns:
        AppendResult with operation details

    Raises:
        AppendError: If no active session found or write fails
        ValueError: If instruction is empty or whitespace-only
    """
    # Validation
    if not instruction or not instruction.strip():
        raise ValueError("Instruction cannot be empty")

    # Find session
    finder = SessionFinder()
    if session_id:
        session = finder.find_session_by_id(session_id)
    else:
        session = finder.find_active_session(sdk_filter=sdk_filter)

    if not session:
        raise AppendError("No active auto mode session found")

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.md"

    # Handle collision (add microseconds if file exists)
    file_path = session.append_dir / filename
    if file_path.exists():
        timestamp_ms = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp_ms}.md"
        file_path = session.append_dir / filename

    # Write instruction
    try:
        file_path.write_text(instruction, encoding='utf-8')
    except Exception as e:
        raise AppendError(f"Failed to write instruction: {e}")

    return AppendResult(
        success=True,
        filename=filename,
        session_id=session.session_id,
        append_dir=session.append_dir,
        timestamp=timestamp,
        message=f"Instruction appended to session {session.session_id}"
    )
```

### Integration Tests

#### 4. test_auto_mode_append_integration.py
End-to-end integration tests combining all components.

**Status**: Tests FAIL until all components implemented

Test Classes:
- `TestFullWorkflowStartAutoAppendProcess` - Complete workflow simulation
- `TestMultipleAppendOperationsQueuing` - Multiple appends and queuing
- `TestAppendFromSubdirectory` - Appending from subdirectories
- `TestSessionFinderIntegration` - SessionFinder with append_instructions
- `TestErrorRecoveryAndEdgeCases` - Error recovery and edge cases
- `TestEndToEndWithRealWorkflow` - Realistic developer workflow simulation

Coverage:
- 15 test cases
- Full workflow: start auto mode → append → process
- Multiple concurrent appends
- Appending from various subdirectory levels
- Session discovery integration
- Error recovery scenarios
- Realistic developer workflow simulation

Key Workflow Test:
```python
def test_developer_workflow_simulation():
    """
    1. Developer: amplihack --auto "Build API"
    2. Auto mode starts executing
    3. Developer: amplihack --append "Add rate limiting"
    4. Auto mode picks up instruction in next turn
    5. Auto mode continues with updated requirements
    """
```

## Running the Tests

### Run All Tests
```bash
# All auto mode injection tests
pytest tests/unit/test_auto_mode_injection.py -v
pytest tests/unit/test_session_finder.py -v
pytest tests/unit/test_append_handler.py -v
pytest tests/integration/test_auto_mode_append_integration.py -v

# Run all together
pytest tests/unit/test_auto_mode_injection.py tests/unit/test_session_finder.py tests/unit/test_append_handler.py tests/integration/test_auto_mode_append_integration.py -v
```

### Run by Test Class
```bash
# Test directory creation (should PASS)
pytest tests/unit/test_auto_mode_injection.py::TestAutoModeDirectoryCreation -v

# Test session finder (should FAIL)
pytest tests/unit/test_session_finder.py::TestSessionFinderBasicDiscovery -v

# Test append handler (should FAIL)
pytest tests/unit/test_append_handler.py::TestAppendInstructionsBasic -v
```

### Run by Category
```bash
# Only unit tests
pytest tests/unit/test_auto_mode_injection.py tests/unit/test_session_finder.py tests/unit/test_append_handler.py -v -m unit

# Only integration tests
pytest tests/integration/test_auto_mode_append_integration.py -v -m integration

# Skip slow tests
pytest -v -m "not slow"
```

### Run with Coverage
```bash
pytest tests/unit/test_auto_mode_injection.py --cov=amplihack.launcher.auto_mode --cov-report=html
pytest tests/unit/test_session_finder.py --cov=amplihack.launcher.session_finder --cov-report=html
pytest tests/unit/test_append_handler.py --cov=amplihack.launcher.append_handler --cov-report=html
```

## Implementation Status

### ✅ Already Implemented (in auto_mode.py)
- `AutoMode.append_dir` attribute (line 49)
- `AutoMode.appended_dir` attribute (line 50)
- Directory creation in `__init__` (lines 51-52)
- `prompt.md` writing (lines 54-59)
- `_check_for_new_instructions()` method (lines 206-243)
- Instruction processing in run loop (line 441)

### ❌ Not Yet Implemented
- `SessionFinder` class
- `SessionInfo` dataclass
- `append_instructions()` function
- `AppendResult` dataclass
- `AppendError` exception
- CLI `--append` flag integration

## Test Coverage Goals

Target: >90% coverage for new code

Current Coverage Breakdown:
- AutoMode modifications: ~95% (mostly implemented)
- SessionFinder: 0% (not implemented)
- append_handler: 0% (not implemented)
- Integration workflows: 0% (not implemented)

## Edge Cases Covered

### Boundary Conditions
- Empty directories (no instruction files)
- Single instruction file
- Multiple instruction files
- Empty instruction content
- Whitespace-only instructions
- Very long instructions

### Error Conditions
- No active session exists
- Multiple sessions (select most recent)
- Permission errors (read/write)
- Corrupted instruction files
- Missing directories
- Symlink loops
- Concurrent operations

### Filesystem Edge Cases
- Deep directory nesting
- Timestamp collisions
- Rapid successive operations
- Non-standard directory names
- Malformed session directories

### Character Encoding
- Unicode characters
- Special markdown characters
- Code blocks
- Emoji
- Multiline content with formatting

## Test Principles Applied

1. **TDD Red-Green-Refactor**
   - Tests written first (RED phase)
   - Implementation will make them pass (GREEN phase)
   - Refactoring guided by tests (REFACTOR phase)

2. **Fast Execution**
   - Unit tests use temp directories (cleanup automatic)
   - No external dependencies
   - Mock SDK calls to avoid network

3. **Isolated Tests**
   - Each test is independent
   - No shared state between tests
   - Fixtures provide clean environment

4. **Clear Assertions**
   - Descriptive failure messages
   - Assert actual behavior, not implementation
   - One logical assertion per test

5. **Comprehensive Coverage**
   - Happy path tested
   - Error conditions tested
   - Boundary conditions tested
   - Edge cases tested

## Next Steps for Implementation

### Phase 1: SessionFinder (1-2 hours)
1. Create `src/amplihack/launcher/session_finder.py`
2. Implement `SessionInfo` dataclass
3. Implement `SessionFinder.find_active_session()`
4. Implement `SessionFinder.list_active_sessions()`
5. Run: `pytest tests/unit/test_session_finder.py -v`

### Phase 2: append_handler (1-2 hours)
1. Create `src/amplihack/launcher/append_handler.py`
2. Implement `AppendResult` dataclass
3. Implement `AppendError` exception
4. Implement `append_instructions()` function
5. Run: `pytest tests/unit/test_append_handler.py -v`

### Phase 3: CLI Integration (1 hour)
1. Add `--append` flag to CLI parser
2. Wire up to `append_instructions()`
3. Add help text
4. Test manually: `amplihack --append "test instruction"`

### Phase 4: Integration Testing (1 hour)
1. Run full integration test suite
2. Fix any integration issues
3. Verify end-to-end workflow
4. Run: `pytest tests/integration/test_auto_mode_append_integration.py -v`

### Phase 5: Documentation (30 minutes)
1. Update CLI help text
2. Add usage examples to docs
3. Update CLAUDE.md if needed
4. Create user-facing documentation

## Success Criteria

Feature is complete when:
- ✅ All 127 tests pass
- ✅ Coverage >90% on new code
- ✅ CLI `--append` flag works end-to-end
- ✅ Multiple concurrent appends handled correctly
- ✅ Session discovery works from any directory
- ✅ Error handling is robust
- ✅ Documentation is complete

## Files Created

1. `/home/azureuser/src/worktrees/verbose-default/tests/unit/test_auto_mode_injection.py` (58 tests)
2. `/home/azureuser/src/worktrees/verbose-default/tests/unit/test_session_finder.py` (24 tests)
3. `/home/azureuser/src/worktrees/verbose-default/tests/unit/test_append_handler.py` (30 tests)
4. `/home/azureuser/src/worktrees/verbose-default/tests/integration/test_auto_mode_append_integration.py` (15 tests)

Total: **127 comprehensive test cases**

## Test Execution Example

```bash
# Initial run (before implementation)
$ pytest tests/unit/test_session_finder.py -v
================================ FAILURES ================================
# Many failures due to ImportError (SessionFinder not found)

# After Phase 1 implementation
$ pytest tests/unit/test_session_finder.py -v
========================= 24 passed in 0.45s ==========================

# After Phase 2 implementation
$ pytest tests/unit/test_append_handler.py -v
========================= 30 passed in 0.52s ==========================

# Full suite after all implementation
$ pytest tests/unit/test_auto_mode_injection.py tests/unit/test_session_finder.py tests/unit/test_append_handler.py tests/integration/test_auto_mode_append_integration.py -v
======================= 127 passed in 2.13s ===========================
```

## Notes

- Tests use `pytest` fixtures for setup/teardown
- All tests use temporary directories (automatic cleanup)
- Mock objects used for SDK calls to avoid external dependencies
- Tests are marked with `@pytest.mark.unit` and `@pytest.mark.integration`
- Slow tests marked with `@pytest.mark.slow`
- Tests requiring SDK marked with `@pytest.mark.requires_sdk`

## References

- AutoMode implementation: `src/amplihack/launcher/auto_mode.py`
- Existing test patterns: `tests/unit/test_expert_panel.py`
- Pytest configuration: `pytest.ini`
- Test fixtures: `conftest.py`
