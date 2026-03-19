"""Tests: ensure_memory_lib_installed() never invokes pip/subprocess.

Issue #3327 — amplihack import eagerly auto-installs amplihack-memory-lib.
The fix removes all subprocess/pip invocations; this suite guards against
regression.

Design note:
- subprocess.run / Popen are patched to assert-fail on any call
- importlib.reload resets the module-level cache between tests
- The happy-path uses sys.modules injection (no real install needed)
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORKTREE_MODULE = "amplihack.memory_auto_install"


def _reload_module():
    """Reload memory_auto_install, resetting the _memory_available cache."""
    import amplihack.memory_auto_install as mod

    mod._memory_available = None  # reset sentinel without full reload
    return mod


def _raise_if_called(*args, **kwargs):
    """Side-effect that fails the test if subprocess is invoked."""
    raise AssertionError(
        f"subprocess must not be called — got args={args!r} kwargs={kwargs!r}"
    )


# ---------------------------------------------------------------------------
# Core guarantee: no subprocess calls regardless of library availability
# ---------------------------------------------------------------------------


class TestNoSubprocessCalls:
    """ensure_memory_lib_installed() must never fork a subprocess."""

    def test_library_absent_no_subprocess(self):
        """ImportError is raised cleanly without touching subprocess."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = None

        with (
            patch("subprocess.run", side_effect=_raise_if_called),
            patch("subprocess.Popen", side_effect=_raise_if_called),
            patch.dict(sys.modules, {"amplihack_memory": None}),
        ):
            # Remove from sys.modules so import attempt runs
            sys.modules.pop("amplihack_memory", None)
            # Patch the import to fail
            with patch.dict(sys.modules, {}):
                # Simulate missing library by making the import fail
                import builtins

                real_import = builtins.__import__

                def _fail_memory_import(name, *args, **kwargs):
                    if name == "amplihack_memory":
                        raise ImportError("mocked missing")
                    return real_import(name, *args, **kwargs)

                mod._memory_available = None
                with patch("builtins.__import__", side_effect=_fail_memory_import):
                    with pytest.raises(ImportError, match="pip install amplihack"):
                        mod.ensure_memory_lib_installed()

    def test_library_present_no_subprocess(self):
        """When library is available, returns True without touching subprocess."""
        import amplihack.memory_auto_install as mod

        # Inject a dummy module so the import succeeds
        dummy = type(sys)("amplihack_memory")
        mod._memory_available = None

        with (
            patch("subprocess.run", side_effect=_raise_if_called),
            patch("subprocess.Popen", side_effect=_raise_if_called),
            patch.dict(sys.modules, {"amplihack_memory": dummy}),
        ):
            result = mod.ensure_memory_lib_installed()

        assert result is True


# ---------------------------------------------------------------------------
# Caching correctness
# ---------------------------------------------------------------------------


class TestCaching:
    """Module-level _memory_available cache must work correctly."""

    def test_cached_true_skips_import(self):
        """Second call with cached True returns immediately."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = True
        # If import machinery ran, it would hit the real sys.modules lookup
        # — we verify by asserting no side-effects needed
        result = mod.ensure_memory_lib_installed()
        assert result is True

    def test_cached_false_raises_immediately(self):
        """Second call with cached False raises without re-scanning sys.path."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = False
        with pytest.raises(ImportError, match="pip install amplihack"):
            mod.ensure_memory_lib_installed()

    def test_sys_modules_fast_path(self):
        """If amplihack_memory is in sys.modules, returns True without import."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = None
        dummy = type(sys)("amplihack_memory")

        with patch.dict(sys.modules, {"amplihack_memory": dummy}):
            result = mod.ensure_memory_lib_installed()

        assert result is True
        assert mod._memory_available is True

    def test_cache_set_on_success(self):
        """_memory_available is set True after first successful check."""
        import amplihack.memory_auto_install as mod

        dummy = type(sys)("amplihack_memory")
        mod._memory_available = None

        with patch.dict(sys.modules, {"amplihack_memory": dummy}):
            mod.ensure_memory_lib_installed()

        assert mod._memory_available is True

    def test_cache_set_on_failure(self):
        """_memory_available is set False after first failed check."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = None
        sys.modules.pop("amplihack_memory", None)

        import builtins

        real_import = builtins.__import__

        def _fail(name, *args, **kwargs):
            if name == "amplihack_memory":
                raise ImportError("mocked missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fail):
            with pytest.raises(ImportError):
                mod.ensure_memory_lib_installed()

        assert mod._memory_available is False


# ---------------------------------------------------------------------------
# Error message quality
# ---------------------------------------------------------------------------


class TestErrorMessage:
    """ImportError must contain actionable install instructions."""

    def test_error_contains_pip_install_command(self):
        """Error message includes the pip install command."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = False
        with pytest.raises(ImportError) as exc_info:
            mod.ensure_memory_lib_installed()

        msg = str(exc_info.value)
        assert "pip install amplihack[memory]" in msg

    def test_error_contains_fallback_install(self):
        """Error message includes the direct package install fallback."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = False
        with pytest.raises(ImportError) as exc_info:
            mod.ensure_memory_lib_installed()

        msg = str(exc_info.value)
        assert "amplihack-memory-lib" in msg

    def test_error_suppresses_context(self):
        """raise ... from None suppresses the original ImportError context."""
        import amplihack.memory_auto_install as mod

        mod._memory_available = False
        with pytest.raises(ImportError) as exc_info:
            mod.ensure_memory_lib_installed()

        assert exc_info.value.__suppress_context__ is True

    def test_no_subprocess_source_code(self):
        """Module source must not contain subprocess invocations."""
        import inspect

        import amplihack.memory_auto_install as mod

        source = inspect.getsource(mod)
        forbidden = ["subprocess.run", "subprocess.Popen", "sys.executable"]
        for pattern in forbidden:
            assert pattern not in source, (
                f"memory_auto_install.py must not contain {pattern!r}"
            )
