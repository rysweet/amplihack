"""Tests for fleet_dashboard — project tracking and fleet metrics.

Testing pyramid:
- 60% Unit: ProjectInfo serialization, completion_rate, name inference
- 30% Integration: FleetDashboard.update_from_queue, persistence roundtrip
- 10% E2E: summary() output format
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from amplihack.fleet.fleet_dashboard import FleetDashboard, ProjectInfo
from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus


# ────────────────────────────────────────────
# UNIT TESTS (60%) — ProjectInfo
# ────────────────────────────────────────────


class TestProjectInfo:
    """Unit tests for ProjectInfo dataclass and serialization."""

    def test_name_inferred_from_url(self):
        proj = ProjectInfo(repo_url="https://github.com/org/my-project")
        assert proj.name == "my-project"

    def test_name_inferred_strips_trailing_slash(self):
        proj = ProjectInfo(repo_url="https://github.com/org/repo/")
        assert proj.name == "repo"

    def test_explicit_name_not_overridden(self):
        proj = ProjectInfo(repo_url="https://github.com/org/repo", name="custom")
        assert proj.name == "custom"

    def test_empty_url_empty_name(self):
        proj = ProjectInfo(repo_url="")
        assert proj.name == ""

    def test_completion_rate_zero_tasks(self):
        proj = ProjectInfo(repo_url="u", tasks_total=0)
        assert proj.completion_rate == 0.0

    def test_completion_rate_some_completed(self):
        proj = ProjectInfo(repo_url="u", tasks_total=10, tasks_completed=3)
        assert proj.completion_rate == pytest.approx(0.3)

    def test_completion_rate_all_completed(self):
        proj = ProjectInfo(repo_url="u", tasks_total=5, tasks_completed=5)
        assert proj.completion_rate == pytest.approx(1.0)

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

    def test_from_dict_missing_optional_dates(self):
        d = {"repo_url": "https://github.com/org/r", "name": "r"}
        proj = ProjectInfo.from_dict(d)
        assert proj.started_at is None
        assert proj.last_activity is None

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

    def test_update_ignores_unassigned_repo(self):
        dashboard = FleetDashboard()
        queue = TaskQueue()
        queue.add_task(prompt="No repo")  # repo_url=""

        dashboard.update_from_queue(queue)
        # "unassigned" tasks don't create projects
        assert len(dashboard.projects) == 0

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

    def test_summary_empty_dashboard(self):
        dashboard = FleetDashboard()
        text = dashboard.summary()
        assert "FLEET DASHBOARD" in text
        assert "Projects: 0" in text
