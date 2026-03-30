"""Tests for Stage 4 code-atlas execution and provenance."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

from amplihack.utils.process import CommandResult


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


def _init_repo(repo_path: Path) -> None:
    _git(repo_path, "init")
    _git(repo_path, "config", "user.email", "tests@example.com")
    _git(repo_path, "config", "user.name", "Recovery Tests")
    (repo_path / "pytest.ini").write_text("[pytest]\n")
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    _git(repo_path, "add", "pytest.ini", "tests/test_ok.py")
    _git(repo_path, "commit", "-m", "initial")


def _make_worktree(repo_path: Path, worktree_path: Path) -> None:
    _git(repo_path, "worktree", "add", str(worktree_path), "HEAD")


class TestStage4AtlasProvenance:
    """Stage 4 must report where atlas ran, not just whether it ran."""

    def test_determine_atlas_target_prefers_validated_isolated_worktree(self, tmp_path: Path):
        determine_atlas_target = _require_attr(
            "amplihack.recovery.stage4", "determine_atlas_target"
        )
        repo_path = tmp_path / "repo"
        worktree_path = tmp_path / "worktree"
        repo_path.mkdir()
        _init_repo(repo_path)
        _make_worktree(repo_path, worktree_path)

        target, provenance = determine_atlas_target(
            repo_path=repo_path, worktree_path=worktree_path
        )

        assert target == worktree_path
        assert provenance == "isolated-worktree"

    def test_determine_atlas_target_falls_back_to_current_tree_for_invalid_worktree(
        self, tmp_path: Path
    ):
        determine_atlas_target = _require_attr(
            "amplihack.recovery.stage4", "determine_atlas_target"
        )
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_repo(repo_path)
        invalid_worktree = tmp_path / "worktree"
        invalid_worktree.mkdir()

        target, provenance = determine_atlas_target(
            repo_path=repo_path, worktree_path=invalid_worktree
        )

        assert target == repo_path
        assert provenance == "current-tree-read-only"

    def test_run_code_atlas_marks_stage_blocked_when_runtime_is_unavailable(self, tmp_path: Path):
        run_code_atlas = _require_attr("amplihack.recovery.stage4", "run_code_atlas")
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        def missing_executor(*_args, **_kwargs):
            raise FileNotFoundError("code-atlas runtime missing")

        result = run_code_atlas(repo_path=repo_path, worktree_path=None, executor=missing_executor)

        assert result.status == "blocked"
        assert result.skill == "code-atlas"
        assert result.provenance == "blocked"
        assert result.blockers[0].code == "code-atlas-unavailable"

    def test_code_atlas_adapter_retries_timeout_and_returns_artifact(
        self, tmp_path: Path, monkeypatch
    ):
        stage4 = importlib.import_module("amplihack.recovery.stage4")
        adapter = _require_attr("amplihack.recovery.stage4", "CodeAtlasAdapter")(
            timeout=5,
            max_attempts=2,
            backoff_seconds=0,
            sleeper=lambda _seconds: None,
        )
        repo_path = tmp_path / "repo"
        artifact_dir = tmp_path / "artifacts"
        repo_path.mkdir()

        calls = {"count": 0}

        def fake_run_command_with_timeout(command, *, cwd, timeout):
            calls["count"] += 1
            if calls["count"] == 1:
                raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)
            output_path = Path(command[-1])
            output_path.write_text('{"ok": true}\n')
            return CommandResult(
                args=tuple(command),
                returncode=0,
                stdout="",
                stderr="",
            )

        monkeypatch.setattr(stage4, "run_command_with_timeout", fake_run_command_with_timeout)

        artifacts = adapter(repo_path, artifact_dir)

        assert calls["count"] == 2
        assert artifacts == [artifact_dir / "atlas.json"]

    def test_run_code_atlas_marks_stage_blocked_when_runtime_exits_nonzero(
        self, tmp_path: Path, monkeypatch
    ):
        stage4 = importlib.import_module("amplihack.recovery.stage4")
        run_code_atlas = _require_attr("amplihack.recovery.stage4", "run_code_atlas")
        adapter = _require_attr("amplihack.recovery.stage4", "CodeAtlasAdapter")(
            timeout=5,
            max_attempts=2,
            backoff_seconds=0,
            sleeper=lambda _seconds: None,
        )
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        def fake_run_command_with_timeout(command, *, cwd, timeout):
            return CommandResult(
                args=tuple(command),
                returncode=23,
                stdout="",
                stderr="temporary upstream failure",
            )

        monkeypatch.setattr(stage4, "run_command_with_timeout", fake_run_command_with_timeout)

        result = run_code_atlas(repo_path=repo_path, worktree_path=None, executor=adapter)

        assert result.status == "blocked"
        assert result.blockers[0].code == "code-atlas-failed"
        assert result.blockers[0].retryable is True
        assert "status 23" in result.blockers[0].message

    def test_run_code_atlas_marks_stage_blocked_when_artifact_is_missing(
        self, tmp_path: Path, monkeypatch
    ):
        stage4 = importlib.import_module("amplihack.recovery.stage4")
        run_code_atlas = _require_attr("amplihack.recovery.stage4", "run_code_atlas")
        adapter = _require_attr("amplihack.recovery.stage4", "CodeAtlasAdapter")(
            timeout=5,
            max_attempts=1,
            backoff_seconds=0,
            sleeper=lambda _seconds: None,
        )
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        def fake_run_command_with_timeout(command, *, cwd, timeout):
            return CommandResult(
                args=tuple(command),
                returncode=0,
                stdout="completed",
                stderr="",
            )

        monkeypatch.setattr(stage4, "run_command_with_timeout", fake_run_command_with_timeout)

        result = run_code_atlas(repo_path=repo_path, worktree_path=None, executor=adapter)

        assert result.status == "blocked"
        assert result.blockers[0].code == "code-atlas-failed"
        assert "without creating atlas.json" in result.blockers[0].message
