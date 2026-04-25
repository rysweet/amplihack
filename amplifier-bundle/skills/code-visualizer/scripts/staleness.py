"""Staleness detection: compare a diagram's mtime to the max source mtime."""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve().parent
if str(_HERE) not in _sys.path:
    _sys.path.insert(0, str(_HERE))

import importlib
import os
from collections.abc import Iterable
from pathlib import Path


def _dispatcher_constants() -> tuple[frozenset[str], dict]:
    """Lazily import the sibling dispatcher module to avoid hard top-level dep."""
    mod = importlib.import_module("dispatcher")
    return mod.IGNORE_DIRS, mod.LANGUAGES


def _extensions_for(languages: Iterable[str]) -> set[str]:
    _ignore, lang_table = _dispatcher_constants()
    exts: set[str] = set()
    for lang in languages:
        if lang in lang_table:
            _mod, lang_exts = lang_table[lang]
            exts.update(lang_exts)
    return exts


def _max_source_mtime(root: Path, extensions: set[str]) -> float | None:
    ignore_dirs, _lang_table = _dispatcher_constants()
    latest: float | None = None
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in extensions:
                continue
            try:
                m = (Path(dirpath) / name).stat().st_mtime
            except OSError:
                continue
            if latest is None or m > latest:
                latest = m
    return latest


def is_stale(target: Path | str, diagram: Path | str, languages: Iterable[str]) -> bool:
    """Return True if any source file is newer than the diagram (or diagram missing)."""
    target_path = Path(target)
    diagram_path = Path(diagram)

    if not diagram_path.exists():
        return True

    try:
        diagram_mtime = diagram_path.stat().st_mtime
    except OSError:
        return True

    extensions = _extensions_for(languages)
    if not extensions:
        return False

    latest = _max_source_mtime(target_path, extensions)
    if latest is None:
        return False
    return latest > diagram_mtime
