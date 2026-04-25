"""Tests for go_analyzer.normalize()."""

from __future__ import annotations

from pathlib import Path


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_single_import(tmp_path: Path):
    from go_analyzer import normalize

    f = _write(tmp_path / "a.go", 'package main\n\nimport "fmt"\n')
    g = normalize([f])
    assert g.language == "go"
    dsts = {e.dst for e in g.edges}
    assert any("fmt" in d for d in dsts)


def test_grouped_import_block(tmp_path: Path):
    from go_analyzer import normalize

    f = _write(
        tmp_path / "b.go",
        """package main

import (
    "fmt"
    "os"
    alias "github.com/user/repo/pkg"
)
""",
    )
    g = normalize([f])
    dsts = {e.dst for e in g.edges}
    assert any("fmt" in d for d in dsts)
    assert any("os" in d for d in dsts)
    assert any("github.com/user/repo/pkg" in d for d in dsts)


def test_empty(tmp_path: Path):
    from go_analyzer import normalize

    g = normalize([])
    assert g.language == "go"
    assert g.edges == []
