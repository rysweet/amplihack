"""Contract tests for the language-blind Graph data structure."""

from __future__ import annotations


def test_node_is_dataclass_with_required_fields():
    from graph import Node

    n = Node(id="a.b", label="a.b", language="python", file_path="a/b.py")
    assert n.id == "a.b"
    assert n.label == "a.b"
    assert n.language == "python"
    assert n.file_path == "a/b.py"


def test_edge_is_dataclass_with_required_fields():
    from graph import Edge

    e = Edge(src="a", dst="b", kind="import")
    assert e.src == "a"
    assert e.dst == "b"
    assert e.kind == "import"


def test_graph_holds_language_nodes_and_edges():
    from graph import Edge, Graph, Node

    g = Graph(
        language="python",
        nodes=[Node(id="a", label="a", language="python", file_path="a.py")],
        edges=[Edge(src="a", dst="b", kind="import")],
    )
    assert g.language == "python"
    assert len(g.nodes) == 1
    assert len(g.edges) == 1


def test_graph_no_inheritance_among_analyzers():
    """Brick philosophy: analyzers must NOT subclass each other."""
    import go_analyzer
    import python_analyzer
    import rust_analyzer
    import ts_analyzer

    for mod in (python_analyzer, ts_analyzer, rust_analyzer, go_analyzer):
        assert hasattr(mod, "normalize"), f"{mod.__name__} must expose normalize()"

    # No analyzer module should define a class that another analyzer inherits from.
    import inspect

    classes = []
    for mod in (python_analyzer, ts_analyzer, rust_analyzer, go_analyzer):
        for _name, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ == mod.__name__:
                classes.append(cls)

    for cls in classes:
        bases = [b for b in cls.__mro__[1:] if b is not object]
        for base in bases:
            assert base.__module__ not in {
                "python_analyzer",
                "ts_analyzer",
                "rust_analyzer",
                "go_analyzer",
            }, f"{cls} inherits from analyzer base {base}"
