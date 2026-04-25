"""Go package import graph analyzer.

Handles single `import "fmt"` and grouped `import ( … )` blocks (with
optional aliases). Self-contained brick: exposes exactly one entry point,
`normalize()`.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve().parent
if str(_HERE) not in _sys.path:
    _sys.path.insert(0, str(_HERE))

import logging
import re
from collections.abc import Iterable
from pathlib import Path

from graph import Edge, Graph, Node

LOG = logging.getLogger(__name__)
MAX_BYTES = 5 * 1024 * 1024

_RE_SINGLE = re.compile(
    r"""^\s*import\s+(?:[A-Za-z_]\w{0,100}\s+)?["]([^"\n]{1,500})["]""",
    re.MULTILINE,
)
_RE_BLOCK = re.compile(r"import\s*\(([^)]{0,5000})\)", re.DOTALL)
_RE_BLOCK_ITEM = re.compile(
    r"""(?:[A-Za-z_]\w{0,100}\s+)?["]([^"\n]{1,500})["]""",
)


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
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen: set[str] = set()

    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            continue
        text = _read(path)
        if not text:
            continue

        src_id = path.stem
        if src_id not in seen:
            nodes.append(Node(id=src_id, label=src_id, language="go", file_path=str(path)))
            seen.add(src_id)

        for spec in _RE_SINGLE.findall(text):
            edges.append(Edge(src=src_id, dst=spec, kind="import"))

        for block in _RE_BLOCK.findall(text):
            for spec in _RE_BLOCK_ITEM.findall(block):
                edges.append(Edge(src=src_id, dst=spec, kind="import"))

    return Graph(language="go", nodes=nodes, edges=edges)
