> [Home](../index.md) > Memory

# Memory

This is the landing page for the current memory documentation.

## Start Here

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md) - fast path for `memory tree`, `memory export`, `memory import`, and generated memory-enabled agents
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md) - explanation of the current top-level SQLite graph view and agent-local Kuzu stores
- [Memory tutorial](../tutorials/memory-enabled-agents-getting-started.md) - step-by-step walkthrough for generating and running a memory-enabled goal agent
- [How to integrate memory into agents](../howto/integrate-memory-into-agents.md) - practical guide for adding memory helpers to generated agent code
- [Memory CLI reference](../reference/memory-cli-reference.md) - exact top-level command syntax and caveats
- [Kuzu code schema](./KUZU_CODE_SCHEMA.md) - schema details for the lower-level Kuzu-backed graph store
- [Memory diagrams](../../Specs/MEMORY_AGENTS_DIAGRAMS.md) - presentation-friendly architecture diagrams

## What "Memory" Means in This Repo

There are three related but distinct memory stories:

1. the top-level CLI graph view under `src/amplihack/memory`, which powers `amplihack memory tree` and stores session data in `~/.amplihack/memory.db`
2. the agent-local hierarchical store used by `amplihack memory export` and `amplihack memory import`
3. the generated goal-agent scaffold from `amplihack new --enable-memory`, which packages `amplihack_memory` helpers, `memory_config.yaml`, and a local `./memory/` directory

The docs above keep those surfaces separate on purpose.

## Verified CLI Surface

The top-level commands verified in this checkout are:

- `amplihack memory tree`
- `amplihack memory export`
- `amplihack memory import`
- `amplihack new --enable-memory`

See the CLI reference for the exact syntax and the caveats around JSON merge versus raw Kuzu replacement.

## Historical Material

Older docs in this area sometimes described removed top-level CLI commands or treated lower-level Kuzu/SQLite experiments as if they were the current default user surface. Treat those as historical context, not as the primary how-to story for the current checkout.
