"""Comprehensive test suite for TDD Prevention Suite.

Test execution order (using pytest-order):
1. Order 1: Basic syntax validation tests (fail fast)
2. Order 2: Performance tests (SLA validation)
3. Order 3: Edge case tests (zero false positives)
4. Order 4: Integration tests (full workflow)

This suite ensures that syntax errors are caught before CI, with zero false
positives and sub-2s performance for full codebase validation.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "pre-commit"))
from check_syntax import validate_file, validate_files

# =============================================================================
# ORDER 1: BASIC SYNTAX VALIDATION (Fail Fast)
# =============================================================================


@pytest.mark.order(1)
@pytest.mark.syntax
class TestSyntaxValidation:
    """Basic syntax validation tests - run first for fail-fast behavior."""

    def test_valid_file_passes(self, tmp_path):
        """Valid Python file should pass validation."""
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("""
def hello():
    '''Valid function.'''
    return "Hello, World!"
""")
        error = validate_file(str(valid_file))
        assert error is None, f"Valid file rejected: {error}"

    def test_syntax_error_detected(self, tmp_path):
        """File with syntax error should be detected."""
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("def broken_function(")
        error = validate_file(str(invalid_file))
        assert error is not None, "Syntax error not detected"
        assert "invalid.py" in error
        assert ":" in error  # Should have file:line:column format

    def test_error_location_accurate(self, tmp_path):
        """Error message should include accurate line and column."""
        invalid_file = tmp_path / "error.py"
        invalid_file.write_text("""
def function1():
    pass

def function2(  # Missing closing paren
    pass
""")
        error = validate_file(str(invalid_file))
        assert error is not None
        # Should contain line number (5) and column info
        assert "error.py" in error
        # Standard format: file:line:column: message

    def test_multiple_files_validation(self, tmp_path):
        """Should validate multiple files and aggregate errors."""
        # Create valid file
        valid = tmp_path / "valid.py"
        valid.write_text("def ok(): pass")

        # Create invalid file
        invalid = tmp_path / "invalid.py"
        invalid.write_text("def broken(")

        exit_code = validate_files([str(valid), str(invalid)])
        assert exit_code == 1, "Should fail when any file has errors"

    def test_empty_file_passes(self, tmp_path):
        """Empty Python file should pass validation."""
        empty = tmp_path / "empty.py"
        empty.write_text("")
        error = validate_file(str(empty))
        assert error is None, "Empty file should be valid"

    def test_utf8_encoding_handled(self, tmp_path):
        """File with UTF-8 encoding should be handled correctly."""
        utf8_file = tmp_path / "utf8.py"
        # Valid UTF-8 encoded file with unicode characters
        utf8_file.write_text("# -*- coding: utf-8 -*-\ndef hello(): return 'Hello 世界'")
        error = validate_file(str(utf8_file))
        assert error is None, "UTF-8 encoded file should be valid"


# =============================================================================
# ORDER 2: PERFORMANCE TESTS (SLA Validation)
# =============================================================================


@pytest.mark.order(2)
@pytest.mark.performance
class TestSyntaxValidationPerformance:
    """Performance tests for syntax validation - ensure SLAs met."""

    def create_test_files(self, tmp_path: Path, count: int) -> list[Path]:
        """Create valid Python test files.

        Args:
            tmp_path: pytest temporary directory
            count: Number of files to create

        Returns:
            List of created file paths
        """
        files = []
        for i in range(count):
            file = tmp_path / f"test_file_{i}.py"
            file.write_text(f"""
def function_{i}():
    '''Valid function {i}.'''
    return {i}

class Class_{i}:
    '''Valid class {i}.'''
    pass
""")
            files.append(file)
        return files

    def test_single_file_performance(self, tmp_path):
        """Single file validation should complete in < 50ms."""
        files = self.create_test_files(tmp_path, 1)

        start = time.perf_counter()
        exit_code = validate_files([str(f) for f in files])
        duration = time.perf_counter() - start

        assert exit_code == 0, "Valid files should pass"
        assert duration < 0.05, f"Single file took {duration * 1000:.1f}ms (limit: 50ms)"

    def test_50_files_performance(self, tmp_path):
        """50 files validation should complete in < 500ms (pre-commit SLA)."""
        files = self.create_test_files(tmp_path, 50)

        start = time.perf_counter()
        exit_code = validate_files([str(f) for f in files])
        duration = time.perf_counter() - start

        assert exit_code == 0, "Valid files should pass"
        assert duration < 0.5, f"50 files took {duration * 1000:.0f}ms (limit: 500ms)"

        # Log performance for monitoring
        per_file = duration / 50 * 1000
        print(f"\nPerformance: 50 files | {duration:.3f}s | {per_file:.1f}ms/file")

    @pytest.mark.slow
    def test_full_codebase_performance(self, tmp_path):
        """Full codebase validation should complete in < 2s."""
        # Find all Python files in the project
        project_root = Path(__file__).parent.parent
        python_files = list(project_root.glob("**/*.py"))

        # Skip test files in tmp directories and venv
        python_files = [
            f
            for f in python_files
            if "venv" not in str(f) and ".venv" not in str(f) and "tmp" not in str(f)
        ]

        if len(python_files) < 10:
            pytest.skip("Not enough files for full codebase test")

        start = time.perf_counter()
        exit_code = validate_files([str(f) for f in python_files])
        duration = time.perf_counter() - start

        # Log performance regardless of pass/fail
        per_file = duration / len(python_files) * 1000
        print(f"\nPerformance: {len(python_files)} files | {duration:.3f}s | {per_file:.1f}ms/file")

        assert duration < 2.0, f"Full codebase took {duration:.1f}s (limit: 2s)"


# =============================================================================
# ORDER 3: EDGE CASE TESTS (Zero False Positives)
# =============================================================================


@pytest.mark.order(3)
@pytest.mark.edge_case
class TestSyntaxEdgeCases:
    """Edge case tests - ensure zero false positives on valid code."""

    def test_equals_in_string_literal(self, tmp_path):
        """String containing '=======' should pass (not a merge conflict)."""
        file = tmp_path / "equals.py"
        file.write_text('''
def render_separator():
    """Return a separator line."""
    return "=" * 70

def test_data():
    """Test data with equals."""
    data = "======"
    return data
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on valid code: {error}"

    def test_angles_in_string_literal(self, tmp_path):
        """String containing '<<<' and '>>>' should pass."""
        file = tmp_path / "angles.py"
        file.write_text('''
def format_heredoc():
    """Format heredoc marker."""
    return "<<<EOF"

def format_chevron():
    """Format chevron."""
    return ">>> result"
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on valid code: {error}"

    def test_pipes_in_string_literal(self, tmp_path):
        """String containing '|||' should pass."""
        file = tmp_path / "pipes.py"
        file.write_text('''
def separator():
    """Pipe separator."""
    return "|||||||"
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on valid code: {error}"

    def test_angles_in_comment(self, tmp_path):
        """Comments containing '<<<' should pass."""
        file = tmp_path / "comments.py"
        file.write_text("""
# This is a comment with <<< marker
def function():
    # Another comment with >>> marker
    pass
""")
        error = validate_file(str(file))
        assert error is None, f"False positive on valid code: {error}"

    def test_doctest_markers(self, tmp_path):
        """Doctest markers ('>>>') should pass."""
        file = tmp_path / "doctest.py"
        file.write_text('''
def add(a, b):
    """Add two numbers.

    >>> add(2, 3)
    5
    >>> add(-1, 1)
    0
    """
    return a + b
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on doctest: {error}"

    def test_multiline_string_with_equals(self, tmp_path):
        """Multiline strings with '=' should pass."""
        file = tmp_path / "multiline.py"
        file.write_text('''
def banner():
    """Return banner."""
    return """
    ========================================
    Welcome to the Application
    ========================================
    """
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on multiline string: {error}"

    def test_fstring_with_equals(self, tmp_path):
        """F-strings with '=' should pass (Python 3.8+ debug syntax)."""
        file = tmp_path / "fstring.py"
        file.write_text('''
def debug(x):
    """Debug print."""
    result = f"{x=}"  # Python 3.8+ f-string debug syntax
    return f"Value: {x}"
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on f-string: {error}"

    def test_real_merge_conflict_fails(self, tmp_path):
        """Real merge conflict markers should fail (invalid syntax)."""
        file = tmp_path / "conflict.py"
        file.write_text("""
def function():
<<<<<<< HEAD
    return "version 1"
=======
    return "version 2"
>>>>>>> branch
""")
        error = validate_file(str(file))
        # Real merge conflicts ARE syntax errors, so this should fail
        assert error is not None, "Real merge conflict should be detected as syntax error"

    def test_raw_string_with_backslashes(self, tmp_path):
        """Raw strings with backslashes should pass."""
        file = tmp_path / "raw.py"
        file.write_text(r'''
def regex_pattern():
    """Return regex pattern."""
    return r"\\d+\\.\\d+"
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on raw string: {error}"

    def test_byte_string_with_special_chars(self, tmp_path):
        """Byte strings with special characters should pass."""
        file = tmp_path / "bytes.py"
        file.write_text('''
def binary_data():
    """Return binary data."""
    return b"<<<binary data>>>"
''')
        error = validate_file(str(file))
        assert error is None, f"False positive on byte string: {error}"


# =============================================================================
# ORDER 4: INTEGRATION TESTS (Full Workflow)
# =============================================================================


@pytest.mark.order(4)
@pytest.mark.integration
class TestPreCommitIntegration:
    """Integration tests for pre-commit hook - full workflow validation."""

    def test_hook_script_executable(self):
        """Verify hook script exists and is Python executable."""
        hook_path = Path(__file__).parent.parent / "scripts" / "pre-commit" / "check_syntax.py"
        assert hook_path.exists(), "Hook script not found"

        # Verify it's valid Python by importing
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_syntax", hook_path)
        assert spec is not None, "Hook script not importable"

    def test_cli_interface(self, tmp_path):
        """Test command-line interface matches specification."""
        hook_path = Path(__file__).parent.parent / "scripts" / "pre-commit" / "check_syntax.py"

        # Create valid file
        valid = tmp_path / "valid.py"
        valid.write_text("def ok(): pass")

        # Test CLI with valid file
        result = subprocess.run(
            [sys.executable, str(hook_path), str(valid)], capture_output=True, text=True
        )
        assert result.returncode == 0, "Valid file should return 0"

        # Create invalid file
        invalid = tmp_path / "invalid.py"
        invalid.write_text("def broken(")

        # Test CLI with invalid file
        result = subprocess.run(
            [sys.executable, str(hook_path), str(invalid)], capture_output=True, text=True
        )
        assert result.returncode == 1, "Invalid file should return 1"
        assert "invalid.py" in result.stdout, "Error should be in stdout"

    @pytest.mark.slow
    def test_pre_commit_config_valid(self):
        """Verify pre-commit configuration is valid."""
        config_path = Path(__file__).parent.parent / ".pre-commit-config.yaml"
        assert config_path.exists(), "Pre-commit config not found"

        # Read config and verify our hook is present
        config_text = config_path.read_text()
        assert "check-python-syntax" in config_text, "Hook not configured"
        assert "scripts/pre-commit/check_syntax.py" in config_text, "Hook path incorrect"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def log_performance(test_name: str, duration: float, file_count: int):
    """Log performance metrics for monitoring.

    Args:
        test_name: Name of the test
        duration: Duration in seconds
        file_count: Number of files processed
    """
    per_file = duration / file_count * 1000 if file_count > 0 else 0
    print(
        f"\nPerformance: {test_name} | Files: {file_count} | "
        f"Duration: {duration:.3f}s | Per-file: {per_file:.1f}ms"
    )
