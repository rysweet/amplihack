"""Tests for fleet observer — agent state detection via pattern matching.

All unit tests — no external dependencies (subprocess mocked).
"""

import time
from unittest.mock import MagicMock, patch

from amplihack.fleet.fleet_observer import (
    FleetObserver,
)
from amplihack.fleet.fleet_state import AgentStatus, TmuxSessionInfo


class TestFleetObserverClassification:
    """Unit tests for output classification logic."""

    def _make_observer(self):
        observer = FleetObserver()
        observer.stuck_threshold_seconds = 1.0  # Speed up tests
        return observer

    def _classify(self, observer, lines, vm="vm-1", session="sess-1"):
        """Helper to call _classify_output directly."""
        return observer._classify_output(lines, vm, session)

    def test_detect_completion_pr_created(self):
        observer = self._make_observer()
        lines = [
            "Step 22: Creating pull request",
            "PR #42 created: https://github.com/org/repo/pull/42",
        ]
        status, conf, pattern = self._classify(observer, lines)
        assert status == AgentStatus.COMPLETED
        assert conf >= 0.8

    def test_detect_completion_goal_achieved(self):
        observer = self._make_observer()
        lines = ["GOAL_STATUS: ACHIEVED", "Summary: All tasks completed"]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.COMPLETED

    def test_detect_completion_workflow_complete(self):
        observer = self._make_observer()
        lines = ["Workflow Complete", "22/22 steps executed"]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.COMPLETED

    def test_detect_error_traceback(self):
        observer = self._make_observer()
        lines = [
            "File /home/user/code.py, line 42",
            "Traceback (most recent call last):",
            "ValueError: invalid input",
        ]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.ERROR
        assert conf >= 0.8

    def test_detect_error_goal_not_achieved(self):
        observer = self._make_observer()
        lines = ["GOAL_STATUS: NOT_ACHIEVED", "Failed to complete task"]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.ERROR

    def test_detect_error_authentication_failed(self):
        observer = self._make_observer()
        lines = ["Authentication failed", "Please check credentials"]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.ERROR

    def test_detect_waiting_input_question(self):
        """Generic questions no longer trigger WAITING_INPUT (L5: narrowed patterns)."""
        observer = self._make_observer()
        lines = ["Which approach do you prefer?"]
        status, conf, _ = self._classify(observer, lines)
        # After L5 fix, a bare question mark is not enough to classify as waiting
        assert status != AgentStatus.WAITING_INPUT

    def test_detect_waiting_input_yn(self):
        observer = self._make_observer()
        lines = ["Continue with this approach? [Y/n]"]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.WAITING_INPUT

    def test_detect_idle_shell_prompt(self):
        observer = self._make_observer()
        lines = ["azureuser@fleet-exp-1:~/code$ "]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.IDLE

    def test_detect_running_step(self):
        observer = self._make_observer()
        lines = ["Step 5: Implementing authentication module", "Reading file auth.py"]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.RUNNING

    def test_detect_running_building(self):
        observer = self._make_observer()
        lines = ["Building the API endpoint for user registration"]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.RUNNING

    def test_detect_stuck_no_change(self):
        observer = self._make_observer()
        observer.stuck_threshold_seconds = 0.1

        lines = ["Some static output that never changes"]
        # First call: set baseline
        observer._classify_output(lines, "vm-1", "sess-1")
        # Wait past threshold
        time.sleep(0.2)
        # Second call: same output
        status, conf, _ = observer._classify_output(lines, "vm-1", "sess-1")
        assert status == AgentStatus.STUCK

    def test_unknown_for_empty_output(self):
        observer = self._make_observer()
        status, conf, _ = self._classify(observer, [])
        assert status == AgentStatus.UNKNOWN
        assert conf == 0.0

    def test_running_default_for_substantial_output(self):
        observer = self._make_observer()
        lines = ["x" * 100]  # Substantial but no recognized pattern
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.RUNNING
        assert conf <= 0.6  # Lower confidence for default

    def test_priority_completion_over_error(self):
        """Completion patterns should take priority."""
        observer = self._make_observer()
        lines = [
            "ERROR: minor issue",  # Error in history
            "All 22 steps completed",  # But completed
            "PR #1 created",
        ]
        status, conf, _ = self._classify(observer, lines)
        assert status == AgentStatus.COMPLETED


class TestFleetObserverIntegration:
    """Integration tests with mocked subprocess."""

    @patch("amplihack.fleet.fleet_observer.subprocess.run")
    def test_observe_session_captures_pane(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Step 5: Building feature\nReading file main.py\n",
        )

        observer = FleetObserver()
        result = observer.observe_session("vm-1", "test-session")

        assert result.status == AgentStatus.RUNNING
        assert result.vm_name == "vm-1"
        assert result.session_name == "test-session"
        assert result.observed_at is not None

    @patch("amplihack.fleet.fleet_observer.subprocess.run")
    def test_observe_session_handles_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        observer = FleetObserver()
        result = observer.observe_session("vm-1", "test-session")

        assert result.status == AgentStatus.UNKNOWN
        assert result.confidence == 0.0

    @patch("amplihack.fleet.fleet_observer.subprocess.run")
    def test_observe_all(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="GOAL_STATUS: ACHIEVED\n",
        )

        observer = FleetObserver()
        sessions = [
            TmuxSessionInfo(session_name="sess-1", vm_name="vm-1"),
            TmuxSessionInfo(session_name="sess-2", vm_name="vm-1"),
        ]

        results = observer.observe_all(sessions)
        assert len(results) == 2
        assert all(r.status == AgentStatus.COMPLETED for r in results)


class TestCapturePaneValidation:
    """Tests for _capture_pane input handling."""

    def test_capture_pane_rejects_empty_session(self):
        """_capture_pane returns None for empty session names."""
        observer = FleetObserver()
        result = observer._capture_pane("vm-1", "")
        assert result is None

    def test_capture_pane_accepts_parenthesized_names(self):
        """_capture_pane accepts names like (none) from tmux — shlex.quote handles safety."""
        observer = FleetObserver()
        # Will fail to connect but should not raise ValueError
        result = observer._capture_pane("vm-1", "(none)")
        # Returns None because azlin isn't available, but no ValueError raised
        assert result is None
