"""Rust module graph analyzer.

Extracts `use …;` and `mod …;` statements via bounded regex. Self-contained
brick: exposes exactly one entry point, `normalize()`.
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

_RE_USE = re.compile(r"^\s*use\s+([A-Za-z_][\w:]{0,500});", re.MULTILINE)
_RE_MOD = re.compile(r"^\s*(?:pub\s+)?mod\s+([A-Za-z_]\w{0,200})\s*;", re.MULTILINE)


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
            nodes.append(Node(id=src_id, label=src_id, language="rust", file_path=str(path)))
            seen.add(src_id)

        for spec in _RE_USE.findall(text):
            edges.append(Edge(src=src_id, dst=spec, kind="use"))
        for name in _RE_MOD.findall(text):
            edges.append(Edge(src=src_id, dst=name, kind="mod"))

    return Graph(language="rust", nodes=nodes, edges=edges)
