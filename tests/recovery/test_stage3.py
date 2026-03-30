"""Tests for the Stage 3 five-part quality audit execution."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest


def _require_attr(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    assert hasattr(module, attr_name), f"{module_name} must define {attr_name}"
    return getattr(module, attr_name)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_pytest_repo(repo_path: Path) -> None:
    _git(repo_path, "init")
    _git(repo_path, "config", "user.email", "tests@example.com")
    _git(repo_path, "config", "user.name", "Recovery Tests")
    (repo_path / "tests").mkdir()
    (repo_path / "pytest.ini").write_text("[pytest]\n")
    (repo_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    _git(repo_path, "add", "pytest.ini", "tests/test_ok.py")
    _git(repo_path, "commit", "-m", "initial")


def _make_worktree(repo_path: Path, worktree_path: Path) -> None:
    _git(repo_path, "worktree", "add", str(worktree_path), "HEAD")


def _make_stage2_result():
    Stage2Result = _require_attr("amplihack.recovery.models", "Stage2Result")
    return Stage2Result(
        status="completed",
        baseline_collection_errors=1,
        final_collection_errors=0,
        delta_verdict="reduced",
        signatures=[],
        clusters=[],
        applied_fixes=[],
        diagnostics=[],
        blockers=[],
    )


class TestStage3AuditExecution:
    """Recovery must expose the documented five-part audit behavior."""

    def test_recovery_audit_phases_match_the_reference(self):
        phases = _require_attr("amplihack.recovery.stage3", "RECOVERY_AUDIT_PHASES")

        assert phases == [
            "scope/setup",
            "SEEK",
            "VALIDATE",
            "FIX+VERIFY",
            "RECURSE+SUMMARY",
        ]

    @pytest.mark.parametrize(
        ("min_cycles", "max_cycles"),
        [
            (2, 4),
            (3, 7),
            (5, 4),
        ],
    )
    def test_validate_cycle_bounds_rejects_out_of_range_values(
        self, min_cycles: int, max_cycles: int
    ):
        validate_cycle_bounds = _require_attr("amplihack.recovery.stage3", "validate_cycle_bounds")

        with pytest.raises(ValueError):
            validate_cycle_bounds(min_cycles=min_cycles, max_cycles=max_cycles)

    def test_resolve_fix_verify_mode_defaults_to_read_only_without_worktree(self):
        resolve_fix_verify_mode = _require_attr(
            "amplihack.recovery.stage3", "resolve_fix_verify_mode"
        )

        assert resolve_fix_verify_mode(None) == "read-only"

    def test_resolve_fix_verify_mode_uses_isolated_worktree_when_present(self, tmp_path: Path):
        resolve_fix_verify_mode = _require_attr(
            "amplihack.recovery.stage3", "resolve_fix_verify_mode"
        )

        assert resolve_fix_verify_mode(tmp_path) == "isolated-worktree"

    def test_run_stage3_records_real_validator_output_and_honors_min_cycles(self, tmp_path: Path):
        run_stage3 = _require_attr("amplihack.recovery.stage3", "run_stage3")
        _init_pytest_repo(tmp_path)

        result = run_stage3(
            _make_stage2_result(),
            repo_path=tmp_path,
            worktree_path=None,
            min_cycles=3,
            max_cycles=6,
        )

        assert result.cycles_completed == 3
        assert result.blocked is True
        assert result.blockers[0].code == "fix-verify-blocked"
        assert result.cycles[0].validation_results
        assert result.cycles[0].validators == [
            "collect-only-baseline",
            "stage2-alignment",
            "fix-verify-worktree",
        ]
        assert result.cycles[0].validation_results[0].details.startswith("current collect-only")

    def test_run_stage3_accepts_valid_worktree_and_keeps_truthful_mode(self, tmp_path: Path):
        run_stage3 = _require_attr("amplihack.recovery.stage3", "run_stage3")
        repo_path = tmp_path / "repo"
        worktree_path = tmp_path / "worktree"
        repo_path.mkdir()
        _init_pytest_repo(repo_path)
        _make_worktree(repo_path, worktree_path)

        result = run_stage3(
            _make_stage2_result(),
            repo_path=repo_path,
            worktree_path=worktree_path,
            min_cycles=3,
            max_cycles=6,
        )

        assert result.fix_verify_mode == "isolated-worktree"
        assert result.blocked is False
        assert result.cycles_completed == 3
        assert result.cycles[0].validation_results[-1].status == "passed"

    def test_run_stage3_turns_invalid_worktree_into_structured_blocker(self, tmp_path: Path):
        run_stage3 = _require_attr("amplihack.recovery.stage3", "run_stage3")
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_pytest_repo(repo_path)
        invalid_worktree = tmp_path / "not-a-worktree"
        invalid_worktree.mkdir()

        result = run_stage3(
            _make_stage2_result(),
            repo_path=repo_path,
            worktree_path=invalid_worktree,
            min_cycles=3,
            max_cycles=6,
        )

        assert result.blocked is True
        assert result.blockers[0].code == "invalid-worktree"
        assert result.fix_verify_mode == "read-only"

    def test_run_stage3_turns_baseline_collect_only_timeout_into_structured_blocker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        stage3 = importlib.import_module("amplihack.recovery.stage3")
        repo_path = tmp_path / "repo"
        worktree_path = tmp_path / "worktree"
        repo_path.mkdir()
        _init_pytest_repo(repo_path)
        _make_worktree(repo_path, worktree_path)
        real_run_collect_only = stage3._run_collect_only

        def fake_run_collect_only(target_path: Path, *, timeout: int):
            if target_path.resolve() == repo_path.resolve():
                raise subprocess.TimeoutExpired(cmd=["pytest", "--collect-only"], timeout=timeout)
            return real_run_collect_only(target_path, timeout=timeout)

        monkeypatch.setattr(stage3, "_run_collect_only", fake_run_collect_only)

        result = stage3.run_stage3(
            _make_stage2_result(),
            repo_path=repo_path,
            worktree_path=worktree_path,
            min_cycles=3,
            max_cycles=6,
        )

        assert result.status == "blocked"
        assert result.blocked is True
        assert result.cycles_completed == 1
        assert result.fix_verify_mode == "isolated-worktree"
        assert result.blockers[0].code == "collect-timeout"
        assert result.cycles[0].validation_results[0].status == "blocked"
        assert "baseline collect-only failed" in result.cycles[0].validation_results[0].details

    @pytest.mark.parametrize(
        ("raised_exception", "expected_code"),
        [
            (FileNotFoundError("pytest not found in isolated worktree"), "pytest-unavailable"),
            (
                subprocess.TimeoutExpired(cmd=["pytest", "--collect-only"], timeout=300),
                "collect-timeout",
            ),
        ],
    )
    def test_run_stage3_turns_fix_verify_collect_only_failure_into_structured_blocker(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        raised_exception: FileNotFoundError | subprocess.TimeoutExpired,
        expected_code: str,
    ):
        stage3 = importlib.import_module("amplihack.recovery.stage3")
        repo_path = tmp_path / "repo"
        worktree_path = tmp_path / "worktree"
        repo_path.mkdir()
        _init_pytest_repo(repo_path)
        _make_worktree(repo_path, worktree_path)
        real_run_collect_only = stage3._run_collect_only

        def fake_run_collect_only(target_path: Path, *, timeout: int):
            if target_path.resolve() == worktree_path.resolve():
                raise raised_exception
            return real_run_collect_only(target_path, timeout=timeout)

        monkeypatch.setattr(stage3, "_run_collect_only", fake_run_collect_only)

        result = stage3.run_stage3(
            _make_stage2_result(),
            repo_path=repo_path,
            worktree_path=worktree_path,
            min_cycles=3,
            max_cycles=6,
        )

        assert result.status == "blocked"
        assert result.blocked is True
        assert result.cycles_completed == 1
        assert result.fix_verify_mode == "isolated-worktree"
        assert result.blockers[0].code == expected_code
        assert result.cycles[0].validation_results[-1].status == "blocked"
        assert "FIX+VERIFY collect-only failed" in result.cycles[0].validation_results[-1].details

    def test_run_stage3_propagates_unexpected_collect_only_exceptions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        stage3 = importlib.import_module("amplihack.recovery.stage3")
        _init_pytest_repo(tmp_path)

        def fake_run_collect_only(_repo_path: Path, *, timeout: int):
            raise RuntimeError(f"unexpected collect-only failure after {timeout}s")

        monkeypatch.setattr(stage3, "_run_collect_only", fake_run_collect_only)

        with pytest.raises(RuntimeError, match="unexpected collect-only failure"):
            stage3.run_stage3(
                _make_stage2_result(),
                repo_path=tmp_path,
                worktree_path=None,
                min_cycles=3,
                max_cycles=6,
            )
