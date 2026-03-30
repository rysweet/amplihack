"""Tests for recovery models and JSON ledger output."""

from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path


def _require_attr(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    assert hasattr(module, attr_name), f"{module_name} must define {attr_name}"
    return getattr(module, attr_name)


def _make_sample_run(tmp_path: Path):
    RecoveryBlocker = _require_attr("amplihack.recovery.models", "RecoveryBlocker")
    RecoveryRun = _require_attr("amplihack.recovery.models", "RecoveryRun")
    Stage1Result = _require_attr("amplihack.recovery.models", "Stage1Result")
    Stage2ErrorSignature = _require_attr("amplihack.recovery.models", "Stage2ErrorSignature")
    Stage2Result = _require_attr("amplihack.recovery.models", "Stage2Result")
    Stage3Cycle = _require_attr("amplihack.recovery.models", "Stage3Cycle")
    Stage3Result = _require_attr("amplihack.recovery.models", "Stage3Result")
    Stage3ValidatorResult = _require_attr("amplihack.recovery.models", "Stage3ValidatorResult")
    Stage4AtlasRun = _require_attr("amplihack.recovery.models", "Stage4AtlasRun")

    blocker = RecoveryBlocker(
        stage="stage3",
        code="fix-verify-blocked",
        message="FIX+VERIFY requires an isolated worktree",
        retryable=True,
    )
    signature = Stage2ErrorSignature(
        signature_id="sig-module-not-found",
        error_type="ModuleNotFoundError",
        headline="No module named 'missing_dep'",
        normalized_location="tests/test_alpha.py",
        normalized_message="No module named 'missing_dep'",
        occurrences=3,
    )
    validation = Stage3ValidatorResult(
        name="collect-only-baseline",
        status="passed",
        details="current collect-only count=0, stage2 final=0",
        metadata={"collection_errors": 0},
    )
    cycle = Stage3Cycle(
        cycle_number=1,
        phases=[
            "scope/setup",
            "SEEK",
            "VALIDATE",
            "FIX+VERIFY",
            "RECURSE+SUMMARY",
        ],
        findings=["Clustered import failures"],
        validators=["collect-only-baseline", "stage2-alignment", "fix-verify-worktree"],
        merged_validation="collect-only-baseline: current collect-only count=0, stage2 final=0",
        fix_verify_mode="read-only",
        blocked=True,
        validation_results=[validation],
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
        signatures=[signature],
        clusters=[
            {
                "cluster_id": "cluster-missing-dependency",
                "root_cause": "optional dependency gating",
                "signature_count": 1,
                "occurrences": 3,
            }
        ],
        applied_fixes=[
            {"cluster_id": "cluster-missing-dependency", "files": ["tests/test_alpha.py"]}
        ],
        diagnostics=[
            {
                "diagnostic_code": "pytest-config-divergence",
                "authoritative_config": str(tmp_path / "pytest.ini"),
                "secondary_config": str(tmp_path / "pyproject.toml"),
            }
        ],
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
        cycles=[cycle],
        blockers=[blocker],
    )
    stage4 = Stage4AtlasRun(
        status="completed",
        skill="code-atlas",
        provenance="current-tree-read-only",
        artifacts=[tmp_path / "files" / "code-atlas" / "atlas.mmd"],
        blockers=[],
    )
    return RecoveryRun(
        repo_path=tmp_path,
        started_at=datetime(2026, 3, 20, 5, 0, 43, tzinfo=UTC),
        finished_at=datetime(2026, 3, 20, 5, 8, 11, tzinfo=UTC),
        protected_staged_files=["docs/index.md", "uv.lock"],
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage4=stage4,
        blockers=[blocker],
    )


class TestRecoveryModels:
    """Typed model contracts from the recovery reference."""

    def test_recovery_run_can_be_constructed_from_documented_fields(self, tmp_path: Path):
        run = _make_sample_run(tmp_path)

        assert run.stage2.baseline_collection_errors == 28
        assert run.stage3.cycles[0].validators == [
            "collect-only-baseline",
            "stage2-alignment",
            "fix-verify-worktree",
        ]
        assert run.stage4.artifacts == [tmp_path / "files" / "code-atlas" / "atlas.mmd"]


class TestRecoveryLedgerRendering:
    """Machine-checkable JSON output for downstream tooling."""

    def test_recovery_run_to_json_preserves_exact_counts_and_blockers(self, tmp_path: Path):
        recovery_run_to_json = _require_attr("amplihack.recovery.results", "recovery_run_to_json")
        run = _make_sample_run(tmp_path)

        payload = recovery_run_to_json(run)

        assert payload["repo_path"] == str(tmp_path.resolve())
        assert payload["started_at"] == "2026-03-20T05:00:43Z"
        assert payload["finished_at"] == "2026-03-20T05:08:11Z"
        assert payload["stage2"]["baseline_collection_errors"] == 28
        assert payload["stage2"]["final_collection_errors"] == 21
        assert payload["stage2"]["delta_verdict"] == "reduced"
        assert payload["stage2"]["diagnostics"][0]["diagnostic_code"] == "pytest-config-divergence"
        assert payload["stage3"]["fix_verify_mode"] == "read-only"
        assert (
            payload["stage3"]["cycles"][0]["validation_results"][0]["name"]
            == "collect-only-baseline"
        )
        assert payload["stage4"]["artifacts"] == [
            str(tmp_path / "files" / "code-atlas" / "atlas.mmd")
        ]
        assert payload["blockers"][0]["code"] == "fix-verify-blocked"

    def test_write_recovery_ledger_round_trips_json(self, tmp_path: Path):
        recovery_run_to_json = _require_attr("amplihack.recovery.results", "recovery_run_to_json")
        write_recovery_ledger = _require_attr("amplihack.recovery.results", "write_recovery_ledger")
        run = _make_sample_run(tmp_path)
        output_path = tmp_path / "recovery.json"

        write_recovery_ledger(run, output_path)

        payload = json.loads(output_path.read_text())
        assert payload == recovery_run_to_json(run)

