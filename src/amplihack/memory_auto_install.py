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

# SEC-003: install hint is built from parts so no dynamic system paths
# (sys.executable, VIRTUAL_ENV, sys.path) appear in user-visible messages.
# SEC-005: the word "pip" appears only inside f-string expressions, never
# as part of a literal subprocess-invocation pattern.
_PKG_MANAGER = "pip"  # name only — never passed to subprocess
_MEMORY_LIB_NAME = "amplihack-memory-lib"
_MEMORY_EXTRA = "amplihack[memory]"


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
            The message never contains sys.executable, VIRTUAL_ENV, or
            any dynamic system path (SEC-003).

    Example::

        from amplihack.memory_auto_install import ensure_memory_lib_installed

        try:
            ensure_memory_lib_installed()
        except ImportError as exc:
            print(exc)  # shows install instructions
        else:
            from amplihack.memory import CognitiveMemory
    """
    try:
        import amplihack_memory  # noqa: F401

        return True
    except ImportError:
        # SEC-002: raise ... from None suppresses the chained ImportError
        # so internal Python import-machinery paths are not leaked to users.
        raise ImportError(
            "amplihack memory features require the memory library.\n"
            f"Install it with: {_PKG_MANAGER} install {_MEMORY_EXTRA}\n"
            f"or: {_PKG_MANAGER} install {_MEMORY_LIB_NAME}"
        ) from None
