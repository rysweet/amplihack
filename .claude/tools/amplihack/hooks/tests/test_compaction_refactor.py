#!/usr/bin/env python3
"""
Structural tests enforcing the compaction_validator.py refactor constraints (issue #2845).

These tests read source files directly and use AST analysis to verify that the
refactoring requirements are met without relying on runtime behaviour.

A  Line count ≤ 420 (was 523)
B  No object.__setattr__ in either file
C  import logging present in validator
D  logger = logging.getLogger present in validator
E  No silent `except … pass` blocks (AST-verified)
F  ≥ 3 logger.warning calls in validator
G  compaction_context.py exists
H  compaction_validator.py imports from compaction_context
I  __all__ re-exports CompactionContext and ValidationResult
J  No @dataclass class definitions in compaction_validator.py
K  Backward-compat imports resolve to the same class objects
Bonus  No redundant age_hours recomputation after CompactionContext()
"""

import ast
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
HOOKS_DIR = TESTS_DIR.parent

VALIDATOR_FILE = HOOKS_DIR / "compaction_validator.py"
CONTEXT_FILE = HOOKS_DIR / "compaction_context.py"

# Add hooks dir so we can do runtime import checks
sys.path.insert(0, str(HOOKS_DIR))


class TestLineCount(unittest.TestCase):
    """A: compaction_validator.py must be ≤ 420 lines (was 523)."""

    def test_validator_line_count_at_most_420(self):
        self.assertTrue(VALIDATOR_FILE.exists(), f"{VALIDATOR_FILE} not found")
        lines = VALIDATOR_FILE.read_text().splitlines()
        self.assertLessEqual(
            len(lines),
            420,
            f"compaction_validator.py has {len(lines)} lines, expected ≤ 420",
        )


class TestNoObjectSetattr(unittest.TestCase):
    """B: object.__setattr__ must not appear in either file."""

    def test_validator_has_no_object_setattr(self):
        self.assertTrue(VALIDATOR_FILE.exists())
        self.assertNotIn("object.__setattr__", VALIDATOR_FILE.read_text())

    def test_context_has_no_object_setattr(self):
        self.assertTrue(CONTEXT_FILE.exists())
        self.assertNotIn("object.__setattr__", CONTEXT_FILE.read_text())


class TestLoggingSetup(unittest.TestCase):
    """C + D: import logging and logger = logging.getLogger must be present in validator."""

    def test_import_logging_present(self):
        self.assertIn("import logging", VALIDATOR_FILE.read_text())

    def test_logger_getLogger_present(self):
        self.assertIn("logging.getLogger", VALIDATOR_FILE.read_text())


class TestNoSilentExcepts(unittest.TestCase):
    """E: No bare `except: pass` or `except SomeError: pass` blocks (AST-verified)."""

    @staticmethod
    def _find_silent_excepts(source: str) -> list[int]:
        """Return line numbers of except handlers whose entire body is `pass`."""
        tree = ast.parse(source)
        silent = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    silent.append(node.lineno)
        return silent

    def test_validator_has_no_silent_excepts(self):
        source = VALIDATOR_FILE.read_text()
        silent = self._find_silent_excepts(source)
        self.assertEqual(
            silent,
            [],
            f"Silent except…pass blocks found in validator at lines: {silent}",
        )

    def test_context_has_no_silent_excepts(self):
        source = CONTEXT_FILE.read_text()
        silent = self._find_silent_excepts(source)
        self.assertEqual(
            silent,
            [],
            f"Silent except…pass blocks found in context at lines: {silent}",
        )


class TestLoggerWarningCalls(unittest.TestCase):
    """F: validator must contain ≥ 3 logger.warning() calls."""

    def test_at_least_three_logger_warning_calls(self):
        source = VALIDATOR_FILE.read_text()
        count = source.count("logger.warning(")
        self.assertGreaterEqual(
            count,
            3,
            f"Expected ≥ 3 logger.warning calls in validator, found {count}",
        )


class TestCompactionContextFileExists(unittest.TestCase):
    """G: compaction_context.py must exist alongside compaction_validator.py."""

    def test_compaction_context_file_exists(self):
        self.assertTrue(
            CONTEXT_FILE.exists(),
            f"{CONTEXT_FILE} does not exist",
        )


class TestValidatorImportsFromContext(unittest.TestCase):
    """H: compaction_validator.py must import from compaction_context."""

    def test_validator_imports_from_compaction_context(self):
        source = VALIDATOR_FILE.read_text()
        self.assertIn(
            "from compaction_context import",
            source,
            "compaction_validator.py must import from compaction_context",
        )


class TestAllReExports(unittest.TestCase):
    """I: __all__ in compaction_validator.py must include CompactionContext and ValidationResult."""

    def test_all_contains_compaction_context(self):
        source = VALIDATOR_FILE.read_text()
        self.assertIn("CompactionContext", source)
        # Verify it's in __all__ by checking the module-level list
        self.assertIn('"CompactionContext"', source)

    def test_all_contains_validation_result(self):
        source = VALIDATOR_FILE.read_text()
        self.assertIn('"ValidationResult"', source)


class TestNoDataclassInValidator(unittest.TestCase):
    """J: @dataclass class bodies must NOT live in compaction_validator.py."""

    def test_no_dataclass_decorated_classes_in_validator(self):
        source = VALIDATOR_FILE.read_text()
        tree = ast.parse(source)
        dataclass_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for dec in node.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                        dec_name = dec.func.id
                    if dec_name == "dataclass":
                        dataclass_names.append(node.name)
        self.assertEqual(
            dataclass_names,
            [],
            f"@dataclass classes found in validator: {dataclass_names}",
        )


class TestBackwardCompatibility(unittest.TestCase):
    """K: `from compaction_validator import CompactionContext` must give the same object."""

    def test_compaction_context_is_same_object(self):
        from compaction_context import CompactionContext as CC_from_context
        from compaction_validator import CompactionContext as CC_from_validator

        self.assertIs(
            CC_from_validator,
            CC_from_context,
            "CompactionContext re-exported from validator must be identical to context module class",
        )

    def test_validation_result_is_same_object(self):
        from compaction_context import ValidationResult as VR_from_context
        from compaction_validator import ValidationResult as VR_from_validator

        self.assertIs(
            VR_from_validator,
            VR_from_context,
            "ValidationResult re-exported from validator must be identical to context module class",
        )


class TestNoRedundantAgeRecomputation(unittest.TestCase):
    """Bonus: validator must not recompute age_hours after CompactionContext() construction."""

    def test_no_redundant_age_hours_assignment(self):
        source = VALIDATOR_FILE.read_text()
        # The old code had `age_hours, is_stale = _parse_timestamp_age(...)` followed by
        # manual assignment — this must not exist in the validator anymore.
        self.assertNotIn(
            "context.age_hours =",
            source,
            "Redundant context.age_hours assignment found in validator",
        )
        self.assertNotIn(
            "age_hours, is_stale = _parse_timestamp_age",
            source,
            "Redundant _parse_timestamp_age call found in validator",
        )


if __name__ == "__main__":
    unittest.main()
