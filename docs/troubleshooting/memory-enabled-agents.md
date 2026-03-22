# Troubleshooting Memory-Enabled Agents (Superseded)

This older troubleshooting page referenced commands and storage assumptions that are no longer current, including:

- `amplihack memory query`
- `amplihack memory metrics`
- `amplihack goal-agent ...`
- older per-agent SQLite paths as the primary top-level memory story

## Use These Docs Instead

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
- [Memory CLI reference](../reference/memory-cli-reference.md)
- [How to integrate memory into agents](../howto/integrate-memory-into-agents.md)

## Current Verified CLI Surface

The verified top-level commands in this checkout are:

- `amplihack memory tree`
- `amplihack memory clean`
- `amplihack new --enable-memory`

See the replacement docs above for the current command syntax and caveats.
