"""Tests for ts_analyzer.normalize() — handles .ts/.tsx/.js/.jsx/.mjs/.cjs."""

from __future__ import annotations

from pathlib import Path


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_es_module_static_imports(tmp_path: Path):
    from ts_analyzer import normalize

    f = _write(
        tmp_path / "src" / "a.ts",
        """
import { foo } from './b';
import bar from "./c";
import * as ns from 'lodash';
""",
    )
    g = normalize([f])
    assert g.language == "typescript"
    dsts = {e.dst for e in g.edges}
    assert any("b" in d for d in dsts)
    assert any("c" in d for d in dsts)
    assert any("lodash" in d for d in dsts)


def test_commonjs_require(tmp_path: Path):
    from ts_analyzer import normalize

    f = _write(tmp_path / "x.js", "const fs = require('fs');\nconst u = require('./util');\n")
    g = normalize([f])
    dsts = {e.dst for e in g.edges}
    assert any("fs" in d for d in dsts)
    assert any("util" in d for d in dsts)


def test_dynamic_import(tmp_path: Path):
    from ts_analyzer import normalize

    f = _write(tmp_path / "y.mjs", "const m = await import('./lazy');\n")
    g = normalize([f])
    dsts = {e.dst for e in g.edges}
    assert any("lazy" in d for d in dsts)


def test_tsx_jsx_supported(tmp_path: Path):
    from ts_analyzer import normalize

    a = _write(tmp_path / "a.tsx", "import React from 'react';\n")
    b = _write(tmp_path / "b.jsx", "import x from './x';\n")
    g = normalize([a, b])
    dsts = {e.dst for e in g.edges}
    assert any("react" in d for d in dsts)
    assert any("x" in d for d in dsts)


def test_empty_input(tmp_path: Path):
    from ts_analyzer import normalize

    g = normalize([])
    assert g.language == "typescript"
    assert g.edges == []
