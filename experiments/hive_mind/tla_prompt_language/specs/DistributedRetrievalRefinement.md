# Distributed Retrieval Refinement Guidance

`DistributedRetrievalContract.tla` is an **abstract behavioral contract** over
global state. It says what must be true of a distributed retrieval request, but
it does **not** yet define an implementation-ready local-knowledge protocol.

Use this guidance to refine that abstract contract into request-local state and
transitions.

## Required refinement boundary

- Treat the TLA+ module as the source of truth for externally visible behavior.
- Do **not** implement omniscient guards such as “all agents have responded”
  using illegal global knowledge.
- Derive completion and failure from **request-local** state that the runtime
  could actually maintain.

## Request-local protocol shape

Each in-flight request should carry explicit request-local state such as:

- `original_question`
- `normalized_query`
- `target_agents`
- `pending_agents`
- `responded_agents`
- `failed_agents`
- `shard_results`
- `started_at` / `deadline` / timeout state
- `status` or another explicit terminal-state marker

The protocol should make these transitions explicit:

1. dispatch the request to the chosen participating agents
2. record shard success or shard failure per agent
3. monotonically shrink `pending_agents`
4. finalize deterministically when the request reaches a terminal condition

## Illegal knowledge checks

The implementation should avoid:

- a hidden global coordinator check that can see all agents without explicit
  request-local state
- completing successfully before the request has accounted for every targeted
  agent
- silently dropping missing shards and pretending the request completed

## Progress guidance

The first slice should not be safety-only. The implementation should express a
progress story:

- every dispatched request must eventually reach an explicit terminal outcome
- terminal outcomes are `complete` or `failed`
- missing responses must be handled by explicit timeout/deadline logic rather
  than infinite waiting
- shard failures or timeouts must become visible in request state

## Deterministic merge guidance

- merge only facts that were actually recorded for this request
- make merge output independent of arrival order
- preserve the original question throughout the request lifecycle

## Test guidance

Focused tests should cover at least:

- out-of-order shard replies still producing deterministic merged output
- completion only after `pending_agents` reaches zero or equivalent
- timeout/deadline behavior for missing shard replies
- explicit terminal failure when some shards fail
- preservation of the original question through the full request lifecycle
