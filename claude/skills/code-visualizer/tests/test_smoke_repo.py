"""Smoke test: run dispatcher against the amplihack repo root.

Asserts that we get non-empty mermaid output for languages this repo actually
contains from the supported set (Python and JS/TS). Rust/Go are tolerated as
absent.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_dispatcher_against_repo_root():
    from dispatcher import analyze
    from mermaid_renderer import render

    assert REPO_ROOT.exists(), f"repo root missing: {REPO_ROOT}"
    result = analyze(REPO_ROOT)

    assert "python" in result, f"expected python in result; got {sorted(result)}"
    py_mermaid = render(result["python"])
    assert py_mermaid.strip() != ""
    assert "-->" in py_mermaid  # has at least one edge

    # JS/TS may or may not be present depending on repo contents
    if "typescript" in result and result["typescript"].nodes:
        ts_mermaid = render(result["typescript"])
        assert ts_mermaid.strip() != ""
