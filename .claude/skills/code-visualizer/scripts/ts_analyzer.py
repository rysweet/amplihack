"""TypeScript / JavaScript import graph analyzer.

Handles `.ts/.tsx/.js/.jsx/.mjs/.cjs`. Uses bounded regex (no nested
quantifiers) to extract three forms:

1. ESM static:  `import … from '<spec>'`
2. CommonJS:    `require('<spec>')`
3. Dynamic:     `import('<spec>')`

Self-contained brick: exposes exactly one entry point, `normalize()`.
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

# Bounded patterns, anchored on quote pair, no catastrophic backtracking.
_RE_IMPORT_FROM = re.compile(
    r"""import\s+[^'";]{0,500}?from\s*['"]([^'"\n]{1,500})['"]""",
    re.MULTILINE,
)
_RE_IMPORT_BARE = re.compile(
    r"""(?:^|[^.\w])import\s*['"]([^'"\n]{1,500})['"]""",
    re.MULTILINE,
)
_RE_REQUIRE = re.compile(
    r"""require\s*\(\s*['"]([^'"\n]{1,500})['"]\s*\)""",
)
_RE_DYNAMIC = re.compile(
    r"""(?:^|[^.\w])import\s*\(\s*['"]([^'"\n]{1,500})['"]\s*\)""",
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
            nodes.append(Node(id=src_id, label=src_id, language="typescript", file_path=str(path)))
            seen.add(src_id)

        specs: list[str] = []
        for pat in (_RE_IMPORT_FROM, _RE_IMPORT_BARE, _RE_REQUIRE, _RE_DYNAMIC):
            specs.extend(pat.findall(text))

        for spec in specs:
            edges.append(Edge(src=src_id, dst=spec, kind="import"))

    return Graph(language="typescript", nodes=nodes, edges=edges)
