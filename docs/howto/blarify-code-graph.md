# How to Use Blarify Code Graph Indexing

Blarify indexes your codebase into a Kuzu graph database so AI agents can
understand code structure - files, classes, functions, and call relationships.

## Quick Start

Blarify runs automatically on session start. It detects if your codebase needs
indexing and runs SCIP indexing in the background. No configuration required.

## Prerequisites

**Required**: Node.js (for scip-python)

```bash
npm install -g @sourcegraph/scip-python
```

**Optional** (for other languages):

```bash
npm install -g @sourcegraph/scip-typescript   # TypeScript/JavaScript
go install github.com/sourcegraph/scip-go/cmd/scip-go@latest  # Go
rustup component add rust-analyzer             # Rust
```

## How It Works

1. **Session start**: The session_start hook checks if indexing is needed
2. **SCIP indexing**: `scip-python` creates an `index.scip` file from your code
3. **Kuzu import**: The SCIP index is imported into a Kuzu graph database
4. **Context injection**: Agents get a summary of the code graph and query instructions

The database is stored at `.amplihack/kuzu_db` in your project root.

## Querying the Code Graph

Agents (and you) can query the graph using the CLI tool:

```bash
# Statistics
python -m amplihack.memory.kuzu.query_code_graph stats

# Search for symbols (functions, classes, files)
python -m amplihack.memory.kuzu.query_code_graph search Orchestrator

# List files matching a pattern
python -m amplihack.memory.kuzu.query_code_graph files --pattern indexing

# List functions in a file
python -m amplihack.memory.kuzu.query_code_graph functions --file orchestrator.py

# List classes in a file
python -m amplihack.memory.kuzu.query_code_graph classes --file code_graph.py

# Find what calls a function
python -m amplihack.memory.kuzu.query_code_graph callers connect

# Find what a function calls
python -m amplihack.memory.kuzu.query_code_graph callees get_users

# JSON output for programmatic use
python -m amplihack.memory.kuzu.query_code_graph search Orchestrator --json

# Limit results
python -m amplihack.memory.kuzu.query_code_graph functions --limit 100
```

## Configuration

Control behavior with environment variables:

| Variable                    | Values                       | Default      | Description                |
| --------------------------- | ---------------------------- | ------------ | -------------------------- |
| `AMPLIHACK_DISABLE_BLARIFY` | `1`                          | unset        | Disable blarify completely |
| `AMPLIHACK_BLARIFY_MODE`    | `background`, `sync`, `skip` | `background` | Indexing mode              |

**Examples**:

```bash
# Disable blarify
export AMPLIHACK_DISABLE_BLARIFY=1

# Run synchronously (blocks until done)
export AMPLIHACK_BLARIFY_MODE=sync

# Skip indexing this session
export AMPLIHACK_BLARIFY_MODE=skip
```

## Troubleshooting

### "scip-python not installed"

```bash
npm install -g @sourcegraph/scip-python
```

### Indexing seems slow

SCIP indexing time depends on codebase size:

- ~200 files: ~40 seconds
- ~1000 files: ~3 minutes

Use background mode (default) so it doesn't block your session.

### "Duplicate primary key" warnings

These are harmless. Python decorators cause SCIP to generate duplicate symbols.
The data is still imported correctly - duplicates are silently skipped.

### No code graph data available

Check that the database exists:

```bash
ls -la .amplihack/kuzu_db
```

If missing, trigger a re-index:

```bash
AMPLIHACK_BLARIFY_MODE=sync amplihack
```

### Query returns empty results

The SCIP indexer only indexes files tracked by git. Make sure your source files
are committed or at least staged.
