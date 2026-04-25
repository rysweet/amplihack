"""Language dispatcher: scan a path, group files by language, route to analyzers.

Loads each language's analyzer via `importlib` (string module name in the
registry) so the dispatcher has no compile-time dependency on any specific
analyzer module.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve().parent
if str(_HERE) not in _sys.path:
    _sys.path.insert(0, str(_HERE))

import importlib
import logging
import os
from pathlib import Path

from graph import Graph

LOG = logging.getLogger(__name__)

# Directories never traversed.
IGNORE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".tox",
        "dist",
        "build",
        "target",  # rust build dir
        ".next",
        ".cache",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)

# language name -> (analyzer module name, set of extensions)
LANGUAGES: dict[str, tuple[str, frozenset[str]]] = {
    "python": ("python_analyzer", frozenset({".py"})),
    "typescript": (
        "ts_analyzer",
        frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}),
    ),
    "rust": ("rust_analyzer", frozenset({".rs"})),
    "go": ("go_analyzer", frozenset({".go"})),
}


def _ext_to_language(ext: str) -> str | None:
    for lang, (_mod, exts) in LANGUAGES.items():
        if ext in exts:
            return lang
    return None


def _scan(root: Path) -> dict[str, list[Path]]:
    by_lang: dict[str, list[Path]] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Filter ignored dirs in place.
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            lang = _ext_to_language(ext)
            if lang is None:
                continue
            by_lang.setdefault(lang, []).append(Path(dirpath) / name)
    return by_lang


def analyze(target: Path | str) -> dict[str, Graph]:
    """Detect languages under `target`, run each analyzer, return graphs.

    Raises ValueError if `target` does not exist or is not a directory.
    """
    path = Path(target)
    if not path.exists():
        raise FileNotFoundError(f"target path does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"target is not a directory: {path}")

    by_lang = _scan(path)
    result: dict[str, Graph] = {}
    for lang, files in by_lang.items():
        mod_name, _exts = LANGUAGES[lang]
        try:
            module = importlib.import_module(mod_name)
        except ImportError as exc:
            LOG.error("could not load analyzer %s: %s", mod_name, exc)
            continue
        normalize = getattr(module, "normalize", None)
        if normalize is None:
            LOG.error("analyzer %s missing normalize()", mod_name)
            continue
        result[lang] = normalize(files)
    return result
