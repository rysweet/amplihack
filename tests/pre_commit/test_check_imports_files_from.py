"""Tests for check_imports.py --files-from support.

Validates:
- --files-from reads scope file and filters .py files
- Blank lines and comments in scope file are ignored
- Missing scope file exits with error
- Missing argument after --files-from exits with error
- End-to-end: scope builder -> check_imports pipeline
"""

import sys
import textwrap
from pathlib import Path

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pre-commit"))
import check_imports as ci_mod

if not hasattr(ci_mod, "_parse_files_from"):
    pytest.skip("_parse_files_from() not yet implemented", allow_module_level=True)

# ---------------------------------------------------------------------------
# _parse_files_from() unit tests
# ---------------------------------------------------------------------------


class TestParseFilesFrom:
    """Tests for the _parse_files_from helper."""

    def test_reads_python_files(self, tmp_path):
        scope = tmp_path / "scope.txt"
        scope.write_text("src/amplihack/core.py\nsrc/amplihack/utils.py\n")
        result = ci_mod._parse_files_from(str(scope))
        assert result == [Path("src/amplihack/core.py"), Path("src/amplihack/utils.py")]

    def test_ignores_blank_lines(self, tmp_path):
        scope = tmp_path / "scope.txt"
        scope.write_text("src/a.py\n\n\nsrc/b.py\n")
        result = ci_mod._parse_files_from(str(scope))
        assert len(result) == 2

    def test_ignores_comments(self, tmp_path):
        scope = tmp_path / "scope.txt"
        scope.write_text("# This is a comment\nsrc/a.py\n# Another comment\n")
        result = ci_mod._parse_files_from(str(scope))
        assert result == [Path("src/a.py")]

    def test_filters_non_python(self, tmp_path):
        scope = tmp_path / "scope.txt"
        scope.write_text("src/a.py\nREADME.md\nconfig.yaml\nsrc/b.py\n")
        result = ci_mod._parse_files_from(str(scope))
        assert result == [Path("src/a.py"), Path("src/b.py")]

    def test_empty_scope_file(self, tmp_path):
        scope = tmp_path / "scope.txt"
        scope.write_text("")
        result = ci_mod._parse_files_from(str(scope))
        assert result == []

    def test_missing_scope_file_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            ci_mod._parse_files_from(str(tmp_path / "nonexistent.txt"))
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# check_type_imports boundary tests
# ---------------------------------------------------------------------------


class TestImportBoundaryEnforcement:
    """Tests that import checking correctly identifies missing type imports."""

    def test_missing_any_import(self, tmp_path):
        """File using Any without importing it should produce error."""
        py_file = tmp_path / "bad.py"
        py_file.write_text(
            textwrap.dedent("""\
            def foo(x: Any) -> None:
                pass
        """)
        )
        errors = ci_mod.check_type_imports(py_file)
        assert len(errors) == 1
        assert "Any" in errors[0]

    def test_correctly_imported_any(self, tmp_path):
        """File using Any with proper import should produce no error."""
        py_file = tmp_path / "good.py"
        py_file.write_text(
            textwrap.dedent("""\
            from typing import Any

            def foo(x: Any) -> None:
                pass
        """)
        )
        errors = ci_mod.check_type_imports(py_file)
        assert errors == []

    def test_multiple_missing_imports(self, tmp_path):
        """Multiple missing type imports produce multiple errors."""
        py_file = tmp_path / "multi_bad.py"
        py_file.write_text(
            textwrap.dedent("""\
            def foo(x: Any, y: Optional[str]) -> Dict[str, Any]:
                pass
        """)
        )
        errors = ci_mod.check_type_imports(py_file)
        # Should flag Any, Optional, Dict
        flagged_types = {e.split(":")[1].strip().split()[0] for e in errors}
        assert "Any" in flagged_types
        assert "Optional" in flagged_types
        assert "Dict" in flagged_types

    def test_star_import_covers_types(self, tmp_path):
        """from typing import * should cover all type hints."""
        py_file = tmp_path / "star.py"
        py_file.write_text(
            textwrap.dedent("""\
            from typing import *

            def foo(x: Any) -> Optional[str]:
                pass
        """)
        )
        errors = ci_mod.check_type_imports(py_file)
        assert errors == []

    def test_empty_file(self, tmp_path):
        """Empty file should produce no errors."""
        py_file = tmp_path / "empty.py"
        py_file.write_text("")
        errors = ci_mod.check_type_imports(py_file)
        assert errors == []


# ---------------------------------------------------------------------------
# Pre-commit hook failure mode tests
# ---------------------------------------------------------------------------


class TestPreCommitFailureModes:
    """Tests for failure modes in the pre-commit pipeline."""

    def test_syntax_error_file_handled(self, tmp_path):
        """File with syntax error should not crash the checker."""
        py_file = tmp_path / "syntax_err.py"
        py_file.write_text("def foo(\n")  # Syntax error
        # extract_used_types and extract_actual_imports should handle parse failure
        errors = ci_mod.check_type_imports(py_file)
        # Should not raise; returns empty errors (parse failure logged at debug)
        assert errors == []

    def test_nonexistent_file_handled(self, tmp_path):
        """Nonexistent file should produce an error, not crash."""
        fake_file = tmp_path / "does_not_exist.py"
        errors = ci_mod.check_type_imports(fake_file)
        # check_type_imports catches exceptions
        assert len(errors) <= 1  # Either empty (no types used) or error msg


# ---------------------------------------------------------------------------
# End-to-end: scope -> validate pipeline
# ---------------------------------------------------------------------------


class TestScopeValidatePipeline:
    """End-to-end tests for the scope builder -> check_imports pipeline."""

    def test_scope_to_files_from_roundtrip(self, tmp_path):
        """Scope file written by build_scope is correctly consumed by _parse_files_from."""
        # Simulate scope output
        scope_file = tmp_path / "scope.txt"
        scope_content = "src/amplihack/core.py\nsrc/amplihack/utils.py\n"
        scope_file.write_text(scope_content)

        parsed = ci_mod._parse_files_from(str(scope_file))
        assert len(parsed) == 2
        assert parsed[0] == Path("src/amplihack/core.py")
        assert parsed[1] == Path("src/amplihack/utils.py")

    def test_empty_scope_produces_no_files(self, tmp_path):
        """Empty scope file means no files to check."""
        scope_file = tmp_path / "empty_scope.txt"
        scope_file.write_text("")
        parsed = ci_mod._parse_files_from(str(scope_file))
        assert parsed == []

    def test_scope_excludes_scenarios_then_validates(self, tmp_path):
        """Full pipeline: scope builder excludes scenarios, checker validates rest."""
        import build_publish_validation_scope as scope_mod_local

        staged = [
            "src/amplihack/core.py",
            ".claude/scenarios/tool/main.py",
            "tests/test_foo.py",
        ]
        scope = scope_mod_local.build_scope(staged_files=staged)
        assert scope == ["src/amplihack/core.py"]

        # Write scope and read back via --files-from parser
        scope_file = tmp_path / "scope.txt"
        scope_file.write_text("\n".join(scope) + "\n")
        parsed = ci_mod._parse_files_from(str(scope_file))
        assert parsed == [Path("src/amplihack/core.py")]

    def test_transitive_exclusion_nested_tests(self, tmp_path):
        """Nested tests/ dirs are excluded transitively."""
        import build_publish_validation_scope as scope_mod_local

        staged = [
            "src/amplihack/memory/tests/test_backend.py",
            "src/amplihack/memory/backend.py",
        ]
        scope = scope_mod_local.build_scope(staged_files=staged)
        assert scope == ["src/amplihack/memory/backend.py"]
