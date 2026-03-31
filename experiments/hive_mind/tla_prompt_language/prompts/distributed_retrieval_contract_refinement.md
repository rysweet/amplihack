# Distributed Retrieval Contract — TLA+ Refinement Prompt

Use the formal specification below as the abstract contract, and use the
refinement guidance to turn that contract into an implementation-ready
request-local protocol.

Focus on:

- preserving the original question end-to-end
- dispatching retrieval across all active agents
- deterministic merged outputs independent of arrival order
- explicit shard failure surfaces
- request-local tracking of pending/responded/failed agents
- explicit timeout/deadline handling so requests reach terminal outcomes
- focused tests for both safety and progress behavior

Do not build a new full hive runtime. Keep the implementation scoped to the
distributed retrieval contract and its request-local refinement.
