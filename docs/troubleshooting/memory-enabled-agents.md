# Troubleshooting Memory-Enabled Agents (Superseded)

This older troubleshooting page referenced commands and storage assumptions that are no longer current, including removed top-level CLI surfaces such as `memory clean`, `memory query`, and `memory metrics`.

## Use These Docs Instead

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
- [Memory CLI reference](../reference/memory-cli-reference.md)
- [How to integrate memory into agents](../howto/integrate-memory-into-agents.md)

## Current Verified CLI Surface

The verified top-level commands in this checkout are:

- `amplihack memory tree`
- `amplihack memory export`
- `amplihack memory import`
- `amplihack new --enable-memory`

## Current Memory Surface Split

- `amplihack memory tree` shows the top-level SQLite session graph at `~/.amplihack/memory.db`
- `amplihack memory export` / `amplihack memory import` operate on agent-local hierarchical stores
- generated goal-agent packages created with `--enable-memory` use their own local `./memory/` directory

See the replacement docs above for the current command syntax and caveats.
