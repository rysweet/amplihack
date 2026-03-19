# File: src/amplihack/memory_auto_install.py
"""Guard for amplihack-memory-lib availability.

This module provides a lightweight import guard for the optional
amplihack-memory-lib package. It does NOT auto-install anything.

PEP 668 compliance: library code must never invoke pip or any
subprocess-based package installer. Users on externally-managed
Python environments (Debian/Ubuntu system Python, Homebrew Python, etc.)
cannot have packages injected by library code without their consent.

To install the memory extra, run the command shown in the ImportError
raised by ``ensure_memory_lib_installed()`` when the library is absent.
"""

from __future__ import annotations

import sys

# SEC-003: install hint is built from named constants so no dynamic runtime
# paths appear in user-visible messages (interpreter path, venv root, etc.).
# SEC-005: "pip" appears only inside the constant string, never as part of
# a subprocess-invocation pattern.
_PKG_MANAGER = "pip"  # name only — never passed to subprocess
_MEMORY_LIB_NAME = "amplihack-memory-lib"
_MEMORY_EXTRA = "amplihack[memory]"

_INSTALL_MSG = (
    f"amplihack memory features require the memory library.\n"
    f"Install it with: {_PKG_MANAGER} install {_MEMORY_EXTRA}\n"
    f"or: {_PKG_MANAGER} install {_MEMORY_LIB_NAME}"
)

# Module-level cache: None = not yet checked, True/False = cached result.
# Avoids rescanning sys.path on every call when the library is absent.
# O(1) on all repeat calls — avoids sys.path re-scan after first probe.
# TODO(free-threaded): Under PEP 703 / CPython free-threaded mode (--disable-gil),
# the GIL no longer protects this flag against concurrent writes. If free-threaded
# Python support is ever required, protect with threading.Lock.
_memory_available: bool | None = None


def ensure_memory_lib_installed() -> bool:
    """Check that amplihack-memory-lib is importable; raise if not.

    This function is a pure availability guard. It will never invoke
    pip, subprocess, or any other installer — doing so would break
    PEP 668 (externally managed Python environments) and constitutes
    a supply-chain risk (SEC-005).

    Returns:
        True if ``amplihack_memory`` is importable.

    Raises:
        ImportError: When ``amplihack_memory`` is not installed, with
            actionable install instructions. Raised with ``from None``
            (SEC-002) to suppress internal import-machinery tracebacks.
            The message never contains runtime paths or environment
            variables (SEC-003).

    Example::

        from amplihack.memory_auto_install import ensure_memory_lib_installed

        try:
            ensure_memory_lib_installed()
        except ImportError as exc:
            print(exc)  # shows install instructions
        else:
            from amplihack.memory import CognitiveMemory

    Caching: result is memoized after the first call (O(1) on repeat).
    """
    global _memory_available

    # Fast path 1: cached result from a previous call — O(1) dict read
    if _memory_available is True:
        return True
    if _memory_available is False:
        # SEC-002: raise ... from None suppresses the chained ImportError
        # so internal Python import-machinery paths are not leaked to users.
        raise ImportError(_INSTALL_MSG) from None

    # Fast path 2: already imported elsewhere — O(1) dict lookup, no disk I/O
    if "amplihack_memory" in sys.modules:
        _memory_available = True
        return True

    # First call: probe the import system once and cache the outcome.
    # sys.path is scanned exactly once per process lifetime.
    try:
        import amplihack_memory  # noqa: F401  # pyright: ignore[reportMissingImports]

        _memory_available = True
        return True
    except ImportError:
        _memory_available = False
        # SEC-002: raise ... from None suppresses the chained ImportError
        # so internal Python import-machinery paths are not leaked to users.
        raise ImportError(_INSTALL_MSG) from None
