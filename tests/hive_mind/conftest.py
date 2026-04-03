"""Conftest for hive_mind tests.

Stubs heavy optional dependencies so query_expansion can be loaded
without requiring kuzu or amplihack_memory to be installed.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock


def _stub(name: str) -> None:
    """Insert a MagicMock stub for *name* and its parent packages."""
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        key = ".".join(parts[:i])
        if key not in sys.modules:
            sys.modules[key] = MagicMock()


# Stub heavy optional deps BEFORE any amplihack.agents import runs.
_stub("kuzu")
_stub("amplihack_memory")
_stub("amplihack_memory.cognitive_memory")
_stub("amplihack_memory.graph")
_stub("amplihack_memory.graph.KuzuGraphStore")
