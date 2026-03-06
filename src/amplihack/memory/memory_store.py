"""InMemoryGraphStore — dict-based GraphStore implementation.

Stores nodes as dict[table][node_id] = properties.
Stores edges as a flat list of dicts.
search_nodes does keyword matching across specified (or all string) fields.

Used as the default shard backend for DistributedGraphStore and for
topology=single + backend=simple scenarios.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any


class InMemoryGraphStore:
    """In-memory implementation of the GraphStore protocol.

    Thread-safe via a single RLock.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # table -> {node_id -> properties_dict}
        self._nodes: dict[str, dict[str, dict[str, Any]]] = {}
        # list of edge dicts: {rel_type, from_table, from_id, to_table, to_id, **props}
        self._edges: list[dict[str, Any]] = []
        # table -> schema (for ensure_table idempotency)
        self._tables: dict[str, dict[str, str]] = {}
        # rel_type -> (from_table, to_table, schema)
        self._rel_tables: dict[str, tuple[str, str, dict[str, str]]] = {}

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def create_node(self, table: str, properties: dict[str, Any]) -> str:
        node_id = properties.get("node_id") or str(uuid.uuid4())
        props = dict(properties)
        props["node_id"] = node_id
        with self._lock:
            if table not in self._nodes:
                self._nodes[table] = {}
            self._nodes[table][node_id] = props
        return node_id

    def get_node(self, table: str, node_id: str) -> dict[str, Any] | None:
        with self._lock:
            table_data = self._nodes.get(table, {})
            node = table_data.get(node_id)
            return dict(node) if node is not None else None

    def update_node(self, table: str, node_id: str, properties: dict[str, Any]) -> None:
        with self._lock:
            table_data = self._nodes.get(table, {})
            if node_id in table_data:
                table_data[node_id].update(properties)

    def delete_node(self, table: str, node_id: str) -> None:
        with self._lock:
            table_data = self._nodes.get(table, {})
            table_data.pop(node_id, None)
            # Also remove edges involving this node
            self._edges = [
                e for e in self._edges
                if e["from_id"] != node_id and e["to_id"] != node_id
            ]

    def query_nodes(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            table_data = self._nodes.get(table, {})
            results = []
            for node in table_data.values():
                if filters:
                    if all(node.get(k) == v for k, v in filters.items()):
                        results.append(dict(node))
                else:
                    results.append(dict(node))
                if len(results) >= limit:
                    break
        return results

    def search_nodes(
        self,
        table: str,
        text: str,
        fields: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        text_lower = text.lower()
        results: list[dict[str, Any]] = []
        with self._lock:
            table_data = self._nodes.get(table, {})
            for node in table_data.values():
                search_fields = fields if fields else [
                    k for k, v in node.items() if isinstance(v, str)
                ]
                for field in search_fields:
                    val = node.get(field)
                    if isinstance(val, str) and text_lower in val.lower():
                        results.append(dict(node))
                        break
                if len(results) >= limit:
                    break
        return results

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def create_edge(
        self,
        rel_type: str,
        from_table: str,
        from_id: str,
        to_table: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        edge: dict[str, Any] = {
            "rel_type": rel_type,
            "from_table": from_table,
            "from_id": from_id,
            "to_table": to_table,
            "to_id": to_id,
        }
        if properties:
            edge.update(properties)
        with self._lock:
            self._edges.append(edge)

    def get_edges(
        self,
        node_id: str,
        rel_type: str | None = None,
        direction: str = "out",
    ) -> list[dict[str, Any]]:
        results = []
        with self._lock:
            for edge in self._edges:
                if rel_type is not None and edge["rel_type"] != rel_type:
                    continue
                if direction == "out" and edge["from_id"] == node_id:
                    results.append(dict(edge))
                elif direction == "in" and edge["to_id"] == node_id:
                    results.append(dict(edge))
                elif direction == "both" and (
                    edge["from_id"] == node_id or edge["to_id"] == node_id
                ):
                    results.append(dict(edge))
        return results

    def delete_edge(self, rel_type: str, from_id: str, to_id: str) -> None:
        with self._lock:
            self._edges = [
                e for e in self._edges
                if not (
                    e["rel_type"] == rel_type
                    and e["from_id"] == from_id
                    and e["to_id"] == to_id
                )
            ]

    # ------------------------------------------------------------------
    # Schema operations (idempotent)
    # ------------------------------------------------------------------

    def ensure_table(self, table: str, schema: dict[str, str]) -> None:
        with self._lock:
            if table not in self._tables:
                self._tables[table] = schema
                self._nodes.setdefault(table, {})

    def ensure_rel_table(
        self,
        rel_type: str,
        from_table: str,
        to_table: str,
        schema: dict[str, str] | None = None,
    ) -> None:
        with self._lock:
            if rel_type not in self._rel_tables:
                self._rel_tables[rel_type] = (from_table, to_table, schema or {})

    def close(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Export / import helpers (for gossip and shard rebuild)
    # ------------------------------------------------------------------

    def get_all_node_ids(self, table: str | None = None) -> set[str]:
        """Get all node IDs, optionally filtered by table."""
        with self._lock:
            if table:
                return set(self._nodes.get(table, {}).keys())
            return {nid for tbl in self._nodes.values() for nid in tbl}

    def export_nodes(self, node_ids: list[str] | None = None) -> list[tuple[str, str, dict]]:
        """Export nodes as (table, node_id, properties) tuples."""
        result = []
        with self._lock:
            for table, nodes in self._nodes.items():
                for nid, props in nodes.items():
                    if node_ids is None or nid in set(node_ids):
                        result.append((table, nid, dict(props)))
        return result

    def export_edges(self, node_ids: list[str] | None = None) -> list[tuple[str, str, str, dict]]:
        """Export edges as (rel_type, from_id, to_id, properties) tuples."""
        result = []
        with self._lock:
            id_set = set(node_ids) if node_ids else None
            for edge in self._edges:
                if id_set is None or edge["from_id"] in id_set or edge["to_id"] in id_set:
                    result.append((edge["rel_type"], edge["from_id"], edge["to_id"], edge.get("properties", {})))
        return result

    def import_nodes(self, nodes: list[tuple[str, str, dict]]) -> int:
        """Import nodes. Returns count of new nodes stored (skips duplicates)."""
        count = 0
        with self._lock:
            for table, node_id, props in nodes:
                if table not in self._nodes:
                    self._nodes[table] = {}
                if node_id not in self._nodes[table]:
                    self._nodes[table][node_id] = dict(props)
                    count += 1
        return count

    def import_edges(self, edges: list[tuple[str, str, str, dict]]) -> int:
        """Import edges. Returns count stored."""
        count = 0
        with self._lock:
            existing = {(e["rel_type"], e["from_id"], e["to_id"]) for e in self._edges}
            for rel_type, from_id, to_id, props in edges:
                if (rel_type, from_id, to_id) not in existing:
                    self._edges.append({
                        "rel_type": rel_type,
                        "from_id": from_id,
                        "from_table": "",
                        "to_id": to_id,
                        "to_table": "",
                        "properties": props,
                    })
                    existing.add((rel_type, from_id, to_id))
                    count += 1
        return count

    # ------------------------------------------------------------------
    # Introspection helpers (for testing / distributed shard access)
    # ------------------------------------------------------------------

    def get_all_nodes(self, table: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(n) for n in self._nodes.get(table, {}).values()]

    @property
    def table_names(self) -> list[str]:
        with self._lock:
            return list(self._nodes.keys())


__all__ = ["InMemoryGraphStore"]
