"""TDD contract tests for scoped --files-from import validation (#4064)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CHECK_IMPORTS = Path(__file__).resolve().parents[3] / "scripts" / "pre-commit" / "check_imports.py"


def _write(repo: Path, relative_path: str, content: str = "") -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "src/published_pkg/__init__.py")
    return repo


def _write_scope(repo: Path, *entries: str) -> Path:
    scope_path = repo / "validation-scope.txt"
    scope_text = "\n".join(entries)
    if scope_text:
        scope_text += "\n"
    scope_path.write_text(scope_text, encoding="utf-8")
    return scope_path


def _run_check_imports(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_IMPORTS), *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_files_from_checks_only_scoped_files_when_unrelated_textual_import_exists(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write(repo, "src/published_pkg/main.py", "VALUE = 1\n")
    _write(repo, "src/unrelated_ui/screen.py", "import textual\n")
    scope_path = _write_scope(repo, "src/published_pkg/main.py")

    result = _run_check_imports(repo, "--files-from", str(scope_path))
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "Checking imports for 1 file(s)" in combined
    assert "src/published_pkg/main.py" in combined
    assert "src/unrelated_ui/screen.py" not in combined


def test_files_from_checks_only_scoped_files_when_unrelated_amplifier_core_import_exists(
    tmp_path: Path,
):
    repo = _make_repo(tmp_path)
    _write(repo, "src/published_pkg/main.py", "VALUE = 1\n")
    _write(repo, "src/unrelated_hooks/wrapper.py", "import amplifier_core\n")
    scope_path = _write_scope(repo, "src/published_pkg/main.py")

    result = _run_check_imports(repo, "--files-from", str(scope_path))
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "Checking imports for 1 file(s)" in combined
    assert "src/published_pkg/main.py" in combined
    assert "src/unrelated_hooks/wrapper.py" not in combined


def test_files_from_ignores_unrelated_claude_scenarios(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write(repo, "src/published_pkg/main.py", "VALUE = 1\n")
    _write(repo, ".claude/scenarios/demo/run.py", "import textual\n")
    scope_path = _write_scope(repo, "src/published_pkg/main.py")

    result = _run_check_imports(repo, "--files-from", str(scope_path))
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "Checking imports for 1 file(s)" in combined
    assert "src/published_pkg/main.py" in combined
    assert ".claude/scenarios/demo/run.py" not in combined


def test_files_from_empty_scope_is_explicit_success(tmp_path: Path):
    repo = _make_repo(tmp_path)
    scope_path = _write_scope(repo)

    result = _run_check_imports(repo, "--files-from", str(scope_path))
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "No Python files to check" in combined


def test_files_from_relevant_missing_import_still_fails(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write(repo, "src/published_pkg/relevant_missing.py", "import definitely_missing_module\n")
    scope_path = _write_scope(repo, "src/published_pkg/relevant_missing.py")

    result = _run_check_imports(repo, "--files-from", str(scope_path))
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "src/published_pkg/relevant_missing.py" in combined
    assert "definitely_missing_module" in combined


def test_files_from_rejects_non_python_entries(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write(repo, "README.md", "not python\n")
    scope_path = _write_scope(repo, "README.md")

    result = _run_check_imports(repo, "--files-from", str(scope_path))
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "README.md" in combined
    assert ".py" in combined


def test_positional_files_mode_still_works(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write(repo, "src/published_pkg/main.py", "VALUE = 1\n")

    result = _run_check_imports(repo, "src/published_pkg/main.py")
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "Checking imports for 1 file(s)" in combined
    assert "src/published_pkg/main.py" in combined


def test_positional_files_reject_outside_repo_paths(tmp_path: Path):
    repo = _make_repo(tmp_path)
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("VALUE = 1\n", encoding="utf-8")

    result = _run_check_imports(repo, str(outside_file))
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "repo-relative" in combined or "outside repository" in combined


def test_import_failures_are_sanitized_and_use_scrubbed_environment(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write(
        repo,
        "src/published_pkg/leaky.py",
        "import os\n"
        "if os.environ.get('SECRET_TOKEN'):\n"
        "    raise RuntimeError('saw secret')\n"
        "raise LookupError('missing secret')\n",
    )

    result = subprocess.run(
        [sys.executable, str(CHECK_IMPORTS), "src/published_pkg/leaky.py"],
        cwd=repo,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "SECRET_TOKEN": "test-key-for-unit-tests",  # pragma: allowlist secret
        },
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "LookupError" in combined
    assert "RuntimeError" not in combined
    assert "TOPSECRET" not in combined
    assert "saw secret" not in combined
    assert "missing secret" not in combined


def test_files_from_is_mutually_exclusive_with_positional_files(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write(repo, "src/published_pkg/main.py", "VALUE = 1\n")
    scope_path = _write_scope(repo, "src/published_pkg/main.py")

    result = _run_check_imports(
        repo,
        "--files-from",
        str(scope_path),
        "src/published_pkg/main.py",
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "exclusive" in combined.lower()
