# Memory-Enabled Agents API Reference (Superseded)

This older page described the standalone `amplihack-memory-lib` API as if it were the primary memory story for the repo.

That is no longer the best starting point for this checkout.

## Use These Docs Instead

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
- [Memory tutorial](../tutorials/memory-enabled-agents-getting-started.md)
- [How to integrate memory into agents](../howto/integrate-memory-into-agents.md)
- [Memory CLI reference](./memory-cli-reference.md)

## Why This Page Was Retired

The previous version centered an older standalone SQLite-first API surface and did not reflect the current split between:

- the in-repo CLI memory backend under `src/amplihack/memory`
- the generated `amplihack new --enable-memory` scaffold that packages `amplihack_memory` helpers into a standalone agent bundle

If you still need deep standalone-library details, read the `amplihack-memory-lib` package docs directly. For this repo, start with the replacement docs above.
