"""Amplihack hooks package.

Bridge the Claude tools hook package to the source-tree hooks package so
collection-safe compatibility modules under ``src/amplihack/hooks`` remain
importable even when ``.claude/tools`` wins the initial import race.
"""

from __future__ import annotations

from pathlib import Path

_CURRENT = Path(__file__).resolve()
_PROJECT_ROOT = next((parent for parent in _CURRENT.parents if (parent / ".claude").exists()), None)

if _PROJECT_ROOT is not None:
    _SRC_HOOKS_DIR = _PROJECT_ROOT / "src" / "amplihack" / "hooks"
    if _SRC_HOOKS_DIR.exists():
        _SRC_HOOKS_STR = str(_SRC_HOOKS_DIR)
        if _SRC_HOOKS_STR not in __path__:
            __path__.append(_SRC_HOOKS_STR)
