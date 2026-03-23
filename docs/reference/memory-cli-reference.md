# Memory CLI Reference

This page documents the current top-level `amplihack memory` surface.

## Synopsis

```bash
amplihack memory <subcommand> [options]
```

## Supported Subcommands

| Subcommand | Purpose                                         |
| ---------- | ----------------------------------------------- |
| `tree`     | Visualize the top-level session memory graph    |
| `export`   | Export an agent-local hierarchical memory store |
| `import`   | Import an agent-local hierarchical memory store |

## `memory tree`

`amplihack memory tree` renders the repo's top-level session memory graph using `MemoryDatabase`, the SQLite-backed store at `~/.amplihack/memory.db` by default.

```bash
amplihack memory tree [--session SESSION] [--type TYPE] [--depth N]
```

### Options

| Flag                | Meaning                                   |
| ------------------- | ----------------------------------------- |
| `--session SESSION` | Filter by session ID                      |
| `--type TYPE`       | Filter by the current legacy parser types |
| `--depth N`         | Limit tree depth                          |

### Current `--type` choices

The current parser accepts these legacy compatibility names:

- `conversation`
- `decision`
- `pattern`
- `context`
- `learning`
- `artifact`

### Examples

```bash
amplihack memory tree
amplihack memory tree --depth 2
amplihack memory tree --session demo_run_01
amplihack memory tree --type learning
```

## `memory export`

`memory export` copies an agent-local hierarchical memory store into a portable JSON file or raw Kuzu directory.

```bash
amplihack memory export --agent AGENT --output OUTPUT [--format {json,kuzu}] [--storage-path STORAGE_PATH]
```

### Options

| Flag                          | Meaning                                                |
| ----------------------------- | ------------------------------------------------------ |
| `--agent AGENT`               | Agent name to export                                   |
| `--output OUTPUT`             | Output file path for JSON or output directory for Kuzu |
| `--format {json,kuzu}`        | Export format; default is `json`                       |
| `--storage-path STORAGE_PATH` | Override the agent's hierarchical-memory storage path  |

### Examples

```bash
amplihack memory export --agent incident-memory-agent --output ./incident-memory.json
amplihack memory export --agent incident-memory-agent --output ./incident-memory-kuzu --format kuzu
```

## `memory import`

`memory import` loads a JSON export into an existing agent memory store, or replaces an agent's raw Kuzu store.

```bash
amplihack memory import --agent AGENT --input INPUT [--format {json,kuzu}] [--merge] [--storage-path STORAGE_PATH]
```

### Options

| Flag                          | Meaning                                               |
| ----------------------------- | ----------------------------------------------------- |
| `--agent AGENT`               | Target agent name                                     |
| `--input INPUT`               | Input file path for JSON or input directory for Kuzu  |
| `--format {json,kuzu}`        | Import format; default is `json`                      |
| `--merge`                     | Merge into existing memory instead of replacing it    |
| `--storage-path STORAGE_PATH` | Override the agent's hierarchical-memory storage path |

### Important caveat

`--merge` is supported only for JSON imports. Raw Kuzu imports replace the target store.

### Examples

```bash
amplihack memory import --agent incident-memory-agent --input ./incident-memory.json --merge
amplihack memory import --agent incident-memory-agent --input ./incident-memory-kuzu --format kuzu
```

## What Is Not Exposed by the Top-Level CLI

The current top-level parser does **not** expose these older surfaces:

- `amplihack memory clean`
- `amplihack memory evaluate`
- `amplihack memory tree --backend ...`

If you need the backend evaluation module directly, run:

```bash
python -m amplihack.memory.cli_evaluate --backend sqlite
```
