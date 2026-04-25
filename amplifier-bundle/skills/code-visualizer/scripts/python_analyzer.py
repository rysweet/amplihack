"""Python import graph analyzer.

Uses the standard library `ast` module to extract `import` and `from … import`
statements. Each source file becomes a node identified by its dotted module
path (best-effort) or filename stem; each import becomes an edge.

Self-contained brick: exposes exactly one entry point, `normalize()`. No
inheritance from or to any other analyzer.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve().parent
if str(_HERE) not in _sys.path:
    _sys.path.insert(0, str(_HERE))

import ast
import logging
from collections.abc import Iterable
from pathlib import Path

from graph import Edge, Graph, Node

LOG = logging.getLogger(__name__)
MAX_BYTES = 5 * 1024 * 1024  # per-file safety cap


def _module_id(path: Path) -> str:
    """Best-effort dotted module id from a path.

    Walks up while sibling __init__.py files exist; otherwise uses the stem.
    """
    parts: list[str] = [path.stem]
    parent = path.parent
    while (parent / "__init__.py").exists():
        parts.append(parent.name)
        if parent.parent == parent:
            break
        parent = parent.parent
    return ".".join(reversed(parts))


def _read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_BYTES:
            LOG.warning("skipping %s: exceeds %d bytes", path, MAX_BYTES)
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        LOG.warning("could not read %s: %s", path, exc)
        return ""


def normalize(paths: Iterable[Path]) -> Graph:
    """Build a normalized Graph from Python source files."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_node_ids: set[str] = set()

    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            continue
        text = _read(path)
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            LOG.info("skipping unparseable %s: %s", path, exc)
            continue

        src_id = _module_id(path)
        if src_id not in seen_node_ids:
            nodes.append(Node(id=src_id, label=src_id, language="python", file_path=str(path)))
            seen_node_ids.add(src_id)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append(Edge(src=src_id, dst=alias.name, kind="import"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and not module:
                    # Pure relative import like `from . import x` — record names
                    for alias in node.names:
                        edges.append(Edge(src=src_id, dst=alias.name, kind="import"))
                else:
                    edges.append(Edge(src=src_id, dst=module, kind="import"))

    return Graph(language="python", nodes=nodes, edges=edges)
