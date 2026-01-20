"""Unit tests for data models - AgentStatus, OrchestrationReport, etc.

Tests the model bricks that represent orchestration state and results.

Philosophy: Test serialization, validation, and state transitions.
"""

import pytest
import json
from datetime import datetime, timedelta


class TestAgentStatus:
    """Unit tests for AgentStatus model."""

    def test_create_agent_status(self):
        """Test creating agent status with required fields."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        status = AgentStatus(
            agent_id="agent-101",
            issue_number=101,
            status="pending"
        )

        assert status.agent_id == "agent-101"
        assert status.issue_number == 101
        assert status.status == "pending"

    @pytest.mark.parametrize("status_value", [
        "pending",
        "in_progress",
        "completed",
        "failed",
        "timeout",
    ])
    def test_valid_status_values(self, status_value):
        """Test that all valid status values are accepted."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        status = AgentStatus(
            agent_id="agent-101",
            issue_number=101,
            status=status_value
        )

        assert status.status == status_value

    def test_invalid_status_value(self):
        """Test that invalid status values are rejected."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        with pytest.raises(ValueError, match="status"):
            AgentStatus(
                agent_id="agent-101",
                issue_number=101,
                status="invalid_status"
            )

    def test_agent_status_serialization(self):
        """Test serialization to JSON."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        status = AgentStatus(
            agent_id="agent-101",
            issue_number=101,
            status="in_progress",
            completion_percentage=45
        )

        json_str = status.to_json()
        data = json.loads(json_str)

        assert data["agent_id"] == "agent-101"
        assert data["status"] == "in_progress"
        assert data["completion_percentage"] == 45

    def test_agent_status_deserialization(self):
        """Test deserialization from JSON."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        json_data = {
            "agent_id": "agent-101",
            "issue_number": 101,
            "status": "completed",
            "pr_number": 1801
        }

        status = AgentStatus.from_dict(json_data)

        assert status.agent_id == "agent-101"
        assert status.status == "completed"
        assert status.pr_number == 1801

    def test_agent_status_with_timestamps(self):
        """Test status includes start and update timestamps."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        now = datetime.now()
        status = AgentStatus(
            agent_id="agent-101",
            issue_number=101,
            status="in_progress",
            start_time=now.isoformat(),
            last_update=now.isoformat()
        )

        assert status.start_time is not None
        assert status.last_update is not None

    def test_agent_status_with_errors(self):
        """Test status can track error messages."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        errors = [
            "ImportError: module not found",
            "Test failed: assertion error"
        ]

        status = AgentStatus(
            agent_id="agent-101",
            issue_number=101,
            status="failed",
            errors=errors
        )

        assert len(status.errors) == 2
        assert "ImportError" in status.errors[0]

    def test_agent_status_completion_percentage(self):
        """Test completion percentage validation."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        # Valid percentages
        for pct in [0, 50, 100]:
            status = AgentStatus(
                agent_id="agent-101",
                issue_number=101,
                status="in_progress",
                completion_percentage=pct
            )
            assert status.completion_percentage == pct

        # Invalid percentage
        with pytest.raises(ValueError, match="percentage"):
            AgentStatus(
                agent_id="agent-101",
                issue_number=101,
                status="in_progress",
                completion_percentage=150
            )

    def test_agent_status_update(self):
        """Test updating agent status."""
        from parallel_task_orchestrator.models.agent_status import AgentStatus

        status = AgentStatus(
            agent_id="agent-101",
            issue_number=101,
            status="pending"
        )

        # Update to in_progress
        updated = status.update(status="in_progress", completion_percentage=25)

        assert updated.status == "in_progress"
        assert updated.completion_percentage == 25


class TestOrchestrationReport:
    """Unit tests for OrchestrationReport model."""

    def test_create_report(self):
        """Test creating orchestration report."""
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=5,
            completed=4,
            failed=1,
            duration_seconds=3600
        )

        assert report.parent_issue == 1783
        assert report.total_sub_issues == 5
        assert report.completed == 4
        assert report.failed == 1

    def test_calculate_success_rate(self):
        """Test calculation of success rate."""
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=10,
            completed=8,
            failed=2
        )

        success_rate = report.calculate_success_rate()

        assert success_rate == 80.0

    def test_report_serialization(self):
        """Test report serialization to JSON."""
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=5,
            completed=5,
            failed=0
        )

        json_str = report.to_json()
        data = json.loads(json_str)

        assert data["parent_issue"] == 1783
        assert data["completed"] == 5

    def test_report_includes_pr_links(self):
        """Test report includes PR URLs."""
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        pr_links = [
            "https://github.com/owner/repo/pull/1801",
            "https://github.com/owner/repo/pull/1802",
        ]

        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=2,
            completed=2,
            failed=0,
            pr_links=pr_links
        )

        assert len(report.pr_links) == 2
        assert all("github.com" in link for link in report.pr_links)

    def test_report_includes_failure_details(self):
        """Test report includes details about failures."""
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        failures = [
            {
                "issue_number": 103,
                "error": "Timeout after 2 hours",
                "status": "timeout"
            }
        ]

        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=3,
            completed=2,
            failed=1,
            failures=failures
        )

        assert len(report.failures) == 1
        assert report.failures[0]["issue_number"] == 103

    def test_report_duration_formatting(self):
        """Test formatting of orchestration duration."""
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=5,
            completed=5,
            failed=0,
            duration_seconds=7325  # 2h 2m 5s
        )

        formatted = report.format_duration()

        assert "2" in formatted  # Hours
        assert "hour" in formatted.lower() or "h" in formatted

    def test_report_summary_text(self):
        """Test generation of human-readable summary."""
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=10,
            completed=8,
            failed=2,
            duration_seconds=3600
        )

        summary = report.generate_summary()

        assert "8" in summary
        assert "10" in summary
        assert "1783" in summary


class TestErrorDetails:
    """Unit tests for ErrorDetails model."""

    def test_create_error_details(self):
        """Test creating error details."""
        from parallel_task_orchestrator.models.completion import ErrorDetails

        error = ErrorDetails(
            issue_number=103,
            error_type="ImportError",
            message="Module not found",
            recoverable=True
        )

        assert error.issue_number == 103
        assert error.error_type == "ImportError"
        assert error.recoverable is True

    def test_error_with_traceback(self):
        """Test error details with traceback."""
        from parallel_task_orchestrator.models.completion import ErrorDetails

        traceback = "File 'module.py', line 10\n  import missing_module"

        error = ErrorDetails(
            issue_number=103,
            error_type="ImportError",
            message="Module not found",
            traceback=traceback
        )

        assert error.traceback is not None
        assert "module.py" in error.traceback

    def test_error_suggested_fix(self):
        """Test error includes suggested fix."""
        from parallel_task_orchestrator.models.completion import ErrorDetails

        error = ErrorDetails(
            issue_number=103,
            error_type="ImportError",
            message="Module not found",
            suggested_fix="Install missing dependency: pip install module"
        )

        assert error.suggested_fix is not None
        assert "pip install" in error.suggested_fix
