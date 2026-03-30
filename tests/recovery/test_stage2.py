"""Tests for Stage 2 collect-only recovery behavior."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path


def _require_attr(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    assert hasattr(module, attr_name), f"{module_name} must define {attr_name}"
    return getattr(module, attr_name)


def _make_signature(
    *,
    signature_id: str,
    error_type: str = "ModuleNotFoundError",
    headline: str = "No module named 'missing_dep'",
    normalized_location: str = "tests/test_alpha.py",
    normalized_message: str | None = None,
    occurrences: int = 1,
):
    Stage2ErrorSignature = _require_attr("amplihack.recovery.models", "Stage2ErrorSignature")
    return Stage2ErrorSignature(
        signature_id=signature_id,
        error_type=error_type,
        headline=headline,
        normalized_location=normalized_location,
        normalized_message=normalized_message or headline,
        occurrences=occurrences,
    )


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


class TestCollectOnlyBaseline:
    """Authoritative baseline selection must use repo-root pytest.ini."""

    def test_build_collect_only_command_pins_repo_root_pytest_ini(self, tmp_path: Path):
        build_collect_only_command = _require_attr(
            "amplihack.recovery.stage2", "build_collect_only_command"
        )
        (tmp_path / "pytest.ini").write_text("[pytest]\n")

        command = build_collect_only_command(tmp_path)

        assert command[:2] == ["pytest", "--collect-only"]
        assert "-c" in command
        assert str(tmp_path / "pytest.ini") in command

    def test_detect_pytest_config_divergence_reports_pyproject_without_switching_baseline(
        self, tmp_path: Path
    ):
        detect_pytest_config_divergence = _require_attr(
            "amplihack.recovery.stage2", "detect_pytest_config_divergence"
        )
        (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
        (tmp_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\ntestpaths = ['tests', 'src']\n"
        )

        diagnostic = detect_pytest_config_divergence(tmp_path)

        assert diagnostic is not None
        assert diagnostic["diagnostic_code"] == "pytest-config-divergence"
        assert diagnostic["authoritative_config"] == str(tmp_path / "pytest.ini")


class TestSignatureNormalization:
    """Stable signatures should survive incidental output churn."""

    def test_extract_collect_location_rejects_malformed_marker_lines(self):
        stage2 = importlib.import_module("amplihack.recovery.stage2")

        assert (
            stage2._extract_collect_location(  # type: ignore[attr-defined]
                "________ Something ERROR collecting tests/test_alpha.py ________"
            )
            is None
        )

    def test_signature_ids_ignore_line_number_noise(self):
        build_error_signatures = _require_attr(
            "amplihack.recovery.stage2", "build_error_signatures"
        )
        first_output = """
________ ERROR collecting tests/test_alpha.py ________
tests/test_alpha.py:10: in <module>
    import missing_dep
E   ModuleNotFoundError: No module named 'missing_dep'
"""
        second_output = """
________ ERROR collecting tests/test_alpha.py ________
tests/test_alpha.py:42: in <module>
    import missing_dep
E   ModuleNotFoundError: No module named 'missing_dep'
"""

        first = build_error_signatures(first_output)
        second = build_error_signatures(second_output)

        assert len(first) == 1
        assert len(second) == 1
        assert first[0].signature_id == second[0].signature_id
        assert first[0].normalized_message == second[0].normalized_message

    def test_build_error_signatures_returns_empty_for_clean_collect_output(self):
        build_error_signatures = _require_attr(
            "amplihack.recovery.stage2", "build_error_signatures"
        )
        clean_output = """
============================= test session starts ==============================
collected 1 item

<Package tests>
  <Module test_ok.py>
    <Function test_ok>
========================== 1 test collected in 0.01s ==========================
"""

        assert build_error_signatures(clean_output) == []

    def test_cluster_signatures_groups_related_root_causes(self):
        cluster_signatures = _require_attr("amplihack.recovery.stage2", "cluster_signatures")
        signatures = [
            _make_signature(
                signature_id="sig-a",
                normalized_location="tests/test_alpha.py",
                occurrences=2,
            ),
            _make_signature(
                signature_id="sig-b",
                normalized_location="tests/test_beta.py",
                occurrences=1,
            ),
        ]

        clusters = cluster_signatures(signatures)

        assert len(clusters) == 1
        assert clusters[0]["signature_count"] == 2
        assert "dependency" in clusters[0]["root_cause"].lower()


class TestDeltaVerdict:
    """Stage 2 must distinguish reduced, unchanged, and replaced failures honestly."""

    def test_determine_delta_verdict_reports_reduced_when_counts_drop(self):
        determine_delta_verdict = _require_attr(
            "amplihack.recovery.stage2", "determine_delta_verdict"
        )
        baseline = [
            _make_signature(signature_id="sig-a"),
            _make_signature(signature_id="sig-b", normalized_location="tests/test_beta.py"),
        ]
        final = [_make_signature(signature_id="sig-a")]

        assert determine_delta_verdict(baseline, final) == "reduced"

    def test_determine_delta_verdict_reports_replaced_when_signature_family_changes(self):
        determine_delta_verdict = _require_attr(
            "amplihack.recovery.stage2", "determine_delta_verdict"
        )
        baseline = [_make_signature(signature_id="sig-a")]
        final = [
            _make_signature(
                signature_id="sig-new",
                error_type="ImportPathMismatchError",
                headline="import file mismatch",
                normalized_message="import file mismatch",
            )
        ]

        assert determine_delta_verdict(baseline, final) == "replaced"


class TestStage2Execution:
    """Stage 2 execution must preserve protected work and surface diagnostics."""

    def test_run_stage2_rejects_fix_batches_touching_protected_staged_files(
        self, tmp_path: Path, monkeypatch
    ):
        run_stage2 = _require_attr("amplihack.recovery.stage2", "run_stage2")
        stage2 = importlib.import_module("amplihack.recovery.stage2")
        _init_pytest_repo(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("protected\n")
        _git(tmp_path, "add", "docs/index.md")

        failing_collect_output = """
________ ERROR collecting tests/test_alpha.py ________
E   ModuleNotFoundError: No module named 'missing_dep'
"""
        monkeypatch.setattr(
            stage2,
            "_run_collect_only",
            lambda *_args, **_kwargs: (2, failing_collect_output),
        )

        def fixer(_clusters, _protected):
            return [{"cluster_id": "cluster-a", "files": ["docs/index.md"]}]

        result = run_stage2(
            tmp_path,
            protected_staged_files=["docs/index.md"],
            fixer=fixer,
        )

        assert result.status == "blocked"
        assert result.blockers[0].code == "protected-staged-overlap"
        assert result.applied_fixes == []

    def test_run_stage2_records_pytest_config_diagnostics(self, tmp_path: Path):
        run_stage2 = _require_attr("amplihack.recovery.stage2", "run_stage2")
        _init_pytest_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\ntestpaths = ['tests', 'src']\n"
        )

        result = run_stage2(tmp_path, protected_staged_files=[])

        assert result.status == "completed"
        assert result.diagnostics[0]["diagnostic_code"] == "pytest-config-divergence"

