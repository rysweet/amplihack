"""TDD contract tests for scoped publish validation scope building (#4064)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BUILD_SCOPE = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "pre-commit"
    / "build_publish_validation_scope.py"
)


def _write(repo: Path, relative_path: str, content: str = "") -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_scope_builder(
    repo: Path, manifest_entries: list[str], *, exclude_claude_scenarios: bool = False
) -> tuple[subprocess.CompletedProcess[str], Path]:
    manifest_path = repo / "publish-manifest.txt"
    scope_path = repo / "validation-scope.txt"
    manifest_text = "\n".join(manifest_entries)
    if manifest_text:
        manifest_text += "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")

    command = [
        sys.executable,
        str(BUILD_SCOPE),
        "--manifest",
        str(manifest_path),
        "--output",
        str(scope_path),
        "--repo-root",
        str(repo),
    ]
    if exclude_claude_scenarios:
        command.append("--exclude-claude-scenarios")

    result = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result, scope_path


def _read_scope(scope_path: Path) -> list[str]:
    return [
        line.strip() for line in scope_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_builds_scope_from_seed_files_without_unrelated_optional_imports(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    _write(repo, "README.md", "publish metadata\n")
    _write(repo, "src/published_pkg/__init__.py")
    _write(
        repo, "src/published_pkg/publish_entry.py", "from published_pkg.local_dep import VALUE\n"
    )
    _write(repo, "src/published_pkg/local_dep.py", "VALUE = 1\n")
    _write(repo, "src/unrelated_ui/screen.py", "import textual\n")
    _write(repo, "src/unrelated_hooks/amplifier_wrapper.py", "import amplifier_core\n")
    _write(repo, ".claude/scenarios/demo/run.py", "import textual\n")

    result, scope_path = _run_scope_builder(
        repo,
        [
            "src/published_pkg/publish_entry.py",
            "README.md",
            "src/published_pkg/publish_entry.py",
        ],
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert json.loads(result.stdout) == {
        "seed_count": 1,
        "expanded_local_dep_count": 1,
        "validated_count": 2,
    }
    assert _read_scope(scope_path) == [
        "src/published_pkg/publish_entry.py",
        "src/published_pkg/local_dep.py",
    ]


def test_bundle_module_seed_does_not_expand_into_other_module_roots(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    _write(repo, "amplifier-bundle/modules/workflow_one/__init__.py")
    _write(
        repo, "amplifier-bundle/modules/workflow_one/publish_entry.py", "from .helper import run\n"
    )
    _write(repo, "amplifier-bundle/modules/workflow_one/helper.py", "def run():\n    return 'ok'\n")
    _write(repo, "amplifier-bundle/modules/workflow_two/__init__.py")
    _write(repo, "amplifier-bundle/modules/workflow_two/optional_dep.py", "import amplifier_core\n")

    result, scope_path = _run_scope_builder(
        repo,
        ["amplifier-bundle/modules/workflow_one/publish_entry.py"],
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert json.loads(result.stdout) == {
        "seed_count": 1,
        "expanded_local_dep_count": 1,
        "validated_count": 2,
    }
    assert _read_scope(scope_path) == [
        "amplifier-bundle/modules/workflow_one/publish_entry.py",
        "amplifier-bundle/modules/workflow_one/helper.py",
    ]


def test_exclude_claude_scenarios_flag_drops_staged_scenario_seeds(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    _write(repo, "src/published_pkg/__init__.py")
    _write(
        repo, "src/published_pkg/publish_entry.py", "from published_pkg.local_dep import VALUE\n"
    )
    _write(repo, "src/published_pkg/local_dep.py", "VALUE = 1\n")
    _write(repo, ".claude/scenarios/demo/run.py", "import textual\n")

    result, scope_path = _run_scope_builder(
        repo,
        [
            "src/published_pkg/publish_entry.py",
            ".claude/scenarios/demo/run.py",
        ],
        exclude_claude_scenarios=True,
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert json.loads(result.stdout) == {
        "seed_count": 1,
        "expanded_local_dep_count": 1,
        "validated_count": 2,
    }
    assert _read_scope(scope_path) == [
        "src/published_pkg/publish_entry.py",
        "src/published_pkg/local_dep.py",
    ]


def test_rejects_unsafe_manifest_paths(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")

    result, _scope_path = _run_scope_builder(
        repo,
        ["../outside.py", str(outside)],
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "outside.py" in combined
    assert "manifest" in combined.lower()
