"""Tests for mermaid_renderer: language-blind rendering and combined view."""

from __future__ import annotations


def _make_graph(language: str, edges: list[tuple[str, str]]):
    from graph import Edge, Graph, Node

    nodes_set = set()
    for s, d in edges:
        nodes_set.add(s)
        nodes_set.add(d)
    nodes = [Node(id=n, label=n, language=language, file_path=f"{n}.x") for n in sorted(nodes_set)]
    es = [Edge(src=s, dst=d, kind="import") for s, d in edges]
    return Graph(language=language, nodes=nodes, edges=es)


def test_render_empty_graph_returns_string():
    from graph import Graph
    from mermaid_renderer import render

    out = render(Graph(language="python", nodes=[], edges=[]))
    assert isinstance(out, str)
    assert out.strip() != ""
    # Must declare a graph type
    assert "graph" in out.lower() or "flowchart" in out.lower()


def test_render_includes_edges():
    from mermaid_renderer import render

    g = _make_graph("python", [("a", "b"), ("b", "c")])
    out = render(g)
    assert "-->" in out
    # both edges represented
    assert out.count("-->") >= 2


def test_render_sanitizes_node_ids():
    from mermaid_renderer import render

    g = _make_graph("typescript", [("./foo-bar", "@scope/pkg")])
    out = render(g)
    # No raw '@' or unescaped '/' as a bare identifier — sanitized form should appear
    # We just check the output is non-empty and contains an edge arrow.
    assert "-->" in out
    # The ids should be sanitized to valid mermaid identifiers (alnum/underscore)
    # Check that we don't emit bare '@scope/pkg' as the identifier on the LHS of [
    for line in out.splitlines():
        # mermaid id syntax: `id["label"]` — the id (before [) must be sanitized
        if "[" in line and "]" in line:
            ident = line.split("[", 1)[0].strip().split()[-1]
            assert all(ch.isalnum() or ch == "_" for ch in ident), f"bad id: {ident!r}"


def test_render_combined_uses_subgraph_per_language():
    from mermaid_renderer import render_combined

    graphs = {
        "python": _make_graph("python", [("a", "b")]),
        "typescript": _make_graph("typescript", [("x", "y")]),
    }
    out = render_combined(graphs)
    assert "subgraph" in out
    # one subgraph per language
    assert out.lower().count("subgraph") >= 2
    assert "python" in out
    assert "typescript" in out


def test_render_combined_empty():
    from mermaid_renderer import render_combined

    out = render_combined({})
    assert isinstance(out, str)
    assert out.strip() != ""
