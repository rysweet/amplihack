# Migrating KuzuGraphStore from kuzu to ladybug

> [Home](index.md) > [Memory](memory/README.md) > Ladybug Migration

## What Changed

The `KuzuGraphStore` class moved from `amplihack.memory.kuzu_store` to
`amplihack.memory.ladybug_store`. The underlying graph engine changed from
[kuzu](https://kuzudb.com/) to [ladybug](https://github.com/kuzudb/ladybug),
Kùzu's next-generation embedded graph database.

The class name (`KuzuGraphStore`) and its public API are **unchanged**.

### Why ladybug?

Ladybug is the successor to kuzu. It ships the same Cypher query engine with
improvements to concurrent access, string handling, and packaging. The amplihack
upgrade adds `fcntl.flock` serialization so multiple processes (e.g., parallel
agent workstreams) can safely share a single database directory.

## Who Needs to Migrate

| You are… | Action required |
|---|---|
| Using `amplihack memory tree` / `export` / `import` CLI | None — transparent |
| Importing `from amplihack.memory import KuzuGraphStore` | None — still works |
| Importing `from amplihack.memory.kuzu_store import …` | Update import path |
| Running tests that mock `kuzu_store` internals | Update mock paths |
| Calling `KuzuGraphStore(db_path=…)` | None — API unchanged |

## Migration Steps

### 1. Update direct imports

```python
# Before
from amplihack.memory.kuzu_store import KuzuGraphStore

# After
from amplihack.memory.ladybug_store import KuzuGraphStore
```

The package-level import still works without changes:

```python
from amplihack.memory import KuzuGraphStore  # no change needed
```

### 2. Install ladybug

```bash
uv add ladybug
# or
pip install ladybug
```

A graceful fallback to `import kuzu` exists during the transition period. If
neither package is installed, the import raises `ImportError`.

### 3. Update mock/patch targets in tests

```python
# Before
@mock.patch("amplihack.memory.kuzu_store.ladybug.Database")

# After
@mock.patch("amplihack.memory.ladybug_store.ladybug.Database")
```

### 4. Verify

```bash
# Quick smoke test
python3 -c "from amplihack.memory.ladybug_store import KuzuGraphStore; print('OK')"

# Run graph store tests
pytest tests/test_graph_store.py -q
```

## New Features

### Read-only mode

Open a database for read-only access with a shared lock:

```python
store = KuzuGraphStore(db_path="~/.amplihack/memory.db", read_only=True)
nodes = store.query_nodes("Session", filters={"status": "completed"})
store.close()
```

Read-only mode acquires `LOCK_SH` (shared) instead of `LOCK_EX` (exclusive),
allowing concurrent readers.

### flock serialization

All `Database()` creation is now serialized through `fcntl.flock` on a sidecar
`.lock` file next to the database directory. This prevents corruption when
multiple agent processes access the same graph store.

| Scenario | Lock type | Concurrent access |
|---|---|---|
| Normal open | `LOCK_EX` (exclusive) | One writer at a time |
| `read_only=True` | `LOCK_SH` (shared) | Multiple readers |
| Lock timeout (30s) | Raises `TimeoutError` | Caller retries or fails |

The lock is released when `close()` is called or the process exits.

### Cypher identifier validation

All table names, relationship types, and property keys interpolated into Cypher
queries are validated against `^[a-zA-Z_][a-zA-Z0-9_]*$`. Invalid identifiers
raise `ValueError` immediately, preventing Cypher injection.

## Unchanged Behavior

- `KuzuGraphStore` class name
- Constructor signature: `db_path`, `buffer_pool_size`, `max_db_size`
- All public methods: `create_node`, `get_node`, `update_node`, `delete_node`,
  `query_nodes`, `search_nodes`, `create_edge`, `get_edges`, `delete_edge`,
  `ensure_table`, `ensure_rel_table`, `export_nodes`, `export_edges`,
  `import_nodes`, `import_edges`, `get_all_node_ids`, `close`
- Thread safety via `threading.RLock`
- In-memory mode (`db_path=None`)

## Files Changed

| File | Change |
|---|---|
| `src/amplihack/memory/ladybug_store.py` | **New** — replaces `kuzu_store.py` |
| `src/amplihack/memory/kuzu_store.py` | **Deleted** |
| `src/amplihack/memory/__init__.py` | Import path updated |
| `src/amplihack/memory/facade.py` | 2 lazy imports updated |
| `src/amplihack/memory/distributed_store.py` | 1 lazy import updated |
| `src/amplihack/memory/cli_visualize.py` | 2 docstring references updated |
| `tests/test_graph_store.py` | Import path updated |
| `tests/memory/test_cli_visualize.py` | Import path updated |
| `tests/memory/test_code_context_injection.py` | Import path updated |

## Out of Scope

These modules still use `kuzu` directly and are **not** affected:

- `src/amplihack/memory/kuzu/` — Code-graph indexing subsystem
- `src/amplihack/memory/backends/kuzu_backend.py` — Separate backend for the
  5-type memory system

## Related

- [Ladybug Graph Store API](memory/LADYBUG_GRAPH_STORE.md)
- [Kuzu Test Configuration](KUZU_TEST_CONFIGURATION.md)
- [Kuzu Memory Schema](memory/KUZU_MEMORY_SCHEMA.md)
- [Memory README](memory/README.md)
