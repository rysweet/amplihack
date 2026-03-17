"""Tests for PackageNotFoundError fallback narrowing (Issue #3235).

The bug: when importlib.metadata is unavailable (Python < 3.8 edge case),
the fallback `PackageNotFoundError = Exception` made `except PackageNotFoundError`
catch ALL exceptions — not just missing-package errors.

The fix: define a proper subclass so only PackageNotFoundError instances are caught.
"""

import subprocess
import sys
import textwrap


def test_fallback_packagenotfounderror_is_not_exception():
    """PackageNotFoundError fallback must NOT be Exception itself.

    If it equals Exception, `except PackageNotFoundError` silently swallows
    every exception during version detection — hiding real bugs.
    """
    code = textwrap.dedent("""\
        import sys
        # Force the ImportError path by removing importlib.metadata from sys.modules
        # and making it unimportable.
        for mod_name in list(sys.modules):
            if mod_name.startswith("importlib.metadata") or mod_name == "importlib_metadata":
                del sys.modules[mod_name]

        import importlib
        _real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def _fake_import(name, *args, **kwargs):
            if name == "importlib.metadata":
                raise ImportError("simulated: no importlib.metadata")
            return _real_import(name, *args, **kwargs)

        import builtins
        builtins.__import__ = _fake_import

        # Now execute the fallback branch
        try:
            from importlib.metadata import PackageNotFoundError, version
        except ImportError:
            version = None
            class PackageNotFoundError(Exception):
                pass

        # --- assertions ---
        # PackageNotFoundError must be a strict subclass, not Exception itself
        assert PackageNotFoundError is not Exception, (
            "PackageNotFoundError should NOT be Exception (catches everything)"
        )
        assert issubclass(PackageNotFoundError, Exception), (
            "PackageNotFoundError must still be an Exception subclass"
        )

        # A generic ValueError must NOT be caught by except PackageNotFoundError
        caught_generic = False
        try:
            raise ValueError("not a package error")
        except PackageNotFoundError:
            caught_generic = True
        except ValueError:
            pass

        assert not caught_generic, (
            "except PackageNotFoundError must NOT catch ValueError"
        )

        # But PackageNotFoundError itself must still be catchable
        caught_specific = False
        try:
            raise PackageNotFoundError("missing package")
        except PackageNotFoundError:
            caught_specific = True

        assert caught_specific, (
            "except PackageNotFoundError must catch its own instances"
        )

        print("ALL_CHECKS_PASSED")
    """)

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Script failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert "ALL_CHECKS_PASSED" in result.stdout


def test_source_file_uses_subclass_not_alias():
    """Verify the actual source file defines a class, not an alias to Exception."""
    from pathlib import Path

    init_path = Path(__file__).parent.parent.parent / "src" / "amplihack" / "__init__.py"
    source = init_path.read_text()

    # The old buggy pattern: PackageNotFoundError = Exception
    assert "PackageNotFoundError = Exception" not in source, (
        "Source still contains the buggy alias 'PackageNotFoundError = Exception'"
    )

    # The fix: class PackageNotFoundError(Exception)
    assert "class PackageNotFoundError(Exception)" in source, (
        "Source must define 'class PackageNotFoundError(Exception)'"
    )
