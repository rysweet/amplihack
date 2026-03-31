# Distributed Retrieval Contract — TLA+ Prompt

Implement only the retrieval-contract slice described by the formal
specification below.

Important boundary: the formal specification is an abstract contract over
global state. Do not mistake that for an implementation-ready omniscient
protocol. Refine it into request-local state and explicit terminal transitions.

Required output:

- code for the distributed retrieval contract slice
- focused tests for question preservation, all-agent participation,
  deterministic merge behavior, explicit failure propagation, and eventual
  terminal request outcomes

Do not widen scope beyond the specified contract.
