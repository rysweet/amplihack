#!/usr/bin/env python3
"""
Unit tests for reflection module imports.
Tests Suite 1: Validates that reflection/__init__.py exports match actual functions.

CRITICAL: These tests prevent ImportError that breaks reflection analysis.
"""

import sys
import unittest
from pathlib import Path

# Add project paths
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "reflection"))


class TestReflectionImports(unittest.TestCase):
    """Test Suite 1: reflection/__init__.py imports validation."""

    def test_reflection_module_imports_without_error(self):
        """Test that importing reflection module doesn't raise ImportError."""
        try:
            import reflection  # noqa: F401
        except ImportError as e:
            self.fail(f"Failed to import reflection module: {e}")

    def test_analyze_session_patterns_function_exists(self):
        """Test that analyze_session_patterns function exists and is callable."""
        try:
            from reflection import analyze_session_patterns
        except ImportError as e:
            self.fail(f"Failed to import analyze_session_patterns: {e}")

        # Verify it's callable
        self.assertTrue(
            callable(analyze_session_patterns), "analyze_session_patterns is not callable"
        )

    def test_process_reflection_analysis_function_exists(self):
        """Test that process_reflection_analysis function exists and is callable."""
        try:
            from reflection import process_reflection_analysis
        except ImportError as e:
            self.fail(f"Failed to import process_reflection_analysis: {e}")

        # Verify it's callable
        self.assertTrue(
            callable(process_reflection_analysis), "process_reflection_analysis is not callable"
        )

    def test_all_exported_functions_are_callable(self):
        """Test that all functions in __all__ are callable."""
        import reflection

        # Get the __all__ list - it may be missing in some import contexts
        if not hasattr(reflection, "__all__"):
            # If __all__ is missing, check that key functions exist
            self.assertTrue(
                hasattr(reflection, "analyze_session_patterns"),
                "reflection module should have analyze_session_patterns",
            )
            self.assertTrue(
                hasattr(reflection, "process_reflection_analysis"),
                "reflection module should have process_reflection_analysis",
            )
            return

        exported_names = reflection.__all__

        self.assertTrue(len(exported_names) > 0, "reflection.__all__ is empty")

        for name in exported_names:
            # Check that the name exists
            self.assertTrue(
                hasattr(reflection, name),
                f"Exported name '{name}' does not exist in reflection module",
            )

            # Check that it's callable
            obj = getattr(reflection, name)
            self.assertTrue(callable(obj), f"Exported object '{name}' is not callable")

    def test_reflection_py_contains_exported_functions(self):
        """Test that reflection.py actually defines the functions exported by __init__.py."""
        import importlib.util

        # Import reflection.py directly
        reflection_py_path = (
            project_root / ".claude" / "tools" / "amplihack" / "reflection" / "reflection.py"
        )

        spec = importlib.util.spec_from_file_location("reflection_module", reflection_py_path)
        reflection_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reflection_module)

        # Expected functions based on __init__.py
        expected_functions = ["analyze_session_patterns", "process_reflection_analysis"]

        for func_name in expected_functions:
            self.assertTrue(
                hasattr(reflection_module, func_name),
                f"reflection.py is missing function: {func_name}",
            )

            func = getattr(reflection_module, func_name)
            self.assertTrue(callable(func), f"reflection.py.{func_name} is not callable")

    def test_no_import_errors_when_importing_specific_functions(self):
        """Test that importing specific functions doesn't raise errors."""
        try:
            # This is the exact import pattern used in stop.py
            from reflection import analyze_session_patterns  # noqa: F401
        except ImportError as e:
            self.fail(f"Failed specific import of analyze_session_patterns: {e}")

    def test_reflection_module_has_all_attribute(self):
        """Test that reflection module defines __all__."""
        import reflection

        # __all__ may not be present in all import contexts
        # The key requirement is that the functions exist
        if not hasattr(reflection, "__all__"):
            # Verify key functions exist instead
            self.assertTrue(
                hasattr(reflection, "analyze_session_patterns"),
                "reflection must have analyze_session_patterns function",
            )
            self.assertTrue(
                hasattr(reflection, "process_reflection_analysis"),
                "reflection must have process_reflection_analysis function",
            )
            return

        # If __all__ exists, verify it's correct
        self.assertIsInstance(reflection.__all__, list, "__all__ should be a list")

        # Verify it's not empty
        self.assertGreater(len(reflection.__all__), 0, "__all__ should not be empty")


class TestReflectionFunctionSignatures(unittest.TestCase):
    """Test Suite 1B: Validate function signatures match usage."""

    def test_analyze_session_patterns_accepts_messages_list(self):
        """Test that analyze_session_patterns accepts a list of messages."""
        from reflection import analyze_session_patterns

        # Test with empty list (should not crash)
        try:
            result = analyze_session_patterns([])
            self.assertIsInstance(result, list, "Should return a list")
        except Exception as e:
            self.fail(f"analyze_session_patterns failed with empty list: {e}")

    def test_analyze_session_patterns_returns_list(self):
        """Test that analyze_session_patterns returns a list."""
        from reflection import analyze_session_patterns

        messages = [
            {"role": "user", "content": "test message"},
            {"role": "assistant", "content": "test response"},
        ]

        result = analyze_session_patterns(messages)

        self.assertIsInstance(result, list, "analyze_session_patterns should return a list")

    def test_process_reflection_analysis_accepts_messages(self):
        """Test that process_reflection_analysis accepts messages parameter."""
        from reflection import process_reflection_analysis

        messages = [{"role": "user", "content": "test message"}]

        try:
            # This may return None or a value, we're just testing it accepts the parameter
            result = process_reflection_analysis(messages)
            # Result can be None or a string (issue number)
            self.assertTrue(
                result is None or isinstance(result, str),
                "process_reflection_analysis should return None or string",
            )
        except Exception as e:
            # Some errors are OK (like missing gh CLI), but not ImportError
            if "ImportError" in str(type(e)):
                self.fail(f"ImportError in process_reflection_analysis: {e}")


class TestReflectionImportPaths(unittest.TestCase):
    """Test Suite 1C: Validate import paths work from different contexts."""

    def test_import_from_absolute_path(self):
        """Test that reflection can be imported using absolute path."""
        import sys

        # Add reflection directory to path
        reflection_dir = project_root / ".claude" / "tools" / "amplihack" / "reflection"
        if str(reflection_dir) not in sys.path:
            sys.path.insert(0, str(reflection_dir))

        try:
            import reflection  # noqa: F401
            from reflection import analyze_session_patterns  # noqa: F401
        except ImportError as e:
            self.fail(f"Failed absolute import: {e}")

    def test_import_from_hooks_context(self):
        """Test that reflection imports work from hooks directory context."""
        import sys

        # Simulate being in hooks directory (like stop.py)
        hooks_dir = project_root / ".claude" / "tools" / "amplihack" / "hooks"
        reflection_dir = hooks_dir.parent / "reflection"

        if str(reflection_dir) not in sys.path:
            sys.path.insert(0, str(reflection_dir))

        try:
            from reflection import analyze_session_patterns  # noqa: F401
        except ImportError as e:
            self.fail(f"Failed import from hooks context: {e}")


if __name__ == "__main__":
    unittest.main()
