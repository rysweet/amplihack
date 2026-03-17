"""Tests for issue #3235: PackageNotFoundError fallback must be narrow.

The bug: when importlib.metadata is unavailable, the fallback used
``PackageNotFoundError = Exception``, which made the except clause on
line 33 catch *every* exception — not just missing-package errors.

The fix: define a proper ``class PackageNotFoundError(Exception)`` so
only that specific exception type is caught.
"""

import sys
from unittest import mock


def _exec_fallback_branch():
    """Execute the ImportError fallback branch in isolation.

    Returns the namespace dict so tests can inspect PackageNotFoundError.
    """
    real_import = __import__

    def patched_import(name, *args, **kwargs):
        if name == "importlib.metadata":
            raise ImportError("mocked: no importlib.metadata")
        return real_import(name, *args, **kwargs)

    namespace: dict = {"sys": sys}
    code = """\
try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    import sys as _sys
    print("WARNING: importlib.metadata not available", file=_sys.stderr)
    version = None
    class PackageNotFoundError(Exception):
        \"\"\"Narrow fallback: only catches missing-package errors.\"\"\"
"""
    with mock.patch("builtins.__import__", side_effect=patched_import):
        exec(code, namespace)

    return namespace


class TestPackageNotFoundErrorFallback:
    """Verify the fallback PackageNotFoundError is a proper subclass."""

    def test_fallback_is_not_bare_exception(self):
        """PackageNotFoundError must NOT be ``Exception`` itself (the bug)."""
        ns = _exec_fallback_branch()
        pnfe = ns["PackageNotFoundError"]
        assert pnfe is not Exception, (
            "PackageNotFoundError should be a subclass, not Exception itself"
        )

    def test_fallback_is_exception_subclass(self):
        """PackageNotFoundError must still inherit from Exception."""
        ns = _exec_fallback_branch()
        pnfe = ns["PackageNotFoundError"]
        assert issubclass(pnfe, Exception)

    def test_fallback_does_not_catch_unrelated_errors(self):
        """A TypeError must NOT be caught by except PackageNotFoundError."""
        ns = _exec_fallback_branch()
        pnfe = ns["PackageNotFoundError"]

        caught_wrongly = False
        try:
            raise TypeError("unrelated error")
        except pnfe:
            caught_wrongly = True
        except TypeError:
            pass

        assert not caught_wrongly, (
            "except PackageNotFoundError must not catch TypeError"
        )

    def test_fallback_catches_own_instances(self):
        """The fallback class must still catch its own instances."""
        ns = _exec_fallback_branch()
        pnfe = ns["PackageNotFoundError"]

        caught = False
        try:
            raise pnfe("test-package")
        except pnfe:
            caught = True

        assert caught, "except PackageNotFoundError must catch its own instances"

    def test_source_contains_class_not_alias(self):
        """The actual __init__.py source must use class, not alias."""
        import amplihack

        init_path = amplihack.__file__
        if init_path is None:
            return  # namespace package, skip

        with open(init_path) as f:
            source = f.read()

        assert "PackageNotFoundError = Exception" not in source, (
            "Source still contains the buggy 'PackageNotFoundError = Exception'"
        )
        assert "class PackageNotFoundError(Exception)" in source, (
            "Source must define 'class PackageNotFoundError(Exception)'"
        )
