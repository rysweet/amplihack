"""Lazy availability check for amplihack-memory-lib.

amplihack-memory-lib is declared as a dependency in pyproject.toml.  The
package manager (pip / uv) installs it when amplihack is installed.

This module provides a **lazy** guard that can be called at the point where
memory features are actually needed — NOT at CLI startup.  On PEP 668
systems the eager startup check caused hard failures even when the user
never invoked memory features (#3331).

No subprocess calls.  No auto-install.  No startup side-effects.
"""

import logging

_log = logging.getLogger(__name__)
_checked: bool | None = None  # tri-state cache: None = not checked yet


def ensure_memory_lib_installed() -> bool:
    """Check whether amplihack-memory-lib is importable (cached).

    Safe to call repeatedly — the actual import probe runs only once and
    the result is cached for the lifetime of the process.

    Returns ``True`` if the library is available, ``False`` otherwise.
    On failure a warning is logged with repair instructions.
    """
    global _checked
    if _checked is not None:
        return _checked

    try:
        import amplihack_memory  # type: ignore[import-untyped]  # noqa: F401

        _checked = True
        return True
    except ImportError:
        _log.warning(
            "amplihack-memory-lib is not importable. Memory features will "
            "be unavailable.  Repair with:  pip install amplihack-memory-lib"
        )
        _checked = False
        return False
