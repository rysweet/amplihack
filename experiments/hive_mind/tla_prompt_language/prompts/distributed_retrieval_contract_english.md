# Distributed Retrieval Contract — English Baseline

## Goal

Implement a focused slice of the hive-memory system: the distributed retrieval
contract.

Treat the current contract as an externally visible behavior boundary. Your
implementation must refine that contract into request-local state and explicit
terminal outcomes rather than relying on illegal global knowledge.

## Required deliverables

1. Preserve the original user question end-to-end through distributed retrieval.
2. Fan retrieval out across all active agents participating in the request.
3. Merge results deterministically instead of depending on arrival order.
4. Surface shard failures explicitly. Do not silently downgrade to local-only
   success.
5. Use request-local state to decide when the request is complete or failed.
6. Add focused tests that prove the contract above, including progress to an
   explicit terminal outcome.

## Non-goals

- Do not build a full greenfield distributed hive implementation.
- Do not expand into Azure deployment or transport changes.
- Do not require changes in `amplihack-agent-eval` for this slice.
- Do not add unrelated evaluation or grading features.

## Existing context

Keep the implementation aligned with the current distributed-memory design in
this repo:

- distributed retrieval should touch all participating agents
- identical inputs should lead to identical ordered outputs
- the original question must be preserved
- distributed failures must be explicit
- completion/failure should be derived from request-local bookkeeping
- missing responses should become explicit timeout or failure outcomes, not
  infinite waiting

## Success criteria

- code stays scoped to the retrieval contract
- tests enforce the contract behavior
- no silent fallback path is introduced
- the implementation does not depend on omniscient global completion checks
