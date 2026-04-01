"""Tests for build_publish_validation_scope.py.

Validates:
- Scope building from staged files
- Exclusion of .claude/scenarios, tests, vendor, etc.
- Edge cases: empty scope, single file, nested tests dirs
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pre-commit"))
import build_publish_validation_scope as scope_mod

# ---------------------------------------------------------------------------
# build_scope() unit tests
# ---------------------------------------------------------------------------


class TestBuildScope:
    """Unit tests for build_scope with pre-supplied file lists."""

    def test_empty_staged_files(self):
        """Empty staged list produces empty scope."""
        assert scope_mod.build_scope(staged_files=[]) == []

    def test_single_src_file(self):
        """A single src/ Python file passes through."""
        result = scope_mod.build_scope(staged_files=["src/amplihack/core.py"])
        assert result == ["src/amplihack/core.py"]

    def test_excludes_scenarios(self):
        """.claude/scenarios/ files are excluded."""
        files = [
            "src/amplihack/core.py",
            ".claude/scenarios/check-broken-links/main.py",
        ]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_tools(self):
        """.claude/tools/ files are excluded."""
        files = ["src/amplihack/core.py", ".claude/tools/amplihack/hook.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_skills(self):
        """.claude/skills/ files are excluded."""
        files = ["src/amplihack/core.py", ".claude/skills/quality_audit.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_toplevel_tests(self):
        """tests/ directory is excluded."""
        files = ["src/amplihack/core.py", "tests/test_core.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_nested_tests(self):
        """Nested tests/ directories (e.g. src/pkg/tests/) are excluded."""
        files = [
            "src/amplihack/core.py",
            "src/amplihack/tests/test_core.py",
        ]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_archive(self):
        """archive/ is excluded."""
        files = ["src/amplihack/core.py", "archive/old_module.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_experiments(self):
        """experiments/ is excluded."""
        files = ["src/amplihack/core.py", "experiments/trial.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_deploy(self):
        """deploy/ is excluded."""
        files = ["src/amplihack/core.py", "deploy/setup.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_build_hooks(self):
        """build_hooks.py at repo root is excluded."""
        files = ["src/amplihack/core.py", "build_hooks.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_excludes_github_scripts(self):
        """.github/scripts/ is excluded."""
        files = ["src/amplihack/core.py", ".github/scripts/release.py"]
        result = scope_mod.build_scope(staged_files=files)
        assert result == ["src/amplihack/core.py"]

    def test_multiple_valid_files_sorted(self):
        """Multiple valid files are returned sorted."""
        files = [
            "src/amplihack/z_module.py",
            "src/amplihack/a_module.py",
            "scripts/helper.py",
        ]
        result = scope_mod.build_scope(staged_files=files)
        assert result == [
            "scripts/helper.py",
            "src/amplihack/a_module.py",
            "src/amplihack/z_module.py",
        ]

    def test_mixed_included_and_excluded(self):
        """Mix of included and excluded files filters correctly."""
        files = [
            "src/amplihack/core.py",
            "tests/test_core.py",
            ".claude/scenarios/tool/main.py",
            "src/amplihack/utils.py",
            "archive/legacy.py",
            "scripts/pre-commit/check_imports.py",
        ]
        result = scope_mod.build_scope(staged_files=files)
        assert result == [
            "scripts/pre-commit/check_imports.py",
            "src/amplihack/core.py",
            "src/amplihack/utils.py",
        ]

    def test_non_python_files_not_in_staged(self):
        """Non-.py files should not appear (they are filtered at git level)."""
        # build_scope trusts the input is already .py-only from
        # get_staged_python_files, but is_excluded doesn't check extension.
        # This test documents that behaviour.
        files = ["src/amplihack/core.py", "README.md"]
        result = scope_mod.build_scope(staged_files=files)
        # README.md passes through because is_excluded only checks prefixes/dirs
        # This is acceptable because get_staged_python_files pre-filters.
        assert "src/amplihack/core.py" in result


# ---------------------------------------------------------------------------
# is_excluded() unit tests
# ---------------------------------------------------------------------------


class TestIsExcluded:
    """Direct tests for the is_excluded helper."""

    def test_src_file_not_excluded(self):
        assert not scope_mod.is_excluded("src/amplihack/core.py")

    def test_scenarios_excluded(self):
        assert scope_mod.is_excluded(".claude/scenarios/foo/bar.py")

    def test_tools_excluded(self):
        assert scope_mod.is_excluded(".claude/tools/amplihack/hook.py")

    def test_root_tests_excluded(self):
        assert scope_mod.is_excluded("tests/unit/test_foo.py")

    def test_nested_tests_excluded(self):
        assert scope_mod.is_excluded("src/amplihack/tests/test_bar.py")

    def test_scripts_not_excluded(self):
        assert not scope_mod.is_excluded("scripts/pre-commit/check_imports.py")


# ---------------------------------------------------------------------------
# get_staged_python_files() integration tests (mocked git)
# ---------------------------------------------------------------------------


class TestGetStagedPythonFiles:
    """Tests for git interaction in get_staged_python_files."""

    def test_parses_git_output(self):
        mock_result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="src/amplihack/core.py\nsrc/amplihack/utils.py\nREADME.md\n",
            stderr="",
        )
        with patch("build_publish_validation_scope.subprocess.run", return_value=mock_result):
            result = scope_mod.get_staged_python_files()
        assert result == ["src/amplihack/core.py", "src/amplihack/utils.py"]

    def test_empty_git_output(self):
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("build_publish_validation_scope.subprocess.run", return_value=mock_result):
            result = scope_mod.get_staged_python_files()
        assert result == []

    def test_git_failure_exits(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: not a git repo"
        )
        with patch("build_publish_validation_scope.subprocess.run", return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                scope_mod.get_staged_python_files()
            assert exc_info.value.code == 1

    def test_git_not_found_exits(self):
        with patch(
            "build_publish_validation_scope.subprocess.run",
            side_effect=FileNotFoundError("git"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                scope_mod.get_staged_python_files()
            assert exc_info.value.code == 1

    def test_git_timeout_exits(self):
        with patch(
            "build_publish_validation_scope.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
        ):
            with pytest.raises(SystemExit) as exc_info:
                scope_mod.get_staged_python_files()
            assert exc_info.value.code == 1
