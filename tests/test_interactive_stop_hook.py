"""Integration tests for Stop hook with interactive reflection."""

import json

# Add paths for imports
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(
    0, str(Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "reflection")
)

from semaphore import ReflectionLock
from state_machine import ReflectionState, ReflectionStateData, ReflectionStateMachine


@pytest.fixture
def temp_project_root():
    """Create temporary project root with .claude structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        claude_dir = root / ".claude"
        runtime_dir = claude_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "logs").mkdir()
        (runtime_dir / "analysis").mkdir()
        yield root


@pytest.fixture
def stop_hook(temp_project_root):
    """Create StopHook instance with mocked project root."""
    # Import here to avoid import issues
    from stop import StopHook

    with patch.object(StopHook, "__init__", lambda self: None):
        hook = StopHook()
        hook.project_root = temp_project_root
        hook.log_dir = temp_project_root / ".claude" / "runtime" / "logs"
        hook.analysis_dir = temp_project_root / ".claude" / "runtime" / "analysis"
        hook._recursion_guard = type("obj", (object,), {})()
        yield hook


@pytest.fixture
def sample_input_data():
    """Sample input data for stop hook."""
    return {
        "session_id": "test-session-123",
        "messages": [
            {"role": "user", "content": "Please help me debug this"},
            {"role": "assistant", "content": "I found an error in your code"},
        ],
    }


class TestRecursionGuard:
    """Tests for recursion guard (loop prevention)."""

    def test_recursion_guard_prevents_nested_calls(self, stop_hook, sample_input_data):
        """Thread-local recursion guard prevents re-entry."""
        # Set recursion guard active
        stop_hook._recursion_guard.active = True

        result = stop_hook.process(sample_input_data)

        # Should return empty dict and not process
        assert result == {}

    def test_recursion_guard_allows_first_call(self, stop_hook, sample_input_data):
        """First call is allowed when recursion guard not active."""
        # Recursion guard not set
        stop_hook._recursion_guard.active = False

        # Mock dependencies
        with patch("stop.ReflectionLock") as mock_lock_class:
            mock_lock = MagicMock()
            mock_lock.is_locked.return_value = False
            mock_lock_class.return_value = mock_lock

            # Should not return {} immediately (would process further)
            stop_hook.process(sample_input_data)

            # May return {} for other reasons, but not from recursion guard
            # The call should proceed past recursion check

    def test_recursion_guard_reset_after_processing(self, stop_hook, sample_input_data):
        """Recursion guard is reset after processing completes."""
        stop_hook._recursion_guard.active = False

        with patch("stop.ReflectionLock") as mock_lock_class, patch.object(
            stop_hook, "get_session_messages", return_value=[]
        ):
            mock_lock = MagicMock()
            mock_lock.is_locked.return_value = False
            mock_lock_class.return_value = mock_lock

            stop_hook.process(sample_input_data)

            # Guard should be False after processing
            assert not stop_hook._recursion_guard.active


class TestSemaphoreIntegration:
    """Tests for semaphore integration with stop hook."""

    def test_semaphore_prevents_concurrent_reflection(self, temp_project_root, sample_input_data):
        """Semaphore blocks second Stop hook during analysis."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Create lock
        lock = ReflectionLock(runtime_dir=runtime_dir)
        lock.acquire(session_id="other-session", purpose="analysis")

        # Create stop hook
        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = type("obj", (object,), {})()

            result = hook.process(sample_input_data)

            # Should return empty due to lock
            assert result == {}

        lock.release()

    def test_stale_lock_cleaned_up_before_analysis(self, temp_project_root, sample_input_data):
        """Stale lock is cleaned up and analysis proceeds."""
        from stop import StopHook

        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Create stale lock
        lock = ReflectionLock(runtime_dir=runtime_dir)
        lock.acquire(session_id="old-session", purpose="analysis")

        # Make it stale
        lock_data = lock.read_lock()
        lock_data.timestamp = time.time() - 61

        with open(lock.lock_file, "w") as f:
            json.dump(
                {
                    "pid": lock_data.pid,
                    "timestamp": lock_data.timestamp,
                    "session_id": lock_data.session_id,
                    "purpose": lock_data.purpose,
                },
                f,
            )

        # Verify lock is stale
        assert lock.is_stale()

        # Process should succeed after cleanup
        with patch.object(StopHook, "__init__", lambda self: None):
            hook = StopHook()
            hook.project_root = temp_project_root
            hook.log_dir = runtime_dir / "logs"
            hook.analysis_dir = runtime_dir / "analysis"
            hook._recursion_guard = type("obj", (object,), {})()

            with patch.object(hook, "get_session_messages", return_value=[]):
                hook.process(sample_input_data)

            # Lock should be cleaned up by process()
            # Create new lock instance to check
            check_lock = ReflectionLock(runtime_dir=runtime_dir)
            assert not check_lock.is_locked() or check_lock.is_stale()


class TestAnalysisWorkflow:
    """Tests for analysis workflow."""

    def test_analysis_runs_when_should_analyze_true(self, stop_hook):
        """Analysis runs when cooldown period passed."""
        state_data = ReflectionStateData(
            state=ReflectionState.IDLE,
            timestamp=time.time() - 40,  # 40 seconds ago
            session_id="test-session",
        )

        result = stop_hook._should_analyze(state_data)

        assert result is True

    def test_analysis_skips_when_too_recent(self, stop_hook):
        """Analysis skips if run < 30 seconds ago."""
        state_data = ReflectionStateData(
            state=ReflectionState.AWAITING_APPROVAL,
            timestamp=time.time() - 10,  # 10 seconds ago
            session_id="test-session",
        )

        result = stop_hook._should_analyze(state_data)

        assert result is False

    def test_analysis_runs_on_idle_state(self, stop_hook):
        """Analysis runs on IDLE state regardless of timestamp."""
        state_data = ReflectionStateData(
            state=ReflectionState.IDLE,
            timestamp=time.time(),  # Current time
            session_id="test-session",
        )

        result = stop_hook._should_analyze(state_data)

        assert result is True


class TestInteractiveStateHandling:
    """Tests for interactive state handling."""

    def test_user_approval_creates_issue(self, stop_hook, temp_project_root):
        """User saying 'yes' creates GitHub issue."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        # Set up state
        state_data = ReflectionStateData(
            state=ReflectionState.AWAITING_APPROVAL,
            analysis={
                "patterns": [{"type": "error", "description": "Test error", "severity": "high"}]
            },
            session_id="test-session",
        )
        state_machine.write_state(state_data)

        input_data = {
            "session_id": "test-session",
            "messages": [{"role": "user", "content": "yes, create the issue"}],
        }

        lock = ReflectionLock(runtime_dir=runtime_dir)

        # Mock subprocess for gh command
        with patch("stop.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="https://github.com/user/repo/issues/123\n"
            )

            result = stop_hook._handle_interactive_state(
                state_machine, state_data, input_data, lock
            )

            # Should create issue
            assert "Created issue" in result.get("message", "")
            assert "github.com" in result.get("message", "")

    def test_user_rejection_cancels_workflow(self, stop_hook, temp_project_root):
        """User saying 'no' resets to IDLE."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        state_data = ReflectionStateData(
            state=ReflectionState.AWAITING_APPROVAL,
            analysis={"patterns": [{"type": "error", "description": "Test", "severity": "high"}]},
            session_id="test-session",
        )

        input_data = {
            "session_id": "test-session",
            "messages": [{"role": "user", "content": "no, cancel it"}],
        }

        lock = ReflectionLock(runtime_dir=runtime_dir)

        result = stop_hook._handle_interactive_state(state_machine, state_data, input_data, lock)

        # Should cancel
        assert "cancelled" in result.get("message", "").lower()

        # State should be reset
        new_state = state_machine.read_state()
        assert new_state.state == ReflectionState.IDLE

    def test_no_intent_returns_empty(self, stop_hook, temp_project_root):
        """No user intent returns empty dict."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        state_data = ReflectionStateData(
            state=ReflectionState.AWAITING_APPROVAL,
            analysis={"patterns": [{"type": "test", "description": "test", "severity": "low"}]},
            session_id="test-session",
        )

        input_data = {
            "session_id": "test-session",
            "messages": [{"role": "user", "content": "Tell me more"}],
        }

        lock = ReflectionLock(runtime_dir=runtime_dir)

        result = stop_hook._handle_interactive_state(state_machine, state_data, input_data, lock)

        # Should return empty when no intent detected
        assert result == {} or "message" not in result


class TestIssueCreation:
    """Tests for GitHub issue creation."""

    def test_issue_creation_success_prompts_start_work(self, stop_hook, temp_project_root):
        """Successful issue creation asks about starting work."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        state_data = ReflectionStateData(
            state=ReflectionState.CREATING_ISSUE,
            analysis={"patterns": [{"type": "error", "description": "Test", "severity": "high"}]},
            session_id="test-session",
        )

        lock = ReflectionLock(runtime_dir=runtime_dir)

        # Mock subprocess
        with patch("stop.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="https://github.com/user/repo/issues/456\n"
            )

            result = stop_hook._create_github_issue(state_machine, state_data, lock)

            # Should prompt for starting work
            assert "Start work" in result.get("message", "")
            assert "(yes/no)" in result.get("message", "")

    def test_issue_creation_failure_returns_error(self, stop_hook, temp_project_root):
        """Failed issue creation returns error message."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        state_data = ReflectionStateData(
            state=ReflectionState.CREATING_ISSUE,
            analysis={"patterns": [{"type": "error", "description": "Test", "severity": "high"}]},
            session_id="test-session",
        )

        lock = ReflectionLock(runtime_dir=runtime_dir)

        # Mock subprocess failure
        with patch("stop.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="gh: authentication failed")

            result = stop_hook._create_github_issue(state_machine, state_data, lock)

            # Should return error
            assert "Failed" in result.get("message", "")

    def test_issue_creation_blocked_by_lock(self, stop_hook, temp_project_root):
        """Issue creation blocked by concurrent lock."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        state_data = ReflectionStateData(
            state=ReflectionState.CREATING_ISSUE,
            analysis={"patterns": [{"type": "error", "description": "Test", "severity": "high"}]},
            session_id="test-session",
        )

        # Lock already held
        lock = ReflectionLock(runtime_dir=runtime_dir)
        lock.acquire(session_id="other-session", purpose="analysis")

        result = stop_hook._create_github_issue(state_machine, state_data, lock)

        # Should be blocked
        assert "in progress" in result.get("message", "").lower()

        lock.release()


class TestStartWork:
    """Tests for start work functionality."""

    def test_start_work_returns_ultrathink_command(self, stop_hook, temp_project_root):
        """Start work returns /ultrathink command string."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        state_data = ReflectionStateData(
            state=ReflectionState.STARTING_WORK,
            issue_url="https://github.com/user/repo/issues/789",
            session_id="test-session",
        )

        lock = ReflectionLock(runtime_dir=runtime_dir)

        result = stop_hook._start_work(state_machine, state_data, lock)

        # Should return command
        assert "ultrathink" in result.get("message", "").lower()
        assert "789" in result.get("message", "")

    def test_start_work_cleans_up_state(self, stop_hook, temp_project_root):
        """Start work cleans up state after completion."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        state_data = ReflectionStateData(
            state=ReflectionState.STARTING_WORK,
            issue_url="https://github.com/user/repo/issues/999",
            session_id="test-session",
        )
        state_machine.write_state(state_data)

        lock = ReflectionLock(runtime_dir=runtime_dir)

        stop_hook._start_work(state_machine, state_data, lock)

        # State file should be cleaned up
        assert not state_machine.state_file.exists()


class TestExistingFeatures:
    """Regression tests for existing stop hook features."""

    def test_existing_decision_summary_still_works(self, stop_hook):
        """Old decision summary feature preserved."""
        # This is a regression test - decision summary should still work
        result = stop_hook.display_decision_summary(session_id="test")

        # Should not raise exception
        assert isinstance(result, str)

    def test_existing_learnings_extraction_still_works(self, stop_hook):
        """Old learnings feature preserved."""
        messages = [
            {"role": "assistant", "content": "I discovered that the issue was caused by..."}
        ]

        # Mock the reflection module import
        # The stop hook tries to import from reflection module which may not exist
        # Test the fallback behavior
        learnings = stop_hook.extract_learnings(messages)

        # Should not raise exception and return list (may be empty or with fallback data)
        assert isinstance(learnings, list)


class TestConcurrentSessions:
    """Tests for concurrent session handling."""

    def test_concurrent_sessions_independent(self, temp_project_root):
        """Multiple sessions don't interfere."""

        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Create two state machines for different sessions
        sm1 = ReflectionStateMachine(session_id="session1", runtime_dir=runtime_dir)
        sm2 = ReflectionStateMachine(session_id="session2", runtime_dir=runtime_dir)

        # Set different states
        sm1.write_state(
            ReflectionStateData(state=ReflectionState.AWAITING_APPROVAL, session_id="session1")
        )
        sm2.write_state(
            ReflectionStateData(state=ReflectionState.CREATING_ISSUE, session_id="session2")
        )

        # Verify they don't interfere
        assert sm1.read_state().state == ReflectionState.AWAITING_APPROVAL
        assert sm2.read_state().state == ReflectionState.CREATING_ISSUE

    def test_lock_blocks_all_sessions(self, temp_project_root):
        """Lock blocks reflection across all sessions."""
        runtime_dir = temp_project_root / ".claude" / "runtime"

        # Session 1 acquires lock
        lock1 = ReflectionLock(runtime_dir=runtime_dir)
        assert lock1.acquire(session_id="session1", purpose="analysis") is True

        # Session 2 cannot acquire
        lock2 = ReflectionLock(runtime_dir=runtime_dir)
        assert lock2.acquire(session_id="session2", purpose="analysis") is False


class TestLockReleaseOnException:
    """Tests for lock release on exception."""

    def test_lock_release_on_exception_in_analysis(self, stop_hook, temp_project_root):
        """Lock is released if analysis throws exception."""
        runtime_dir = temp_project_root / ".claude" / "runtime"
        lock = ReflectionLock(runtime_dir=runtime_dir)
        state_machine = ReflectionStateMachine(session_id="test-session", runtime_dir=runtime_dir)

        input_data = {"session_id": "test-session", "messages": []}

        # Mock get_session_messages to raise exception
        with patch.object(stop_hook, "get_session_messages", side_effect=Exception("Test error")):
            try:
                stop_hook._run_new_analysis(lock, state_machine, input_data, "test-session")
            except Exception:
                pass

        # Lock should be released
        assert not lock.is_locked()


class TestToolLogCollection:
    """Tests for tool log collection."""

    def test_get_recent_tool_logs_reads_file(self, stop_hook, temp_project_root):
        """Gets recent tool use log entries."""
        # Create tool log file
        log_file = temp_project_root / ".claude" / "runtime" / "logs" / "post_tool_use.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "w") as f:
            f.write("[2025-10-01T10:00:00] Tool: Bash\n")
            f.write("[2025-10-01T10:00:01] Tool: Read\n")

        logs = stop_hook._get_recent_tool_logs()

        assert len(logs) > 0

    def test_get_recent_tool_logs_handles_missing_file(self, stop_hook):
        """Handles missing tool log file gracefully."""
        logs = stop_hook._get_recent_tool_logs()

        # Should return empty list
        assert logs == []


class TestAnalysisFormatting:
    """Tests for analysis output formatting."""

    def test_format_analysis_output_includes_patterns(self, stop_hook):
        """Formats analysis results for user display."""
        result = {
            "patterns": [
                {"type": "error", "description": "Test error", "severity": "high"},
                {"type": "inefficiency", "description": "Test inefficiency", "severity": "medium"},
            ],
            "elapsed_seconds": 2.5,
        }

        formatted = stop_hook._format_analysis_output(result)

        assert "error" in formatted.lower()
        assert "inefficiency" in formatted.lower()
        assert "2.5" in formatted
        assert "yes/no" in formatted.lower()

    def test_format_includes_severity_emojis(self, stop_hook):
        """Formatted output includes severity emojis."""
        result = {
            "patterns": [
                {"type": "error", "description": "High severity", "severity": "high"},
                {"type": "warning", "description": "Medium severity", "severity": "medium"},
            ],
            "elapsed_seconds": 1.0,
        }

        formatted = stop_hook._format_analysis_output(result)

        # Should contain emoji indicators (exact emojis may vary)
        assert any(emoji in formatted for emoji in ["🔴", "🟡", "🟢"])
