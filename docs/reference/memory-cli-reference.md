# Memory CLI Reference

This page documents the current `amplihack memory` command surface.

## Synopsis

```bash
amplihack memory <subcommand> [options]
```

## Subcommands

| Subcommand | Purpose                                                             |
| ---------- | ------------------------------------------------------------------- |
| `tree`     | Visualize the in-repo memory graph                                  |
| `clean`    | Preview or delete matching sessions from the in-repo memory backend |
| `export`   | Export an agent memory store to JSON or Kuzu format                 |
| `import`   | Import an agent memory store from JSON or Kuzu format               |

## `memory tree`

Visualize the current memory graph.

```bash
amplihack memory tree [--session SESSION] [--type TYPE] [--depth N] [--backend {kuzu,sqlite}]
```

### Options

| Flag                      | Meaning                           |
| ------------------------- | --------------------------------- |
| `--session SESSION`       | Filter by session ID              |
| `--type TYPE`             | Filter by memory type             |
| `--depth N`               | Limit tree depth                  |
| `--backend {kuzu,sqlite}` | Select backend; default is `kuzu` |

### Current `--type` choices

The CLI currently accepts the legacy compatibility names:

- `conversation`
- `decision`
- `pattern`
- `context`
- `learning`
- `artifact`

The underlying model layer also supports the preferred primary types (`episodic`, `semantic`, `procedural`, `prospective`, `working`), but those are not the current `tree --type` parser choices.

### Examples

```bash
amplihack memory tree
amplihack memory tree --backend kuzu --depth 2
amplihack memory tree --session demo_run_01
amplihack memory tree --type learning
```

## `memory clean`

Preview or delete sessions that match a wildcard pattern.

```bash
amplihack memory clean [--pattern PATTERN] [--backend {kuzu,sqlite}] [--no-dry-run] [--confirm]
```

### Options

| Flag                      | Meaning                                                    |
| ------------------------- | ---------------------------------------------------------- |
| `--pattern PATTERN`       | Wildcard pattern to match; default is `test_*`             |
| `--backend {kuzu,sqlite}` | Select backend; default is `kuzu`                          |
| `--no-dry-run`            | Actually delete matching sessions                          |
| `--confirm`               | Skip the confirmation prompt when used with `--no-dry-run` |

### Examples

```bash
amplihack memory clean --pattern 'test_*'
amplihack memory clean --pattern 'demo_*'
amplihack memory clean --pattern '*_temp'
amplihack memory clean --pattern 'dev_*' --no-dry-run --confirm
```

## `memory export`

Export an agent memory store.

```bash
amplihack memory export --agent AGENT --output OUTPUT [--format {json,kuzu}] [--storage-path STORAGE_PATH]
```

### Options

| Flag                          | Meaning                                                |
| ----------------------------- | ------------------------------------------------------ |
| `--agent AGENT`               | Agent name to export                                   |
| `--output OUTPUT`             | Output file path for JSON or output directory for Kuzu |
| `--format {json,kuzu}`        | Export format; default is `json`                       |
| `--storage-path STORAGE_PATH` | Override the agent's Kuzu storage path                 |

## `memory import`

Import an agent memory store.

```bash
amplihack memory import --agent AGENT --input INPUT [--format {json,kuzu}] [--merge] [--storage-path STORAGE_PATH]
```

### Options

| Flag                          | Meaning                                              |
| ----------------------------- | ---------------------------------------------------- |
| `--agent AGENT`               | Target agent name                                    |
| `--input INPUT`               | Input file path for JSON or input directory for Kuzu |
| `--format {json,kuzu}`        | Import format; default is `json`                     |
| `--merge`                     | Merge into existing memory instead of replacing it   |
| `--storage-path STORAGE_PATH` | Override the agent's Kuzu storage path               |

## Source-Checkout Caveat for `export` and `import`

The parser currently exposes `export` and `import`, but in this source checkout those commands still import `amplihack.agents.goal_seeking.memory_export` and related modules that are missing from `src/`.

When run from this checkout with `PYTHONPATH=src`, they can fail with `ModuleNotFoundError` before the export or import work begins.

Treat `tree` and `clean` as the verified top-level CLI memory commands here, and use `export` or `import` only if you have restored those source modules or you are running from a package build that includes them.

## Backend Path Resolution

For the Kuzu backend, the preferred environment variable is:

```bash
export AMPLIHACK_GRAPH_DB_PATH=/path/to/memory_kuzu.db
```

The legacy alias still exists:

```bash
export AMPLIHACK_KUZU_DB_PATH=/path/to/memory_kuzu.db
```

If neither is set, the default path is `~/.amplihack/memory_kuzu.db`.

## Related Docs

- [Top-level CLI reference](./cli.md)
- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
