---
name: code-graph
version: 2.0.0
description: Query the code graph for functions, classes, files, and call relationships
triggers:
  - "show code graph"
  - "query code graph"
  - "search codebase"
  - "find function"
philosophy:
  - principle: Observable
    application: Clear view of codebase structure via graph queries
  - principle: Zero-BS
    application: Uses real query tool, no stubs or temp scripts
dependencies:
  required:
    - Python packages: kuzu
    - scip-python (npm install -g @sourcegraph/scip-python)
examples:
  - "/code-graph stats"
  - "/code-graph search Orchestrator"
---

# Code Graph Command

Query the Kuzu code graph for code intelligence - functions, classes, files,
and call relationships.

## Usage

Use the query tool directly:

```bash
# Statistics
python -m amplihack.memory.kuzu.query_code_graph stats

# Search for symbols
python -m amplihack.memory.kuzu.query_code_graph search <name>

# List functions in a file
python -m amplihack.memory.kuzu.query_code_graph functions --file <path>

# List classes in a file
python -m amplihack.memory.kuzu.query_code_graph classes --file <path>

# Find files matching a pattern
python -m amplihack.memory.kuzu.query_code_graph files --pattern <pattern>

# Call graph
python -m amplihack.memory.kuzu.query_code_graph callers <function_name>
python -m amplihack.memory.kuzu.query_code_graph callees <function_name>
```

Add `--json` for machine-readable output. Add `--limit N` to control results.

## Prerequisites

The code graph must be indexed first. This happens automatically on session
start (background indexing). To check status:

```bash
python -m amplihack.memory.kuzu.query_code_graph stats
```

If no data, ensure `scip-python` is installed:

```bash
npm install -g @sourcegraph/scip-python
```

## See Also

- `docs/howto/blarify-code-graph.md` - Full user guide
