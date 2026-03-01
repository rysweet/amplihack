"""Tests for fleet_results — structured task outcome tracking.

Testing pyramid:
- 60% Unit: TaskResult serialization, is_success, ResultCollector queries
- 30% Integration: persistence roundtrip (record, save/load index)
- 10% E2E: summary output
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from amplihack.fleet.fleet_results import ResultCollector, TaskResult


# ────────────────────────────────────────────
# UNIT TESTS (60%) — TaskResult
# ────────────────────────────────────────────


class TestTaskResult:
    def test_is_success_true(self):
        r = TaskResult(task_id="t1", status="success")
        assert r.is_success is True

    def test_is_success_false(self):
        r = TaskResult(task_id="t1", status="failure")
        assert r.is_success is False

    def test_is_success_partial(self):
        r = TaskResult(task_id="t1", status="partial")
        assert r.is_success is False

    def test_to_dict_all_fields(self):
        now = datetime(2025, 6, 15, 12, 0, 0)
        r = TaskResult(
            task_id="task-123",
            status="success",
            pr_url="https://github.com/org/repo/pull/1",
            pr_number=1,
            commit_shas=["abc123"],
            tests_passed=True,
            tests_summary="All pass",
            error_summary="",
            agent_log_tail="Done.",
            vm_name="vm-01",
            session_name="sess-1",
            repo_url="https://github.com/org/repo",
            branch="feat/x",
            started_at=now,
            completed_at=now,
            duration_seconds=120.5,
        )
        d = r.to_dict()
        assert d["task_id"] == "task-123"
        assert d["status"] == "success"
        assert d["pr_number"] == 1
        assert d["commit_shas"] == ["abc123"]
        assert d["tests_passed"] is True
        assert d["started_at"] == "2025-06-15T12:00:00"
        assert d["duration_seconds"] == 120.5

    def test_from_dict_roundtrip(self):
        now = datetime(2025, 6, 15, 12, 0, 0)
        original = TaskResult(
            task_id="t1",
            status="failure",
            pr_url="pr-url",
            pr_number=42,
            commit_shas=["sha1", "sha2"],
            tests_passed=False,
            tests_summary="3 failed",
            error_summary="import error",
            agent_log_tail="last line",
            vm_name="vm-02",
            session_name="sess-2",
            repo_url="repo-url",
            branch="fix/bug",
            started_at=now,
            completed_at=now,
            duration_seconds=55.0,
        )
        restored = TaskResult.from_dict(original.to_dict())
        assert restored.task_id == original.task_id
        assert restored.status == original.status
        assert restored.pr_number == original.pr_number
        assert restored.commit_shas == original.commit_shas
        assert restored.tests_passed == original.tests_passed
        assert restored.started_at == now
        assert restored.completed_at == now
        assert restored.duration_seconds == 55.0

    def test_from_dict_missing_optional_dates(self):
        d = {"task_id": "t1", "status": "success"}
        r = TaskResult.from_dict(d)
        assert r.started_at is None
        assert r.completed_at is None

    def test_to_dict_none_dates(self):
        r = TaskResult(task_id="t1", status="success")
        d = r.to_dict()
        assert d["started_at"] is None
        assert d["completed_at"] is None


class TestResultCollectorQueries:
    """Unit tests for ResultCollector query methods."""

    def test_success_rate_empty(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        assert collector.success_rate() == 0.0

    def test_success_rate_mixed(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        collector.record(TaskResult(task_id="t1", status="success"))
        collector.record(TaskResult(task_id="t2", status="failure"))
        collector.record(TaskResult(task_id="t3", status="success"))
        assert collector.success_rate() == pytest.approx(2 / 3)

    def test_by_vm(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        collector.record(TaskResult(task_id="t1", status="success", vm_name="vm-01"))
        collector.record(TaskResult(task_id="t2", status="success", vm_name="vm-02"))
        collector.record(TaskResult(task_id="t3", status="failure", vm_name="vm-01"))

        vm01 = collector.by_vm("vm-01")
        assert len(vm01) == 2
        assert all(r.vm_name == "vm-01" for r in vm01)

    def test_by_repo(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        collector.record(TaskResult(task_id="t1", status="success", repo_url="repo-a"))
        collector.record(TaskResult(task_id="t2", status="success", repo_url="repo-b"))

        repo_a = collector.by_repo("repo-a")
        assert len(repo_a) == 1

    def test_recent_ordering(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        r1 = TaskResult(task_id="old", status="success", completed_at=datetime(2025, 1, 1))
        r2 = TaskResult(task_id="new", status="success", completed_at=datetime(2025, 6, 1))
        collector.record(r1)
        collector.record(r2)

        recent = collector.recent(limit=1)
        assert len(recent) == 1
        assert recent[0].task_id == "new"

    def test_get_by_id(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        collector.record(TaskResult(task_id="find-me", status="success"))
        assert collector.get("find-me") is not None
        assert collector.get("not-here") is None


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — persistence
# ────────────────────────────────────────────


class TestResultCollectorPersistence:
    def test_record_creates_individual_file(self, tmp_path):
        results_dir = tmp_path / "results"
        collector = ResultCollector(results_dir=results_dir)
        collector.record(TaskResult(task_id="t1", status="success"))

        individual = results_dir / "t1.json"
        assert individual.exists()
        data = json.loads(individual.read_text())
        assert data["task_id"] == "t1"

    def test_index_roundtrip(self, tmp_path):
        results_dir = tmp_path / "results"
        c1 = ResultCollector(results_dir=results_dir)
        c1.record(TaskResult(task_id="a", status="success", vm_name="vm-01"))
        c1.record(TaskResult(task_id="b", status="failure", vm_name="vm-02"))

        # New collector loads from index
        c2 = ResultCollector(results_dir=results_dir)
        assert c2.get("a") is not None
        assert c2.get("a").status == "success"
        assert c2.get("b") is not None
        assert c2.get("b").status == "failure"

    def test_corrupt_index_resets(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir(parents=True)
        index = results_dir / "index.json"
        index.write_text("not valid json{{{")

        collector = ResultCollector(results_dir=results_dir)
        assert collector.success_rate() == 0.0


# ────────────────────────────────────────────
# E2E TESTS (10%) — summary
# ────────────────────────────────────────────


class TestResultCollectorSummary:
    def test_summary_empty(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        text = collector.summary()
        assert "No results recorded yet" in text

    def test_summary_with_data(self, tmp_path):
        collector = ResultCollector(results_dir=tmp_path / "results")
        collector.record(TaskResult(
            task_id="t1",
            status="success",
            pr_url="https://github.com/org/repo/pull/1",
            completed_at=datetime(2025, 6, 1),
        ))
        collector.record(TaskResult(
            task_id="t2",
            status="failure",
            completed_at=datetime(2025, 6, 2),
        ))

        text = collector.summary()
        assert "2 tasks" in text
        assert "Success: 1 (50%)" in text
        assert "Failure: 1" in text
        assert "PRs created: 1" in text
