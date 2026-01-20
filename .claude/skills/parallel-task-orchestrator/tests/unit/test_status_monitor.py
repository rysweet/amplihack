"""Unit tests for StatusMonitor - agent status tracking and polling.

Tests the StatusMonitor brick that polls agent status files and detects completion/failures.

Philosophy: Fast unit tests with mocked file system operations.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, mock_open


class TestStatusMonitor:
    """Unit tests for agent status monitoring."""

    def test_read_status_file_success(self, temp_dir, sample_agent_status):
        """Test successful reading of agent status file."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        # Create status file
        status_file = temp_dir / ".agent_status.json"
        status_file.write_text(json.dumps(sample_agent_status))

        monitor = StatusMonitor()
        result = monitor.read_status_file(status_file)

        assert result["agent_id"] == "agent-101"
        assert result["status"] == "in_progress"
        assert result["completion_percentage"] == 45

    def test_read_status_file_not_found(self, temp_dir):
        """Test handling of missing status file."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor()
        result = monitor.read_status_file(temp_dir / "nonexistent.json")

        # Should return None or default status
        assert result is None or result["status"] == "unknown"

    def test_read_status_file_invalid_json(self, temp_dir):
        """Test handling of corrupted status file."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        status_file = temp_dir / ".agent_status.json"
        status_file.write_text("{ invalid json }")

        monitor = StatusMonitor()

        with pytest.raises(ValueError, match="Invalid JSON"):
            monitor.read_status_file(status_file)

    def test_poll_agent_statuses(self, mock_worktree_structure):
        """Test polling multiple agent status files."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor(worktree_base=mock_worktree_structure)
        statuses = monitor.poll_all_agents()

        # Should find all 3 agent status files
        assert len(statuses) == 3
        assert all(s["status"] == "pending" for s in statuses)

    def test_detect_completed_agents(self, sample_agent_statuses):
        """Test detection of completed agents."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor()
        completed = monitor.filter_by_status(sample_agent_statuses, "completed")

        assert len(completed) == 1
        assert completed[0]["issue_number"] == 101

    def test_detect_failed_agents(self, sample_agent_statuses):
        """Test detection of failed agents."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor()
        failed = monitor.filter_by_status(sample_agent_statuses, "failed")

        assert len(failed) == 1
        assert failed[0]["issue_number"] == 103
        assert len(failed[0]["errors"]) > 0

    def test_detect_in_progress_agents(self, sample_agent_statuses):
        """Test detection of in-progress agents."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor()
        in_progress = monitor.filter_by_status(sample_agent_statuses, "in_progress")

        assert len(in_progress) == 1
        assert in_progress[0]["issue_number"] == 102

    def test_detect_timeout(self):
        """Test detection of agent timeout based on last_update timestamp."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        old_time = (datetime.now() - timedelta(hours=3)).isoformat()
        status = {
            "agent_id": "agent-101",
            "status": "in_progress",
            "last_update": old_time,
        }

        monitor = StatusMonitor(timeout_minutes=120)
        is_timeout = monitor.is_timed_out(status)

        assert is_timeout is True

    def test_no_timeout_for_recent_update(self):
        """Test that recent updates don't trigger timeout."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        recent_time = (datetime.now() - timedelta(minutes=30)).isoformat()
        status = {
            "agent_id": "agent-102",
            "status": "in_progress",
            "last_update": recent_time,
        }

        monitor = StatusMonitor(timeout_minutes=120)
        is_timeout = monitor.is_timed_out(status)

        assert is_timeout is False

    def test_calculate_overall_progress(self, sample_agent_statuses):
        """Test calculation of overall orchestration progress."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor()
        progress = monitor.calculate_overall_progress(sample_agent_statuses)

        # 1 completed, 1 in_progress (60%), 1 failed
        # Overall should be reasonable average
        assert 0 <= progress <= 100
        assert isinstance(progress, (int, float))

    def test_all_agents_completed(self):
        """Test detection when all agents have completed."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        all_done = [
            {"agent_id": f"agent-{i}", "status": "completed"}
            for i in range(3)
        ]

        monitor = StatusMonitor()
        assert monitor.all_completed(all_done) is True

    def test_not_all_agents_completed(self, sample_agent_statuses):
        """Test detection when some agents still in progress."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor()
        assert monitor.all_completed(sample_agent_statuses) is False

    def test_wait_for_completion_with_timeout(self, mock_worktree_structure):
        """Test waiting for all agents with timeout."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor(
            worktree_base=mock_worktree_structure,
            status_poll_interval=1  # Fast polling for test
        )

        # Should timeout if agents never complete
        with pytest.raises(TimeoutError):
            monitor.wait_for_completion(timeout_seconds=3)

    @patch("time.sleep")
    def test_poll_interval_respected(self, mock_sleep, mock_worktree_structure):
        """Test that status poll interval is respected."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor(
            worktree_base=mock_worktree_structure,
            status_poll_interval=30
        )

        # Mock completion after 2 polls
        with patch.object(monitor, "all_completed", side_effect=[False, True]):
            monitor.wait_for_completion(timeout_seconds=100)

        # Should have slept with correct interval
        mock_sleep.assert_called_with(30)

    def test_status_change_detection(self):
        """Test detection of status changes between polls."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        old_status = [
            {"agent_id": "agent-101", "status": "in_progress"},
            {"agent_id": "agent-102", "status": "in_progress"},
        ]

        new_status = [
            {"agent_id": "agent-101", "status": "completed"},
            {"agent_id": "agent-102", "status": "in_progress"},
        ]

        monitor = StatusMonitor()
        changes = monitor.detect_changes(old_status, new_status)

        assert len(changes) == 1
        assert changes[0]["agent_id"] == "agent-101"
        assert changes[0]["old_status"] == "in_progress"
        assert changes[0]["new_status"] == "completed"

    def test_get_agent_log_path(self, mock_worktree_structure):
        """Test retrieval of agent log file path."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor(worktree_base=mock_worktree_structure)
        log_path = monitor.get_agent_log_path("agent-101")

        assert log_path is not None
        assert "agent-101" in str(log_path)

    def test_extract_error_details_from_status(self, sample_agent_statuses):
        """Test extraction of error details from failed agent status."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        monitor = StatusMonitor()
        failed_agent = sample_agent_statuses[2]  # The failed one

        errors = monitor.extract_errors(failed_agent)

        assert len(errors) > 0
        assert "Import error" in errors[0]

    def test_health_check_all_healthy(self):
        """Test health check when all agents are progressing normally."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        healthy_statuses = [
            {
                "agent_id": f"agent-{i}",
                "status": "in_progress",
                "last_update": datetime.now().isoformat(),
            }
            for i in range(3)
        ]

        monitor = StatusMonitor()
        health = monitor.health_check(healthy_statuses)

        assert health["overall"] == "healthy"
        assert health["issues"] == []

    def test_health_check_with_stalled_agents(self):
        """Test health check detection of stalled agents."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        statuses = [
            {
                "agent_id": "agent-101",
                "status": "in_progress",
                "last_update": old_time,  # Stalled
            }
        ]

        monitor = StatusMonitor(timeout_minutes=60)
        health = monitor.health_check(statuses)

        assert health["overall"] == "degraded"
        assert len(health["issues"]) > 0
        assert "stalled" in health["issues"][0].lower() or "timeout" in health["issues"][0].lower()
