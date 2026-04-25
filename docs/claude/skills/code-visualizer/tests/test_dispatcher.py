"""Tests for dispatcher: language detection, routing, ignore dirs."""

from __future__ import annotations

from pathlib import Path


def _write(p: Path, text: str = "") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_dispatcher_routes_by_extension(tmp_path: Path):
    from dispatcher import analyze

    _write(tmp_path / "a.py", "import os\n")
    _write(tmp_path / "b.ts", "import x from './y';\n")
    _write(tmp_path / "c.go", 'package main\nimport "fmt"\n')
    _write(tmp_path / "d.rs", "use std::io;\n")

    result = analyze(tmp_path)
    # result is a dict[language_name, Graph]
    assert "python" in result
    assert "typescript" in result
    assert "go" in result
    assert "rust" in result
    for lang, g in result.items():
        assert g.language == lang


def test_dispatcher_ignores_common_dirs(tmp_path: Path):
    from dispatcher import analyze

    _write(tmp_path / "real.py", "import os\n")
    _write(tmp_path / "node_modules" / "junk.ts", "import x from 'y';\n")
    _write(tmp_path / ".git" / "stuff.py", "import gone\n")
    _write(tmp_path / "__pycache__" / "x.py", "import nope\n")
    _write(tmp_path / "dist" / "out.js", "require('z');\n")

    result = analyze(tmp_path)
    py = result.get("python")
    assert py is not None
    # Only the real one
    file_paths = {n.file_path for n in py.nodes}
    assert any("real.py" in fp for fp in file_paths)
    assert not any("__pycache__" in fp for fp in file_paths)
    assert not any(".git" in fp for fp in file_paths)
    # node_modules should be excluded entirely
    ts = result.get("typescript")
    if ts is not None:
        assert not any("node_modules" in n.file_path for n in ts.nodes)


def test_dispatcher_returns_empty_for_unsupported(tmp_path: Path):
    from dispatcher import analyze

    _write(tmp_path / "doc.md", "hello")
    _write(tmp_path / "config.toml", "x = 1")
    result = analyze(tmp_path)
    assert result == {} or all(len(g.nodes) == 0 for g in result.values())


def test_dispatcher_rejects_nonexistent_path(tmp_path: Path):
    import pytest as _pytest
    from dispatcher import analyze

    with _pytest.raises((FileNotFoundError, ValueError, NotADirectoryError)):
        analyze(tmp_path / "does-not-exist")
