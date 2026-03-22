# 5-Type Memory System Guide (Superseded)

This older guide described an automatic 5-type memory flow with hook behavior and backend assumptions that are not the current source of truth for this checkout.

## Use These Docs Instead

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
- [Memory CLI reference](../reference/memory-cli-reference.md)
- [Memory docs landing page](./README.md)

## Why This Page Was Retired

The current docs separate:

- the in-repo CLI memory backend under `src/amplihack/memory`
- the generated `amplihack new --enable-memory` scaffold for standalone goal-agent packages

The older automatic-hook narrative and backend performance claims from the previous version of this page should not be treated as the current user guide.
