# Agent Memory Integration (Superseded)

This page used to describe an older Neo4j-era memory integration flow.

That material is no longer the current source of truth for this repo.

## Use These Docs Instead

- [Agent Memory Quickstart](./AGENT_MEMORY_QUICKSTART.md)
- [Memory-enabled agents architecture](./concepts/memory-enabled-agents-architecture.md)
- [Memory tutorial](./tutorials/memory-enabled-agents-getting-started.md)
- [How to integrate memory into agents](./howto/integrate-memory-into-agents.md)
- [Memory CLI reference](./reference/memory-cli-reference.md)

## What Changed

The current docs separate two different memory surfaces:

- the in-repo CLI memory backend under `src/amplihack/memory`
- the generated `amplihack new --enable-memory` scaffold that uses `amplihack_memory` helpers in a standalone package

The older automatic Neo4j injection and extraction flow described in the previous version of this page is not the current repo story.
