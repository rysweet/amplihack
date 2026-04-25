"""Language-blind graph data contract used by all analyzers and the renderer.

Brick philosophy: this module defines plain dataclasses (a *data contract*),
not a base class. Analyzers may import these dataclasses but MUST NOT inherit
from one another.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    label: str
    language: str
    file_path: str


@dataclass
class Edge:
    src: str
    dst: str
    kind: str


@dataclass
class Graph:
    language: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
