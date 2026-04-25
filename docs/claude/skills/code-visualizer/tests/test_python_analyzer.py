"""Tests for python_analyzer.normalize()."""

from __future__ import annotations

from pathlib import Path


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_normalize_extracts_simple_imports(tmp_path: Path):
    from python_analyzer import normalize

    a = _write(tmp_path / "pkg" / "a.py", "import os\nimport pkg.b\n")
    b = _write(tmp_path / "pkg" / "b.py", "x = 1\n")
    _write(tmp_path / "pkg" / "__init__.py", "")

    g = normalize([a, b])
    assert g.language == "python"
    node_ids = {n.id for n in g.nodes}
    # a and b at minimum
    assert any(nid.endswith("a") for nid in node_ids)
    assert any(nid.endswith("b") for nid in node_ids)

    # edge a -> pkg.b (or b)
    pairs = {(e.src, e.dst) for e in g.edges}
    assert any(src.endswith("a") and ("b" in dst) for src, dst in pairs)


def test_normalize_extracts_from_imports(tmp_path: Path):
    from python_analyzer import normalize

    f = _write(tmp_path / "m.py", "from collections import OrderedDict\nfrom .sib import x\n")
    g = normalize([f])
    dsts = {e.dst for e in g.edges}
    assert any("collections" in d for d in dsts)


def test_normalize_skips_unparseable(tmp_path: Path):
    from python_analyzer import normalize

    bad = _write(tmp_path / "bad.py", "def (((( syntax error\n")
    good = _write(tmp_path / "good.py", "import json\n")
    g = normalize([bad, good])
    # Should not raise; should still return graph with json edge
    assert any("json" in e.dst for e in g.edges)


def test_normalize_empty_input_returns_empty_graph():
    from python_analyzer import normalize

    g = normalize([])
    assert g.language == "python"
    assert g.nodes == []
    assert g.edges == []
