"""Kùzu embedded graph database backend.

Provides an embedded, zero-infrastructure alternative to Neo4j Docker.
No server process needed - just pip install kuzu.

Key Benefits:
- Zero infrastructure: No Docker, no server, no daemon
- Same query language: Uses Cypher (like Neo4j)
- Persistent storage: File-based, survives restarts
- Fast: Embedded execution, no network overhead

Example:
    from amplihack.memory.kuzu import KuzuConnector

    with KuzuConnector() as conn:
        conn.execute_query("CREATE (:Person {name: 'Alice'})")
        results = conn.execute_query("MATCH (p:Person) RETURN p.name")

Installation:
    pip install amplihack
    # (kuzu is now a required dependency)
"""

from .code_graph import KuzuCodeGraph, run_blarify
from .connector import KUZU_AVAILABLE, KuzuConnector

__all__ = ["KuzuConnector", "KUZU_AVAILABLE", "KuzuCodeGraph", "run_blarify"]
