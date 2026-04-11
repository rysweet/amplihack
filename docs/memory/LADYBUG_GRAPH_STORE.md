# Ladybug Graph Store API

> [Home](../index.md) > [Memory](README.md) > Ladybug Graph Store

API reference for `amplihack.memory.ladybug_store.KuzuGraphStore`.

## Import

```python
# Preferred — stable package-level export
from amplihack.memory import KuzuGraphStore

# Direct module import
from amplihack.memory.ladybug_store import KuzuGraphStore
```

## Constructor

```python
KuzuGraphStore(
    db_path: str | Path | None = None,
    buffer_pool_size: int = 67_108_864,   # 64 MB
    max_db_size: int = 1_073_741_824,     # 1 GB
    read_only: bool = False,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `db_path` | `str \| Path \| None` | `None` | Path to database directory. `None` for in-memory. |
| `buffer_pool_size` | `int` | 64 MB | Buffer pool size in bytes. |
| `max_db_size` | `int` | 1 GB | Maximum database size in bytes. |
| `read_only` | `bool` | `False` | Open in read-only mode with shared lock. |

When `db_path` is not `None`, a sidecar `<db_path>.lock` file is created and
locked via `fcntl.flock` before the database is opened. Read-only mode uses
`LOCK_SH`; write mode uses `LOCK_EX`. The lock is released by `close()`.

## Schema Methods

### ensure_table

```python
store.ensure_table(table: str, schema: dict[str, str]) -> None
```

Create a node table if it doesn't exist. The schema maps column names to Kùzu
types. If `node_id` is included in the schema, it becomes the `PRIMARY KEY`.
You must include `node_id` for `create_node` / `get_node` to work.

```python
store.ensure_table("Session", {
    "node_id": "STRING",
    "start_time": "STRING",
    "status": "STRING",
    "context": "STRING",
})
```

### ensure_rel_table

```python
store.ensure_rel_table(
    rel_type: str,
    from_table: str,
    to_table: str,
    schema: dict[str, str] | None = None,
) -> None
```

Create a relationship table if it doesn't exist.

```python
store.ensure_rel_table("REMEMBERS", "Session", "EpisodicMemory", schema={
    "strength": "DOUBLE",
})
```

## Node CRUD

### create_node

```python
store.create_node(table: str, properties: dict[str, Any]) -> str
```

Create a node with the given properties. Returns the `node_id` (auto-generated
UUID if not provided in `properties`).

```python
node_id = store.create_node("Session", {
    "start_time": "2026-04-10T07:00:00Z",
    "status": "active",
})
```

### get_node

```python
store.get_node(table: str, node_id: str) -> dict[str, Any] | None
```

Retrieve a node by ID. Returns `None` if not found.

### update_node

```python
store.update_node(table: str, node_id: str, properties: dict[str, Any]) -> None
```

Update specific properties on an existing node. Only the provided keys are
modified.

### delete_node

```python
store.delete_node(table: str, node_id: str) -> None
```

Delete a node by ID.

## Querying

### query_nodes

```python
store.query_nodes(
    table: str,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]
```

Query nodes with optional equality filters. Returns up to `limit` rows.

```python
sessions = store.query_nodes("Session", filters={"status": "active"}, limit=10)
```

### search_nodes

```python
store.search_nodes(
    table: str,
    text: str,
    fields: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]
```

Keyword-tokenized search. Splits `text` into up to 6 meaningful keywords
(length ≥ 3, stop words removed), then matches any keyword against all `STRING`
columns (or only the specified `fields`) using Cypher `CONTAINS()`. Falls back
to exact substring match when no usable tokens remain.

```python
results = store.search_nodes(
    "SemanticMemory",
    text="authentication",
    fields=["content", "concept"],
    limit=5,
)
```

## Edge Operations

### create_edge

```python
store.create_edge(
    rel_type: str,
    from_table: str,
    from_id: str,
    to_table: str,
    to_id: str,
    properties: dict[str, Any] | None = None,
) -> None
```

Create a directed edge between two nodes.

```python
store.create_edge(
    "REMEMBERS", "Session", session_id,
    "EpisodicMemory", memory_id,
    properties={"strength": 0.9},
)
```

### get_edges

```python
store.get_edges(
    node_id: str,
    rel_type: str | None = None,
    direction: str = "out",
) -> list[dict[str, Any]]
```

Query edges connected to a node. `direction` controls traversal: `"out"`
(outgoing), `"in"` (incoming), or `"both"`. Returns dicts with `from_id`,
`to_id`, edge properties, and optionally `rel_type`.

### delete_edge

```python
store.delete_edge(rel_type: str, from_id: str, to_id: str) -> None
```

Delete a specific edge.

## Import / Export

### export_nodes

```python
store.export_nodes(
    node_ids: list[str] | None = None,
) -> list[tuple[str, str, dict]]
```

Export nodes as `(table, node_id, properties)` tuples. If `node_ids` is `None`,
exports all nodes.

### export_edges

```python
store.export_edges(
    node_ids: list[str] | None = None,
) -> list[tuple[str, str, str, str, str, dict]]
```

Export edges as `(rel_type, from_table, from_id, to_table, to_id, properties)`
tuples. If `node_ids` is provided, exports edges where either endpoint is in
the set.

### import_nodes / import_edges

```python
store.import_nodes(nodes: list[tuple[str, str, dict]]) -> int
store.import_edges(edges: list[tuple[str, str, str, str, str, dict]]) -> int
```

Import nodes and edges from the export format (`(table, node_id, props)` for
nodes). Returns the count of items imported. Only imports into already-known
tables. Duplicate `node_id` values are silently skipped (MERGE semantics).

## Utility

### get_all_node_ids

```python
store.get_all_node_ids(table: str | None = None) -> set[str]
```

Return all node IDs across all tables, or for a specific table.

### close

```python
store.close() -> None
```

Close the database connection and release the flock. Always call this when done,
or use a context manager pattern:

```python
store = KuzuGraphStore(db_path="/tmp/test.db")
try:
    store.create_node("Session", {"status": "active"})
finally:
    store.close()
```

## Concurrency

`KuzuGraphStore` is thread-safe within a single process (protected by
`threading.RLock`). Cross-process safety is provided by `fcntl.flock`:

```
Process A: KuzuGraphStore(db_path="/data/graph")  → acquires LOCK_EX
Process B: KuzuGraphStore(db_path="/data/graph")  → blocks until A releases
Process C: KuzuGraphStore(db_path="/data/graph", read_only=True)
           → blocks until A releases (readers wait for writers)

Process D: KuzuGraphStore(db_path="/data/graph", read_only=True)  → acquires LOCK_SH
Process E: KuzuGraphStore(db_path="/data/graph", read_only=True)  → acquires LOCK_SH (concurrent)
Process F: KuzuGraphStore(db_path="/data/graph")  → blocks until D and E release
```

Lock timeout is 30 seconds. If the lock cannot be acquired, `TimeoutError` is
raised.

## Security

All identifiers (table names, relationship types, property keys) interpolated
into Cypher queries are validated against `^[a-zA-Z_][a-zA-Z0-9_]*$`. Invalid
identifiers raise `ValueError`. User-supplied values always use `$param`
binding, never string interpolation.

## Related

- [Ladybug Migration Guide](../LADYBUG_MIGRATION_GUIDE.md)
- [Kuzu Memory Schema](KUZU_MEMORY_SCHEMA.md)
- [Kuzu Code Schema](KUZU_CODE_SCHEMA.md)
- [Memory README](README.md)
