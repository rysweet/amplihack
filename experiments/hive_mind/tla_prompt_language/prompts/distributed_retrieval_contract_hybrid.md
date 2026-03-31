# Distributed Retrieval Contract — Hybrid Prompt

Use the formal specification below as the source of truth, and use this
natural-language guidance only to map the contract onto the current repo.

Focus on:

- preserving the original question
- dispatching retrieval across all active agents
- deterministic merged outputs
- explicit failure surfaces
- focused tests that enforce the contract

Do not build a new full hive runtime. Keep the implementation scoped to the
distributed retrieval contract.
