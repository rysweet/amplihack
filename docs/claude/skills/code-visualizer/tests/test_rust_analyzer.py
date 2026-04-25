"""Tests for rust_analyzer.normalize()."""

from __future__ import annotations

from pathlib import Path


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_use_statements(tmp_path: Path):
    from rust_analyzer import normalize

    f = _write(
        tmp_path / "src" / "main.rs",
        """
use std::collections::HashMap;
use crate::utils::helper;
use super::sibling;
mod local;
""",
    )
    g = normalize([f])
    assert g.language == "rust"
    dsts = {e.dst for e in g.edges}
    assert any("std" in d or "HashMap" in d or "collections" in d for d in dsts)
    assert any("utils" in d or "helper" in d for d in dsts)
    assert any("sibling" in d for d in dsts)
    assert any("local" in d for d in dsts)


def test_empty(tmp_path: Path):
    from rust_analyzer import normalize

    g = normalize([])
    assert g.language == "rust"
    assert g.edges == []
