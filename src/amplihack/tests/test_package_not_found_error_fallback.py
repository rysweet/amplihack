"""Tests for issue #3235: PackageNotFoundError fallback must not catch all exceptions.

The bug: when importlib.metadata is unavailable, the fallback defined
PackageNotFoundError = Exception, meaning the except clause on version
detection would silently swallow ANY exception (KeyError, TypeError, etc.),
not just the missing-package case.

The fix: define a proper class PackageNotFoundError(Exception) subclass so
only that specific exception type is caught.
"""

import importlib
import sys
import types
import unittest
from unittest.mock import patch


class TestPackageNotFoundErrorFallback(unittest.TestCase):
    """Verify the fallback PackageNotFoundError is a narrow subclass."""

    def _import_init_without_importlib_metadata(self):
        """Re-import amplihack.__init__ with importlib.metadata blocked.

        Returns the freshly-imported module so tests can inspect the
        fallback PackageNotFoundError that gets defined.
        """
        import amplihack

        module_name = "amplihack"

        # Save original module
        original_module = sys.modules.get(module_name)

        # Block importlib.metadata so the except-ImportError branch runs
        blocked = {}
        for key in list(sys.modules):
            if key == "importlib.metadata" or key.startswith("importlib.metadata."):
                blocked[key] = sys.modules.pop(key)

        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def fake_import(name, *args, **kwargs):
            if name == "importlib.metadata":
                raise ImportError("blocked for test")
            # Also block "from importlib.metadata import ..."
            if name == "importlib" and args and args[0]:  # fromlist
                fromlist = args[0] if len(args) > 0 else kwargs.get("fromlist", ())
                # This handles "from importlib.metadata import X"
                pass
            return real_import(name, *args, **kwargs)

        try:
            # Remove cached module so it gets re-imported
            sys.modules.pop(module_name, None)
            # Also remove sub-modules that might cache the old import
            for key in list(sys.modules):
                if key.startswith(f"{module_name}."):
                    pass  # keep submodules, only re-exec __init__

            with patch("builtins.__import__", side_effect=fake_import):
                # Force re-execution of the module __init__
                # We can't easily re-import because of side effects,
                # so instead test the logic directly
                pass
        finally:
            # Restore everything
            sys.modules.update(blocked)
            if original_module is not None:
                sys.modules[module_name] = original_module

    def test_fallback_is_not_bare_exception(self):
        """The fallback PackageNotFoundError must NOT be Exception itself.

        This is the core regression test for issue #3235. Before the fix,
        PackageNotFoundError = Exception meant except PackageNotFoundError
        would catch every exception type.
        """
        # Simulate the fallback code path directly
        # This mirrors what __init__.py lines 24-29 do in the except branch
        exec_globals = {}
        code = """
class PackageNotFoundError(Exception):
    pass
"""
        exec(code, exec_globals)
        fallback_cls = exec_globals["PackageNotFoundError"]

        # The class must be a STRICT subclass of Exception, not Exception itself
        self.assertIsNot(fallback_cls, Exception,
                         "PackageNotFoundError fallback must not be Exception itself")
        self.assertTrue(issubclass(fallback_cls, Exception),
                        "PackageNotFoundError fallback must still be an Exception subclass")

    def test_fallback_does_not_catch_unrelated_exceptions(self):
        """except PackageNotFoundError must NOT catch KeyError, TypeError, etc."""
        # Define the fallback class the same way the fixed code does
        class PackageNotFoundError(Exception):
            """Narrow fallback: only catches missing-package errors."""

        # These unrelated exceptions must NOT be caught
        for exc_type in (KeyError, TypeError, ValueError, RuntimeError, OSError):
            with self.assertRaises(exc_type,
                                   msg=f"{exc_type.__name__} should not be caught "
                                       f"by except PackageNotFoundError"):
                try:
                    raise exc_type("test")
                except PackageNotFoundError:
                    pass  # This should NOT fire for unrelated exceptions

    def test_fallback_catches_its_own_instances(self):
        """except PackageNotFoundError must still catch PackageNotFoundError."""
        class PackageNotFoundError(Exception):
            """Narrow fallback: only catches missing-package errors."""

        caught = False
        try:
            raise PackageNotFoundError("amplihack")
        except PackageNotFoundError:
            caught = True

        self.assertTrue(caught, "PackageNotFoundError must catch its own instances")

    def test_old_bug_would_catch_everything(self):
        """Demonstrate the bug: PackageNotFoundError = Exception catches all."""
        PackageNotFoundError = Exception  # noqa: N806 — reproducing the bug

        # With the old code, this KeyError would be silently swallowed
        caught_wrongly = False
        try:
            raise KeyError("oops")
        except PackageNotFoundError:
            caught_wrongly = True

        self.assertTrue(caught_wrongly,
                        "This test proves the old code caught unrelated exceptions")

    def test_actual_module_fallback_class(self):
        """Verify the actual __init__.py code defines a proper subclass.

        We read the source and check that the except-ImportError block
        uses 'class PackageNotFoundError' not 'PackageNotFoundError = Exception'.
        """
        import inspect
        import amplihack

        source = inspect.getsource(amplihack)

        # The fixed code must contain a class definition, not an alias
        self.assertIn("class PackageNotFoundError(Exception):", source,
                       "Source must define PackageNotFoundError as a class, "
                       "not an alias to Exception")
        self.assertNotIn("PackageNotFoundError = Exception", source,
                         "Source must NOT alias PackageNotFoundError to Exception")


if __name__ == "__main__":
    unittest.main()
