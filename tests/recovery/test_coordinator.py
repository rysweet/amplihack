"""Integration-style tests for sequencing the recovery stages."""

from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest


def _require_attr(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    assert hasattr(module, attr_name), f"{module_name} must define {attr_name}"
    return getattr(module, attr_name)


def _make_stage_results(tmp_path: Path):
    RecoveryBlocker = _require_attr("amplihack.recovery.models", "RecoveryBlocker")
    Stage1Result = _require_attr("amplihack.recovery.models", "Stage1Result")
    Stage2Result = _require_attr("amplihack.recovery.models", "Stage2Result")
    Stage3Result = _require_attr("amplihack.recovery.models", "Stage3Result")
    Stage4AtlasRun = _require_attr("amplihack.recovery.models", "Stage4AtlasRun")

    blocker = RecoveryBlocker(
        stage="stage3",
        code="fix-verify-blocked",
        message="FIX+VERIFY requires an isolated worktree",
        retryable=True,
    )
    stage1 = Stage1Result(
        status="completed",
        mode="no-op",
        protected_staged_files=["docs/index.md", "uv.lock"],
        actions=["captured protected staged set", "found no uncommitted .claude changes"],
        blockers=[],
    )
    stage2 = Stage2Result(
        status="completed",
        baseline_collection_errors=28,
        final_collection_errors=21,
        delta_verdict="reduced",
        signatures=[],
        clusters=[],
        applied_fixes=[],
        diagnostics=[],
        blockers=[],
    )
    stage3 = Stage3Result(
        status="completed",
        cycles_completed=3,
        fix_verify_mode="read-only",
        blocked=True,
        phases=[
            "scope/setup",
            "SEEK",
            "VALIDATE",
            "FIX+VERIFY",
            "RECURSE+SUMMARY",
        ],
        cycles=[],
        blockers=[blocker],
    )
    stage4 = Stage4AtlasRun(
        status="completed",
        skill="code-atlas",
        provenance="current-tree-read-only",
        artifacts=[tmp_path / "atlas.mmd"],
        blockers=[],
    )
    return blocker, stage1, stage2, stage3, stage4


class TestRecoveryCoordinator:
    """Coordinator behavior over Stage 1-4 sequencing and ledger emission."""

    def test_run_recovery_sequences_stages_and_writes_single_ledger(
        self, tmp_path: Path, monkeypatch
    ):
        coordinator = importlib.import_module("amplihack.recovery.coordinator")
        run_recovery = _require_attr("amplihack.recovery.coordinator", "run_recovery")
        blocker, stage1, stage2, stage3, stage4 = _make_stage_results(tmp_path)
        calls: list[str] = []

        def _record(name: str, value):
            def _runner(*_args, **_kwargs):
                calls.append(name)
                return value

            return _runner

        monkeypatch.setattr(coordinator, "run_stage1", _record("stage1", stage1))
        monkeypatch.setattr(coordinator, "run_stage2", _record("stage2", stage2))
        monkeypatch.setattr(coordinator, "run_stage3", _record("stage3", stage3))
        monkeypatch.setattr(coordinator, "run_stage4", _record("stage4", stage4))
        monkeypatch.setattr(
            coordinator,
            "require_isolated_worktree",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError("unused")),
        )

        result = run_recovery(
            repo_path=tmp_path,
            output_path=tmp_path / "recovery.json",
            worktree_path=None,
            min_audit_cycles=3,
            max_audit_cycles=3,
            started_at=datetime(2026, 3, 20, 5, 0, 43, tzinfo=UTC),
        )

        assert calls == ["stage1", "stage2", "stage3", "stage4"]
        assert result.protected_staged_files == ["docs/index.md", "uv.lock"]
        payload = json.loads((tmp_path / "recovery.json").read_text())
        assert payload["stage2"]["delta_verdict"] == "reduced"
        assert payload["stage4"]["skill"] == "code-atlas"
        assert payload["blockers"][0]["code"] == blocker.code

    def test_run_recovery_turns_invalid_worktree_into_stage3_blocker(
        self, tmp_path: Path, monkeypatch
    ):
        coordinator = importlib.import_module("amplihack.recovery.coordinator")
        run_recovery = _require_attr("amplihack.recovery.coordinator", "run_recovery")
        _blocker, stage1, stage2, _stage3, stage4 = _make_stage_results(tmp_path)

        monkeypatch.setattr(coordinator, "run_stage1", lambda *_args, **_kwargs: stage1)
        monkeypatch.setattr(coordinator, "run_stage2", lambda *_args, **_kwargs: stage2)
        monkeypatch.setattr(coordinator, "run_stage4", lambda *_args, **_kwargs: stage4)
        monkeypatch.setattr(
            coordinator,
            "require_isolated_worktree",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError("recovery requires a git worktree")),
        )

        captured = {}

        def fake_run_stage3(*_args, initial_blockers=None, worktree_path=None, **_kwargs):
            captured["initial_blockers"] = initial_blockers
            captured["worktree_path"] = worktree_path
            Stage3Result = _require_attr("amplihack.recovery.models", "Stage3Result")
            return Stage3Result(
                status="blocked",
                cycles_completed=3,
                fix_verify_mode="read-only",
                blocked=True,
                phases=["scope/setup", "SEEK", "VALIDATE", "FIX+VERIFY", "RECURSE+SUMMARY"],
                cycles=[],
                blockers=list(initial_blockers or []),
            )

        monkeypatch.setattr(coordinator, "run_stage3", fake_run_stage3)

        result = run_recovery(
            repo_path=tmp_path,
            worktree_path=tmp_path / "bad-worktree",
        )

        assert captured["worktree_path"] is None
        assert captured["initial_blockers"][0].code == "invalid-worktree"
        assert result.blockers[0].code == "invalid-worktree"

    def test_recovery_cli_returns_zero_when_ledger_is_emitted_with_stage_blockers(
        self, tmp_path: Path, monkeypatch
    ):
        main = _require_attr("amplihack.recovery.__main__", "main")
        RecoveryRun = _require_attr("amplihack.recovery.models", "RecoveryRun")
        write_recovery_ledger = _require_attr("amplihack.recovery.results", "write_recovery_ledger")
        blocker, stage1, stage2, stage3, stage4 = _make_stage_results(tmp_path)
        fake_run = RecoveryRun(
            repo_path=tmp_path,
            started_at=datetime(2026, 3, 20, 5, 0, 43, tzinfo=UTC),
            finished_at=datetime(2026, 3, 20, 5, 8, 11, tzinfo=UTC),
            protected_staged_files=stage1.protected_staged_files,
            stage1=stage1,
            stage2=stage2,
            stage3=stage3,
            stage4=stage4,
            blockers=[blocker],
        )
        coordinator = importlib.import_module("amplihack.recovery.coordinator")

        def fake_run_recovery(*_args, output_path=None, **_kwargs):
            if output_path is not None:
                write_recovery_ledger(fake_run, output_path)
            return fake_run

        monkeypatch.setattr(coordinator, "run_recovery", fake_run_recovery)

        exit_code = main(
            [
                "run",
                "--repo",
                str(tmp_path),
                "--output",
                str(tmp_path / "cli-ledger.json"),
            ]
        )

        assert exit_code == 0
        assert json.loads((tmp_path / "cli-ledger.json").read_text())["blockers"][0]["code"] == (
            "fix-verify-blocked"
        )

    def test_main_cli_registers_recovery_run_help(self):
        cli_module = importlib.import_module("amplihack.cli")
        create_parser = cli_module._load_cli_module().create_parser

        with pytest.raises(SystemExit) as exc:
            create_parser().parse_args(["recovery", "run", "--help"])

        assert exc.value.code == 0
