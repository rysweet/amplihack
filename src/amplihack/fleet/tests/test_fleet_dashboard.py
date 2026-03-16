"""Tests for fleet_dashboard — project tracking and fleet metrics.

Testing pyramid:
- 60% Unit: ProjectInfo serialization, completion_rate, name inference
- 30% Integration: FleetDashboard.update_from_queue, persistence roundtrip
- 10% E2E: summary() output format
"""

from __future__ import annotations

from datetime import datetime

import pytest

from amplihack.fleet.fleet_dashboard import FleetDashboard, ProjectInfo
from amplihack.fleet.fleet_tasks import TaskQueue
from amplihack.utils.logging_utils import log_call

# ────────────────────────────────────────────
# UNIT TESTS (60%) — ProjectInfo
# ────────────────────────────────────────────


class TestProjectInfo:
    """Unit tests for ProjectInfo dataclass and serialization."""

    @log_call
    def test_name_inferred_from_url(self):
        proj = ProjectInfo(repo_url="https://github.com/org/my-project")
        assert proj.name == "my-project"

    @log_call
    def test_name_inferred_strips_trailing_slash(self):
        proj = ProjectInfo(repo_url="https://github.com/org/repo/")
        assert proj.name == "repo"

    @log_call
    def test_explicit_name_not_overridden(self):
        proj = ProjectInfo(repo_url="https://github.com/org/repo", name="custom")
        assert proj.name == "custom"

    @log_call
    def test_empty_url_empty_name(self):
        proj = ProjectInfo(repo_url="")
        assert proj.name == ""

    @log_call
    def test_completion_rate_zero_tasks(self):
        proj = ProjectInfo(repo_url="u", tasks_total=0)
        assert proj.completion_rate == 0.0

    @log_call
    def test_completion_rate_some_completed(self):
        proj = ProjectInfo(repo_url="u", tasks_total=10, tasks_completed=3)
        assert proj.completion_rate == pytest.approx(0.3)

    @log_call
    def test_completion_rate_all_completed(self):
        proj = ProjectInfo(repo_url="u", tasks_total=5, tasks_completed=5)
        assert proj.completion_rate == pytest.approx(1.0)

    @log_call
    def test_to_dict_roundtrip(self):
        now = datetime(2025, 6, 15, 12, 0, 0)
        proj = ProjectInfo(
            repo_url="https://github.com/org/repo",
            name="repo",
            github_identity="user1",
            vms=["vm-01", "vm-02"],
            tasks_total=10,
            tasks_completed=7,
            tasks_failed=1,
            tasks_in_progress=2,
            prs_created=["https://github.com/org/repo/pull/1"],
            estimated_cost_usd=12.50,
            started_at=now,
            last_activity=now,
        )
        d = proj.to_dict()
        restored = ProjectInfo.from_dict(d)

        assert restored.repo_url == proj.repo_url
        assert restored.name == proj.name
        assert restored.github_identity == proj.github_identity
        assert restored.vms == proj.vms
        assert restored.tasks_total == proj.tasks_total
        assert restored.tasks_completed == proj.tasks_completed
        assert restored.tasks_failed == proj.tasks_failed
        assert restored.tasks_in_progress == proj.tasks_in_progress
        assert restored.prs_created == proj.prs_created
        assert restored.estimated_cost_usd == pytest.approx(12.50)
        assert restored.started_at == now
        assert restored.last_activity == now

    @log_call
    def test_from_dict_missing_optional_dates(self):
        d = {"repo_url": "https://github.com/org/r", "name": "r"}
        proj = ProjectInfo.from_dict(d)
        assert proj.started_at is None
        assert proj.last_activity is None

    @log_call
    def test_to_dict_none_dates(self):
        proj = ProjectInfo(repo_url="u")
        d = proj.to_dict()
        assert d["started_at"] is None
        assert d["last_activity"] is None


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — FleetDashboard
# ────────────────────────────────────────────


class TestFleetDashboardUpdateFromQueue:
    """Integration: update_from_queue syncs task stats."""

    @log_call
    def test_update_creates_project_for_new_repo(self):
        dashboard = FleetDashboard()
        queue = TaskQueue()
        task = queue.add_task(
            prompt="Fix bug",
            repo_url="https://github.com/org/repo",
        )
        task.start()

        dashboard.update_from_queue(queue)

        assert len(dashboard.projects) == 1
        proj = dashboard.projects[0]
        assert proj.repo_url == "https://github.com/org/repo"
        assert proj.tasks_total == 1

    @log_call
    def test_update_counts_by_status(self):
        dashboard = FleetDashboard()
        queue = TaskQueue()

        t1 = queue.add_task(prompt="A", repo_url="https://github.com/org/repo")
        t1.complete(pr_url="https://github.com/org/repo/pull/1")

        t2 = queue.add_task(prompt="B", repo_url="https://github.com/org/repo")
        t2.fail("broken")

        t3 = queue.add_task(prompt="C", repo_url="https://github.com/org/repo")
        t3.assign("vm-01", "sess-1")

        dashboard.update_from_queue(queue)

        proj = dashboard.projects[0]
        assert proj.tasks_total == 3
        assert proj.tasks_completed == 1
        assert proj.tasks_failed == 1
        assert proj.tasks_in_progress == 1
        assert proj.prs_created == ["https://github.com/org/repo/pull/1"]
        assert "vm-01" in proj.vms

    @log_call
    def test_update_ignores_unassigned_repo(self):
        dashboard = FleetDashboard()
        queue = TaskQueue()
        queue.add_task(prompt="No repo")  # repo_url=""

        dashboard.update_from_queue(queue)
        # "unassigned" tasks don't create projects
        assert len(dashboard.projects) == 0

    @log_call
    def test_persistence_roundtrip(self, tmp_path):
        path = tmp_path / "dashboard.json"
        dashboard = FleetDashboard(persist_path=path)
        dashboard.add_project(
            repo_url="https://github.com/org/repo",
            github_identity="user1",
        )

        # Load into new dashboard
        dashboard2 = FleetDashboard(persist_path=path)
        assert len(dashboard2.projects) == 1
        assert dashboard2.projects[0].repo_url == "https://github.com/org/repo"
        assert dashboard2.projects[0].github_identity == "user1"

    @log_call
    def test_get_project_by_name_and_url(self):
        dashboard = FleetDashboard()
        dashboard.add_project(repo_url="https://github.com/org/alpha", name="alpha")

        assert dashboard.get_project("alpha") is not None
        assert dashboard.get_project("https://github.com/org/alpha") is not None
        assert dashboard.get_project("nonexistent") is None


# ────────────────────────────────────────────
# E2E TESTS (10%) — summary
# ────────────────────────────────────────────


class TestFleetDashboardSummary:
    """E2E test: summary produces readable output."""

    @log_call
    def test_summary_format(self):
        dashboard = FleetDashboard()
        proj = dashboard.add_project(
            repo_url="https://github.com/org/repo",
            github_identity="user1",
        )
        proj.tasks_total = 4
        proj.tasks_completed = 2
        proj.tasks_failed = 1
        proj.vms = ["vm-01"]
        proj.prs_created = ["pr-url"]
        proj.estimated_cost_usd = 5.25

        text = dashboard.summary()
        assert "FLEET DASHBOARD" in text
        assert "Projects: 1" in text
        assert "2/4 completed" in text
        assert "PRs created: 1" in text
        assert "$5.25" in text
        assert "1 failed tasks" in text
        assert "(user1)" in text

    @log_call
    def test_summary_empty_dashboard(self):
        dashboard = FleetDashboard()
        text = dashboard.summary()
        assert "FLEET DASHBOARD" in text
        assert "Projects: 0" in text


# ────────────────────────────────────────────
# Additional coverage: fleet_dashboard.py (78% -> target 80%+)
# ────────────────────────────────────────────


class TestFleetDashboardUpdateFromState:
    """Tests for update_from_state cost calculation."""

    @log_call
    def test_update_cost_for_running_vms(self):
        """Cost should be calculated based on hours active."""
        from amplihack.fleet.fleet_state import FleetState, VMInfo

        dashboard = FleetDashboard()
        proj = dashboard.add_project(repo_url="https://github.com/org/repo")
        proj.vms = ["vm-1"]
        proj.started_at = datetime(2025, 6, 15, 12, 0, 0)

        state = FleetState()
        state.vms = [
            VMInfo(name="vm-1", session_name="vm-1", status="Running"),
        ]

        dashboard.update_from_state(state)

        # Should have a cost > 0 since vm-1 is running
        assert proj.estimated_cost_usd > 0.0

    @log_call
    def test_update_cost_for_stopped_vms(self):
        """Stopped VMs should not contribute to cost."""
        from amplihack.fleet.fleet_state import FleetState, VMInfo

        dashboard = FleetDashboard()
        proj = dashboard.add_project(repo_url="https://github.com/org/repo")
        proj.vms = ["vm-1"]
        proj.started_at = datetime.now()

        state = FleetState()
        state.vms = [
            VMInfo(name="vm-1", session_name="vm-1", status="Stopped"),
        ]

        dashboard.update_from_state(state)

        assert proj.estimated_cost_usd == 0.0

    @log_call
    def test_update_cost_no_started_at(self):
        """Without started_at, default to 1 hour."""
        from amplihack.fleet.fleet_dashboard import DEFAULT_COST_PER_HOUR
        from amplihack.fleet.fleet_state import FleetState, VMInfo

        dashboard = FleetDashboard()
        proj = dashboard.add_project(repo_url="https://github.com/org/repo")
        proj.vms = ["vm-1"]
        proj.started_at = None

        state = FleetState()
        state.vms = [
            VMInfo(name="vm-1", session_name="vm-1", status="Running"),
        ]

        dashboard.update_from_state(state)

        assert proj.estimated_cost_usd == round(DEFAULT_COST_PER_HOUR, 2)

    @log_call
    def test_update_cost_vm_not_in_state(self):
        """VMs not found in state should not contribute cost."""
        from amplihack.fleet.fleet_state import FleetState

        dashboard = FleetDashboard()
        proj = dashboard.add_project(repo_url="https://github.com/org/repo")
        proj.vms = ["nonexistent-vm"]

        state = FleetState()
        state.vms = []

        dashboard.update_from_state(state)

        assert proj.estimated_cost_usd == 0.0


class TestFleetDashboardPersistence:
    """Additional persistence tests."""

    @log_call
    def test_load_corrupt_file(self, tmp_path):
        """Corrupt JSON file should not crash, creates backup."""
        path = tmp_path / "dashboard.json"
        path.write_text("not valid json{{{")

        dashboard = FleetDashboard(persist_path=path)
        assert dashboard.projects == []
        # Backup file should exist
        backup = path.with_suffix(".json.bak")
        assert backup.exists()

    @log_call
    def test_load_valid_data(self, tmp_path):
        """Valid JSON with proper dict entries loads correctly."""
        path = tmp_path / "dashboard.json"
        path.write_text('[{"repo_url": "https://github.com/org/repo", "name": "repo"}]')

        dashboard = FleetDashboard(persist_path=path)
        assert len(dashboard.projects) == 1
        assert dashboard.projects[0].repo_url == "https://github.com/org/repo"

    @log_call
    def test_add_project_duplicate_returns_existing(self):
        """Adding duplicate project returns the existing one."""
        dashboard = FleetDashboard()
        proj1 = dashboard.add_project(repo_url="https://github.com/org/repo")
        proj2 = dashboard.add_project(repo_url="https://github.com/org/repo")
        assert proj1 is proj2
        assert len(dashboard.projects) == 1

    @log_call
    def test_remove_project_success(self):
        """Remove existing project returns True."""
        dashboard = FleetDashboard()
        dashboard.add_project(repo_url="https://github.com/org/repo")
        assert dashboard.remove_project("repo") is True
        assert len(dashboard.projects) == 0

    @log_call
    def test_remove_project_not_found(self):
        """Remove nonexistent project returns False."""
        dashboard = FleetDashboard()
        assert dashboard.remove_project("nonexistent") is False


class TestFleetDashboardProgressBar:
    """Tests for _progress_bar helper."""

    @log_call
    def test_progress_bar_zero(self):
        dashboard = FleetDashboard()
        bar = dashboard._progress_bar(0.0)
        assert "0%" in bar
        assert bar.startswith("[")

    @log_call
    def test_progress_bar_half(self):
        dashboard = FleetDashboard()
        bar = dashboard._progress_bar(0.5)
        assert "50%" in bar

    @log_call
    def test_progress_bar_full(self):
        dashboard = FleetDashboard()
        bar = dashboard._progress_bar(1.0)
        assert "100%" in bar

    @log_call
    def test_progress_bar_custom_width(self):
        dashboard = FleetDashboard()
        bar = dashboard._progress_bar(0.5, width=10)
        # 5 filled + 5 empty = 10 chars inside brackets
        assert len(bar.split("]")[0].split("[")[1]) == 10
