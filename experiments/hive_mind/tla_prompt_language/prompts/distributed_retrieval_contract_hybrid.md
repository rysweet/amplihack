# Distributed Retrieval Contract — Hybrid Prompt

Use the formal specification below as the source of truth, and use this
natural-language guidance only to map the contract onto the current repo.

The formal spec is an abstract behavioral contract. Implement it as a
request-local protocol that a real runtime could maintain, not as an illegal
omniscient global-state check.

Focus on:

- preserving the original question
- dispatching retrieval across all active agents
- deterministic merged outputs
- explicit failure surfaces
- request-local completion and failure tracking
- focused tests that enforce the contract and request progress

Do not build a new full hive runtime. Keep the implementation scoped to the
distributed retrieval contract.
