"""KuzuGraphStore — kuzu.Database-backed GraphStore implementation.

Maps the GraphStore protocol to Kùzu Cypher queries:
  - create_node  → CREATE (:table {properties})
  - get_node     → MATCH (n:table) WHERE n.node_id = $id RETURN n
  - query_nodes  → MATCH (n:table) WHERE ... RETURN n LIMIT k
  - search_nodes → MATCH (n:table) WHERE CONTAINS(n.field, $text) RETURN n
  - create_edge  → MATCH (a), (b) CREATE (a)-[:rel]->(b)
  - get_edges    → MATCH (n)-[r:rel]->() WHERE ...

Requires kuzu to be installed (`uv add kuzu`).
"""

from __future__ import annotations

import re
import threading
import uuid
from pathlib import Path
from typing import Any


def _validate_identifier(name: str) -> None:
    """Validate that name is a safe Cypher identifier to prevent injection."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid identifier: {name!r}")


# Kuzu type → Python type coercion helpers
_KUZU_INT_TYPES = {"INT64", "INT32", "INT16", "INT8", "UINT64", "UINT32", "UINT16", "UINT8"}
_KUZU_FLOAT_TYPES = {"DOUBLE", "FLOAT"}


def _coerce(value: Any, kuzu_type: str) -> Any:
    """Coerce a Python value to match the declared Kuzu column type."""
    if value is None:
        return None
    t = kuzu_type.upper()
    if t in _KUZU_INT_TYPES:
        return int(value)
    if t in _KUZU_FLOAT_TYPES:
        return float(value)
    if t == "BOOLEAN":
        return bool(value)
    return str(value) if not isinstance(value, str) else value


class KuzuGraphStore:
    """Kùzu-backed GraphStore.

    Args:
        db_path: Path to the Kùzu database directory. Use None for in-memory.
        buffer_pool_size: Buffer pool size in bytes (default 64 MB).
        max_db_size: Max database size in bytes (default 1 GB).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        buffer_pool_size: int = 64 * 1024 * 1024,
        max_db_size: int = 1024 * 1024 * 1024,
    ) -> None:
        import kuzu

        db_arg = str(db_path) if db_path is not None else None
        if db_path is not None:
            p = Path(db_path)
            # Kuzu creates its own db directory; remove empty stale dir if present
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
            p.parent.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(
            db_arg,
            buffer_pool_size=buffer_pool_size,
            max_db_size=max_db_size,
        )
        self._conn = kuzu.Connection(self._db)
        self._lock = threading.RLock()
        # Track known tables to avoid duplicate CREATE TABLE
        self._known_tables: set[str] = set()
        self._known_rel_tables: set[str] = set()
        # Cache schemas for coercion
        self._schemas: dict[str, dict[str, str]] = {}
        # rel_type -> (from_table, to_table) for import_edges
        self._rel_table_map: dict[str, tuple[str, str]] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        with self._lock:
            if params:
                return self._conn.execute(query, parameters=params)
            return self._conn.execute(query)

    def _result_to_dicts(self, result: Any) -> list[dict[str, Any]]:
        """Convert a Kùzu query result to a list of dicts."""
        rows = []
        if result is None:
            return rows
        col_names = result.get_column_names()
        while result.has_next():
            row = result.get_next()
            row_dict: dict[str, Any] = {}
            for i, col in enumerate(col_names):
                val = row[i]
                # Kùzu returns node objects for node columns — flatten to dict
                if hasattr(val, "_node"):
                    # older kuzu API
                    inner = val._node
                    if isinstance(inner, dict):
                        row_dict.update(inner)
                    else:
                        row_dict[col] = val
                elif hasattr(val, "get_properties"):
                    row_dict.update(val.get_properties())
                elif isinstance(val, dict):
                    row_dict.update(val)
                else:
                    row_dict[col] = val
            rows.append(row_dict)
        return rows

    def _build_where(self, filters: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Build a WHERE clause from a filters dict."""
        clauses = []
        params: dict[str, Any] = {}
        for i, (k, v) in enumerate(filters.items()):
            param_name = f"filter_{i}"
            clauses.append(f"n.{k} = ${param_name}")
            params[param_name] = v
        where = " AND ".join(clauses)
        return where, params

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def ensure_table(self, table: str, schema: dict[str, str]) -> None:
        if table in self._known_tables:
            return
        _validate_identifier(table)
        # Build column definitions
        cols = ", ".join(f"{col} {dtype}" for col, dtype in schema.items())
        # node_id is always the primary key
        if "node_id" in schema:
            query = f"CREATE NODE TABLE IF NOT EXISTS {table} ({cols}, PRIMARY KEY (node_id))"
        else:
            query = f"CREATE NODE TABLE IF NOT EXISTS {table} ({cols})"
        self._execute(query)
        self._known_tables.add(table)
        self._schemas[table] = dict(schema)

    def ensure_rel_table(
        self,
        rel_type: str,
        from_table: str,
        to_table: str,
        schema: dict[str, str] | None = None,
    ) -> None:
        if rel_type in self._known_rel_tables:
            return
        _validate_identifier(rel_type)
        _validate_identifier(from_table)
        _validate_identifier(to_table)
        if schema:
            cols = ", ".join(f"{col} {dtype}" for col, dtype in schema.items())
            query = (
                f"CREATE REL TABLE IF NOT EXISTS {rel_type} "
                f"(FROM {from_table} TO {to_table}, {cols})"
            )
        else:
            query = (
                f"CREATE REL TABLE IF NOT EXISTS {rel_type} "
                f"(FROM {from_table} TO {to_table})"
            )
        self._execute(query)
        self._known_rel_tables.add(rel_type)
        self._rel_table_map[rel_type] = (from_table, to_table)

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def create_node(self, table: str, properties: dict[str, Any]) -> str:
        _validate_identifier(table)
        node_id = properties.get("node_id") or str(uuid.uuid4())
        props = dict(properties)
        props["node_id"] = node_id

        schema = self._schemas.get(table, {})
        coerced = {k: _coerce(v, schema.get(k, "STRING")) for k, v in props.items()}

        prop_str = ", ".join(f"{k}: ${k}" for k in coerced.keys())
        query = f"CREATE (:{table} {{{prop_str}}})"
        self._execute(query, coerced)
        return node_id

    def get_node(self, table: str, node_id: str) -> dict[str, Any] | None:
        _validate_identifier(table)
        query = f"MATCH (n:{table}) WHERE n.node_id = $node_id RETURN n"
        result = self._execute(query, {"node_id": node_id})
        rows = self._result_to_dicts(result)
        return rows[0] if rows else None

    def update_node(self, table: str, node_id: str, properties: dict[str, Any]) -> None:
        _validate_identifier(table)
        schema = self._schemas.get(table, {})
        set_clauses = []
        params: dict[str, Any] = {"node_id": node_id}
        for i, (k, v) in enumerate(properties.items()):
            pname = f"upd_{i}"
            set_clauses.append(f"n.{k} = ${pname}")
            params[pname] = _coerce(v, schema.get(k, "STRING"))
        if not set_clauses:
            return
        set_str = ", ".join(set_clauses)
        query = f"MATCH (n:{table}) WHERE n.node_id = $node_id SET {set_str}"
        self._execute(query, params)

    def delete_node(self, table: str, node_id: str) -> None:
        _validate_identifier(table)
        query = f"MATCH (n:{table}) WHERE n.node_id = $node_id DETACH DELETE n"
        self._execute(query, {"node_id": node_id})

    def query_nodes(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        _validate_identifier(table)
        if filters:
            where, params = self._build_where(filters)
            query = f"MATCH (n:{table}) WHERE {where} RETURN n LIMIT {limit}"
        else:
            query = f"MATCH (n:{table}) RETURN n LIMIT {limit}"
            params = {}
        result = self._execute(query, params or None)
        return self._result_to_dicts(result)

    def search_nodes(
        self,
        table: str,
        text: str,
        fields: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _validate_identifier(table)
        schema = self._schemas.get(table, {})
        search_fields = fields or [
            col for col, dtype in schema.items()
            if dtype.upper() in ("STRING", "VARCHAR")
        ]
        if not search_fields:
            # No schema info — fall back to node_id search
            search_fields = ["node_id"]

        # Tokenise the query into up to 6 meaningful keywords (len >= 3) so
        # that full natural-language questions still find relevant nodes even
        # when no node contains the entire question as a literal substring.
        # This mirrors SemanticMemory.search_facts keyword tokenisation.
        _STOP = frozenset(
            {"what", "was", "the", "did", "how", "who", "why", "are", "is",
             "it", "in", "on", "at", "of", "to", "and", "or", "not", "for",
             "with", "from", "that", "this", "a", "an", "by", "be", "has",
             "had", "have", "does", "were", "been", "being", "do", "its"}
        )
        tokens = [
            w.strip("?.,!;:'\"").lower()
            for w in text.split()
            if len(w.strip("?.,!;:'\"")) >= 3
            and w.strip("?.,!;:'\"").lower() not in _STOP
        ][:6]

        if tokens:
            params: dict[str, Any] = {"lim": limit}
            kw_clauses: list[str] = []
            for i, tok in enumerate(tokens):
                pname = f"kw{i}"
                params[pname] = tok
                field_clauses = [f"lower(n.{f}) CONTAINS lower(${pname})" for f in search_fields]
                kw_clauses.append("(" + " OR ".join(field_clauses) + ")")
            where = " OR ".join(kw_clauses)
            query = f"MATCH (n:{table}) WHERE {where} RETURN n LIMIT $lim"
            result = self._execute(query, params)
        else:
            # Fallback to exact substring match when no usable tokens
            result = self._execute(
                f"MATCH (n:{table}) WHERE "
                + " OR ".join(f"CONTAINS(n.{f}, $text)" for f in search_fields)
                + " RETURN n LIMIT $lim",
                {"text": text, "lim": limit},
            )
        return self._result_to_dicts(result)

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
        _validate_identifier(rel_type)
        _validate_identifier(from_table)
        _validate_identifier(to_table)
        params: dict[str, Any] = {"from_id": from_id, "to_id": to_id}
        if properties:
            prop_str = ", ".join(f"{k}: ${k}" for k in properties.keys())
            params.update(properties)
            query = (
                f"MATCH (a:{from_table}), (b:{to_table}) "
                f"WHERE a.node_id = $from_id AND b.node_id = $to_id "
                f"CREATE (a)-[:{rel_type} {{{prop_str}}}]->(b)"
            )
        else:
            query = (
                f"MATCH (a:{from_table}), (b:{to_table}) "
                f"WHERE a.node_id = $from_id AND b.node_id = $to_id "
                f"CREATE (a)-[:{rel_type}]->(b)"
            )
        self._execute(query, params)

    def get_edges(
        self,
        node_id: str,
        rel_type: str | None = None,
        direction: str = "out",
    ) -> list[dict[str, Any]]:
        if rel_type is not None:
            _validate_identifier(rel_type)
        rel_pattern = f"[r:{rel_type}]" if rel_type else "[r]"
        if direction == "out":
            query = (
                f"MATCH (n)-{rel_pattern}->(m) "
                f"WHERE n.node_id = $node_id "
                f"RETURN r, n.node_id AS from_id, m.node_id AS to_id"
            )
        elif direction == "in":
            query = (
                f"MATCH (m)-{rel_pattern}->(n) "
                f"WHERE n.node_id = $node_id "
                f"RETURN r, m.node_id AS from_id, n.node_id AS to_id"
            )
        else:
            query = (
                f"MATCH (n)-{rel_pattern}-(m) "
                f"WHERE n.node_id = $node_id "
                f"RETURN r, n.node_id AS from_id, m.node_id AS to_id"
            )
        result = self._execute(query, {"node_id": node_id})
        rows = []
        if result:
            col_names = result.get_column_names()
            while result.has_next():
                row = result.get_next()
                row_dict: dict[str, Any] = {}
                for i, col in enumerate(col_names):
                    val = row[i]
                    if col == "r":
                        if hasattr(val, "get_properties"):
                            row_dict.update(val.get_properties())
                        elif isinstance(val, dict):
                            row_dict.update(val)
                    else:
                        row_dict[col] = val
                # Store the rel_type from the query pattern
                if rel_type is not None:
                    row_dict["rel_type"] = rel_type
                rows.append(row_dict)
        return rows

    def delete_edge(self, rel_type: str, from_id: str, to_id: str) -> None:
        _validate_identifier(rel_type)
        query = (
            f"MATCH (a)-[r:{rel_type}]->(b) "
            f"WHERE a.node_id = $from_id AND b.node_id = $to_id "
            f"DELETE r"
        )
        self._execute(query, {"from_id": from_id, "to_id": to_id})

    # ------------------------------------------------------------------
    # Export / import helpers (for gossip and shard rebuild)
    # ------------------------------------------------------------------

    def get_all_node_ids(self, table: str | None = None) -> set[str]:
        """Get all node IDs, optionally filtered by table."""
        node_ids: set[str] = set()
        tables = [table] if table else list(self._known_tables)
        for tbl in tables:
            if tbl not in self._known_tables:
                continue
            _validate_identifier(tbl)
            query = f"MATCH (n:{tbl}) RETURN n.node_id"
            result = self._execute(query)
            if result:
                while result.has_next():
                    row = result.get_next()
                    if row and row[0] is not None:
                        node_ids.add(str(row[0]))
        return node_ids

    def export_nodes(self, node_ids: list[str] | None = None) -> list[tuple[str, str, dict]]:
        """Export nodes as (table, node_id, properties) tuples."""
        result = []
        id_set = set(node_ids) if node_ids is not None else None
        for tbl in list(self._known_tables):
            _validate_identifier(tbl)
            nodes = self.query_nodes(tbl, limit=100_000)
            for node in nodes:
                nid = node.get("node_id", "")
                if id_set is None or nid in id_set:
                    result.append((tbl, nid, dict(node)))
        return result

    def export_edges(self, node_ids: list[str] | None = None) -> list[tuple[str, str, str, str, str, dict]]:
        """Export edges as (rel_type, from_table, from_id, to_table, to_id, properties) tuples."""
        result = []
        id_set = set(node_ids) if node_ids is not None else None
        for rel_type in list(self._known_rel_tables):
            _validate_identifier(rel_type)
            from_table, to_table = self._rel_table_map.get(rel_type, ("", ""))
            query = f"MATCH (a)-[r:{rel_type}]->(b) RETURN a.node_id, b.node_id"
            res = self._execute(query)
            if res:
                while res.has_next():
                    row = res.get_next()
                    from_id, to_id = str(row[0]), str(row[1])
                    if id_set is None or from_id in id_set or to_id in id_set:
                        result.append((rel_type, from_table, from_id, to_table, to_id, {}))
        return result

    def import_nodes(self, nodes: list[tuple[str, str, dict]]) -> int:
        """Import nodes. Returns count of new nodes stored (skips duplicates)."""
        count = 0
        for table, node_id, props in nodes:
            if table not in self._known_tables:
                continue
            if self.get_node(table, node_id) is None:
                self.create_node(table, dict(props))
                count += 1
        return count

    def import_edges(self, edges: list[tuple[str, str, str, str, str, dict]]) -> int:
        """Import edges. Returns count stored."""
        count = 0
        for rel_type, from_table, from_id, to_table, to_id, props in edges:
            if rel_type not in self._known_rel_tables:
                continue
            _validate_identifier(rel_type)
            if not from_table:
                from_table, to_table = self._rel_table_map.get(rel_type, ("", ""))
            if not from_table:
                continue
            check_q = (
                f"MATCH (a:{from_table})-[r:{rel_type}]->(b:{to_table}) "
                f"WHERE a.node_id = $fid AND b.node_id = $tid RETURN r LIMIT 1"
            )
            res = self._execute(check_q, {"fid": from_id, "tid": to_id})
            if not self._result_to_dicts(res):
                self.create_edge(rel_type, from_table, from_id, to_table, to_id, props or None)
                count += 1
        return count

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


__all__ = ["KuzuGraphStore"]
