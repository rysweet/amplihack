"""Tests for staleness detection: max-mtime over source files vs diagram mtime."""

from __future__ import annotations

import os
import time
from pathlib import Path


def _write(p: Path, text: str = "") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_diagram_missing_is_stale(tmp_path: Path):
    from staleness import is_stale

    _write(tmp_path / "a.py", "import os\n")
    diagram = tmp_path / "diagram.mmd"
    assert is_stale(tmp_path, diagram, ["python"]) is True


def test_diagram_newer_than_sources_is_fresh(tmp_path: Path):
    from staleness import is_stale

    src = _write(tmp_path / "a.py", "x=1\n")
    old = time.time() - 100
    os.utime(src, (old, old))
    diagram = _write(tmp_path / "d.mmd", "graph LR\n")
    # diagram mtime is now > old
    assert is_stale(tmp_path, diagram, ["python"]) is False


def test_source_newer_than_diagram_is_stale(tmp_path: Path):
    from staleness import is_stale

    diagram = _write(tmp_path / "d.mmd", "graph LR\n")
    old = time.time() - 100
    os.utime(diagram, (old, old))
    _write(tmp_path / "a.py", "x=2\n")  # new mtime
    assert is_stale(tmp_path, diagram, ["python"]) is True


def test_only_listed_languages_considered(tmp_path: Path):
    from staleness import is_stale

    diagram = _write(tmp_path / "d.mmd", "graph LR\n")
    old = time.time() - 100
    os.utime(diagram, (old, old))
    # Only a JS file is newer; if we ask about python only, should be fresh
    _write(tmp_path / "a.js", "require('x');\n")
    assert is_stale(tmp_path, diagram, ["python"]) is False
    assert is_stale(tmp_path, diagram, ["typescript"]) is True
