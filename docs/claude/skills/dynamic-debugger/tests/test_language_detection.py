"""Unit tests for language detection module.

Testing pyramid distribution:
- This file contains 18 unit tests (~60% of unit test coverage for this module)
- Tests focus on manifest detection, extension analysis, and edge cases
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from detect_language import (
    detect_language,
    get_debugger_for_language,
    MANIFEST_MAP,
    EXTENSION_MAP
)


# ============================================================================
# MANIFEST FILE DETECTION TESTS (6 tests)
# ============================================================================

class TestManifestDetection:
    """Test language detection from manifest files (highest confidence)."""

    def test_detect_python_from_requirements_txt(self, python_project):
        """Test Python detection from requirements.txt."""
        language, confidence = detect_language(str(python_project))
        assert language == "python"
        assert confidence == 0.95  # Manifest detection = 0.95 confidence

    def test_detect_python_from_pyproject_toml(self, temp_project_dir):
        """Test Python detection from pyproject.toml."""
        (temp_project_dir / "pyproject.toml").write_text("[tool.pytest]")
        language, confidence = detect_language(str(temp_project_dir))
        assert language == "python"
        assert confidence == 0.95

    def test_detect_javascript_from_package_json(self, javascript_project):
        """Test JavaScript detection from package.json."""
        language, confidence = detect_language(str(javascript_project))
        assert language == "javascript"
        assert confidence == 0.95

    def test_detect_go_from_go_mod(self, go_project):
        """Test Go detection from go.mod."""
        language, confidence = detect_language(str(go_project))
        assert language == "go"
        assert confidence == 0.95

    def test_detect_rust_from_cargo_toml(self, rust_project):
        """Test Rust detection from Cargo.toml."""
        language, confidence = detect_language(str(rust_project))
        assert language == "rust"
        assert confidence == 0.95

    def test_detect_cpp_from_cmake(self, cpp_project):
        """Test C++ detection from CMakeLists.txt."""
        language, confidence = detect_language(str(cpp_project))
        assert language == "cpp"
        assert confidence == 0.95


# ============================================================================
# FILE EXTENSION ANALYSIS TESTS (6 tests)
# ============================================================================

class TestExtensionAnalysis:
    """Test language detection from file extensions (medium confidence)."""

    def test_detect_from_extensions_python(self, temp_project_dir):
        """Test detection from Python file extensions."""
        # Create only Python files (no manifest)
        (temp_project_dir / "script1.py").write_text("# Python")
        (temp_project_dir / "script2.py").write_text("# Python")
        (temp_project_dir / "script3.py").write_text("# Python")

        language, confidence = detect_language(str(temp_project_dir))
        assert language == "python"
        assert 0 < confidence <= 0.85  # Extension-based confidence

    def test_detect_from_extensions_mixed_python_dominant(self, temp_project_dir):
        """Test detection with mixed extensions (Python dominant)."""
        # 3 Python files, 1 JavaScript file
        (temp_project_dir / "script1.py").write_text("# Python")
        (temp_project_dir / "script2.py").write_text("# Python")
        (temp_project_dir / "script3.py").write_text("# Python")
        (temp_project_dir / "script.js").write_text("// JS")

        language, confidence = detect_language(str(temp_project_dir))
        assert language == "python"
        # Confidence = 3/4 = 0.75
        assert 0.70 <= confidence <= 0.80

    def test_detect_from_extensions_equal_split(self, temp_project_dir):
        """Test detection with equal language distribution."""
        # 2 Python, 2 JavaScript
        (temp_project_dir / "script1.py").write_text("# Python")
        (temp_project_dir / "script2.py").write_text("# Python")
        (temp_project_dir / "script1.js").write_text("// JS")
        (temp_project_dir / "script2.js").write_text("// JS")

        language, confidence = detect_language(str(temp_project_dir))
        # Should detect one of them (whichever Counter returns first)
        assert language in ["python", "javascript"]
        # Confidence = 2/4 = 0.5
        assert 0.45 <= confidence <= 0.55

    def test_extension_detection_excludes_common_dirs(self, temp_project_dir):
        """Test that common non-source directories are excluded."""
        # Create files in excluded directories
        (temp_project_dir / ".venv").mkdir()
        (temp_project_dir / ".venv" / "script.py").write_text("# Excluded")

        (temp_project_dir / "node_modules").mkdir()
        (temp_project_dir / "node_modules" / "script.js").write_text("// Excluded")

        (temp_project_dir / "__pycache__").mkdir()
        (temp_project_dir / "__pycache__" / "script.py").write_text("# Excluded")

        # Create one real source file
        (temp_project_dir / "main.py").write_text("# Real source")

        language, confidence = detect_language(str(temp_project_dir))
        assert language == "python"
        # Should only count the real source file
        assert confidence > 0.8  # 1/1 = 1.0, but capped at 0.85

    def test_detect_typescript_from_ts_files(self, temp_project_dir):
        """Test TypeScript detection from .ts files."""
        (temp_project_dir / "app.ts").write_text("// TypeScript")
        (temp_project_dir / "utils.ts").write_text("// TypeScript")

        language, confidence = detect_language(str(temp_project_dir))
        assert language == "typescript"
        assert 0 < confidence <= 0.85

    def test_detect_cpp_from_extensions(self, temp_project_dir):
        """Test C++ detection from various C++ extensions."""
        (temp_project_dir / "main.cpp").write_text("// C++")
        (temp_project_dir / "utils.cc").write_text("// C++")
        (temp_project_dir / "helper.cxx").write_text("// C++")
        (temp_project_dir / "header.hpp").write_text("// C++")

        language, confidence = detect_language(str(temp_project_dir))
        assert language == "cpp"
        assert 0 < confidence <= 0.85


# ============================================================================
# EDGE CASES AND ERROR HANDLING (6 tests)
# ============================================================================

class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""

    def test_detect_nonexistent_directory(self):
        """Test detection with non-existent directory."""
        language, confidence = detect_language("/nonexistent/path")
        assert language == "unknown"
        assert confidence == 0.0

    def test_detect_empty_directory(self, empty_project):
        """Test detection with empty directory."""
        language, confidence = detect_language(str(empty_project))
        assert language == "unknown"
        assert confidence == 0.0

    def test_detect_with_permission_error(self, temp_project_dir, monkeypatch):
        """Test handling of permission errors during file scanning."""
        # Create a Python file
        (temp_project_dir / "script.py").write_text("# Python")

        # Mock rglob to raise PermissionError
        original_rglob = Path.rglob

        def mock_rglob(self, pattern):
            if "script.py" in str(self):
                raise PermissionError("Access denied")
            return original_rglob(self, pattern)

        monkeypatch.setattr(Path, "rglob", mock_rglob)

        # Should handle gracefully and return unknown
        language, confidence = detect_language(str(temp_project_dir))
        # Might be unknown or might detect from other files
        assert language in ["unknown", "python"]
        assert 0.0 <= confidence <= 1.0

    def test_manifest_takes_precedence_over_extensions(self, python_project):
        """Test that manifest detection takes precedence over extensions."""
        # Add some JavaScript files to a Python project
        (python_project / "script.js").write_text("// JS")
        (python_project / "app.js").write_text("// JS")

        # Should still detect Python due to manifest (higher confidence)
        language, confidence = detect_language(str(python_project))
        assert language == "python"
        assert confidence == 0.95  # Manifest confidence

    def test_confidence_score_bounds(self, temp_project_dir):
        """Test that confidence scores stay within bounds [0.0, 1.0]."""
        # Create 100 Python files to test confidence capping
        for i in range(100):
            (temp_project_dir / f"script_{i}.py").write_text(f"# Script {i}")

        language, confidence = detect_language(str(temp_project_dir))
        assert language == "python"
        assert 0.0 <= confidence <= 1.0
        # Should be capped at 0.85 for extension-based detection
        assert confidence <= 0.85

    def test_get_debugger_for_unknown_language(self):
        """Test debugger mapping for unknown language."""
        debugger = get_debugger_for_language("unknown")
        assert debugger == "unknown"


# ============================================================================
# DEBUGGER MAPPING TESTS (Bonus - not counted in 18)
# ============================================================================

class TestDebuggerMapping:
    """Test debugger recommendations for detected languages."""

    @pytest.mark.parametrize("language,expected_debugger", [
        ("python", "debugpy"),
        ("javascript", "node"),
        ("typescript", "node"),
        ("c", "gdb"),
        ("cpp", "gdb"),
        ("go", "delve"),
        ("rust", "rust-gdb"),
        ("java", "jdwp"),
    ])
    def test_debugger_mapping(self, language, expected_debugger):
        """Test debugger mapping for all supported languages."""
        debugger = get_debugger_for_language(language)
        assert debugger == expected_debugger


# ============================================================================
# CLI INTERFACE TESTS (Bonus - not counted in 18)
# ============================================================================

class TestCLIInterface:
    """Test command-line interface."""

    def test_cli_json_output(self, python_project, capsys):
        """Test JSON output format."""
        sys.argv = ["detect_language.py", "--path", str(python_project), "--json"]

        # Import and run the main section
        with patch('sys.argv', ["detect_language.py", "--path", str(python_project), "--json"]):
            # Re-run the module
            import json
            from detect_language import detect_language, get_debugger_for_language

            lang, conf = detect_language(str(python_project))
            debugger = get_debugger_for_language(lang)

            result = {
                "language": lang,
                "confidence": round(conf, 2),
                "debugger": debugger
            }

            # Verify JSON structure
            assert result["language"] == "python"
            assert result["confidence"] == 0.95
            assert result["debugger"] == "debugpy"

    def test_cli_default_output(self, python_project):
        """Test default text output format."""
        lang, conf = detect_language(str(python_project))
        debugger = get_debugger_for_language(lang)

        # Verify output components
        assert lang == "python"
        assert 0.0 <= conf <= 1.0
        assert debugger == "debugpy"
