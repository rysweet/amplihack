# Memory Tree Visualization

This page documents the current `amplihack memory tree` command.

## Overview

`amplihack memory tree` renders the repo's top-level session memory graph using `MemoryDatabase`, a SQLite store at `~/.amplihack/memory.db` by default.

It is a graph view over the top-level CLI/session memory store. It is **not** a live view into a generated goal agent's local `./memory/` directory.

## Usage

### Basic command

```bash
amplihack memory tree
```

### Filter by session

```bash
amplihack memory tree --session Session-2026-01-12
```

### Filter by current parser type

```bash
amplihack memory tree --type learning
amplihack memory tree --type pattern
```

The current parser accepts these legacy type names:

- `conversation`
- `decision`
- `pattern`
- `context`
- `learning`
- `artifact`

### Limit depth

```bash
amplihack memory tree --depth 3
```

## Supported Options

```bash
amplihack memory tree [--session SESSION] [--type TYPE] [--depth N]
```

There is no supported top-level `--backend` flag on `memory tree` in the current parser.

## Output Shape

The command renders a Rich tree of the current session graph, grouped by session and memory item metadata. The exact styling may change, but the current command is intended for human inspection rather than machine parsing.

## Related Commands

- `amplihack memory export` / `amplihack memory import` for agent-local hierarchical memory transfer
- `amplihack new --enable-memory` for generated agent scaffolds with local `./memory/`

## Related Docs

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [Memory CLI reference](../reference/memory-cli-reference.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
