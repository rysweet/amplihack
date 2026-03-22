# Memory

This is the landing page for the current memory documentation.

## Start Here

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md) - fast path for `memory tree`, `memory clean`, and generated memory-enabled agents
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md) - explanation of the current Kuzu graph backend and generated-agent memory scaffold
- [Memory tutorial](../tutorials/memory-enabled-agents-getting-started.md) - step-by-step walkthrough for generating and running a memory-enabled goal agent
- [How to integrate memory into agents](../howto/integrate-memory-into-agents.md) - practical guide for adding memory helpers to generated agent code
- [Memory CLI reference](../reference/memory-cli-reference.md) - exact command syntax and options
- [Kuzu code schema](./KUZU_CODE_SCHEMA.md) - schema details for the Kuzu-backed graph store
- [Memory diagrams](../../Specs/MEMORY_AGENTS_DIAGRAMS.md) - presentation-friendly architecture diagrams

## What "Memory" Means in This Repo

There are two related but different memory stories:

1. the in-repo memory backend under `src/amplihack/memory`, which powers `amplihack memory tree` and `amplihack memory clean`
2. the generated goal-agent scaffold from `amplihack new --enable-memory`, which packages `amplihack_memory` helpers, `memory_config.yaml`, and a local `./memory/` directory

The docs above keep those two surfaces separate on purpose.

## Verified CLI Surface

The top-level commands verified in this checkout are:

- `amplihack memory tree`
- `amplihack memory clean`
- `amplihack new --enable-memory`

See the CLI reference for the full syntax and the current caveats around `export` and `import`.

## Historical Material

Older docs in this area sometimes described Neo4j- or SQLite-first designs as if they were the current path. Treat those as historical context, not as the primary how-to story for the current checkout.
