# Module Creation Guide: How the HiveMindOrchestrator Was Built

This document explains the process used to identify the architectural gap and implement
`hive_mind/orchestrator.py` as a functional brick. Use it as a template when creating
future modules for the `feat/distributed-hive-mind` branch or any part of amplihack.

---

## 1. Identifying the Gap

### Method: Read the Architecture First

Before writing a single line of code, read:

1. **`DESIGN.md`** — the authoritative description of the intended system
2. **`__init__.py`** — what is already exported (the "studs" on existing bricks)
3. **All module headers** — the "Public API" section in each file's docstring

In `DESIGN.md`, the four-layer architecture was described:

```
Layer 1: HiveGraph (storage)
Layer 2: EventBus (transport)
Layer 3: Gossip (discovery)
Layer 4: Query deduplication
```

And an experimental result claimed **94% accuracy with a unified approach** vs. 47-57% for individual
layers. But no class in the codebase stitched those four layers together.

### Checklist for Gap Identification

- [ ] Does `DESIGN.md` describe a class or role that no file implements?
- [ ] Does any module comment reference something as "TODO" or describe something "delegated" elsewhere?
- [ ] Is there a `_promote_to_hive()` that does a direct call with no policy or routing decision?
- [ ] Does `__init__.py.__all__` list concepts that don't correspond to any file?

In this case: `cognitive_adapter._promote_to_hive()` called `hive.promote_fact()` directly —
hardcoded single-layer behavior with no policy, no event bus involvement, no gossip.
That was the architectural seam where the missing module belonged.

---

## 2. Defining the Module's Single Responsibility

The Bricks and Studs philosophy requires **one class, one job**. Before writing the class,
write one sentence:

> `HiveMindOrchestrator` routes fact operations through the appropriate architectural layer
> based on a configurable policy.

Everything in the module either:

- **Fulfills** that responsibility, or
- **Is removed**

To make the single responsibility concrete, answer these three questions:

| Question                           | Answer                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------ |
| What does this module **take in**? | A fact (concept + content + confidence) or a query                             |
| What does this module **produce**? | A result dict (promoted, event_published, gossip_triggered) or a list of facts |
| What does this module **NOT do**?  | Store facts itself, own the event bus, run background threads                  |

---

## 3. Designing the Interface (the "Studs")

Studs are what other bricks connect to. Design them before implementing anything.

### Start with the Protocol

If your module makes decisions based on external rules, extract those rules into a `Protocol`:

```python
@runtime_checkable
class PromotionPolicy(Protocol):
    def should_promote(self, fact: HiveFact, source_agent: str) -> bool: ...
    def should_gossip(self, fact: HiveFact, source_agent: str) -> bool: ...
    def should_broadcast(self, fact: HiveFact, source_agent: str) -> bool: ...
```

Then provide a `Default*` dataclass implementation using constants from `constants.py` —
no magic numbers in the module itself.

### Design the Return Dicts

Every method returns a dict with named keys, not a naked bool or tuple:

```python
# Good: caller knows what happened at each layer
{"fact_id": "hf_abc", "promoted": True, "event_published": True, "gossip_triggered": False}

# Bad: caller loses context
True
```

This pattern appears throughout the codebase (see `distributed.py`, `controller.py`).

---

## 4. Implementing (No Stubs)

A "stub" is any function that:

- Returns a hardcoded value (`return {}`)
- Has only `...` in the body
- Raises `NotImplementedError`

Every method must do real work. For `store_and_promote`:

```python
def store_and_promote(self, concept, content, confidence, tags=None):
    # Build the fact
    fact = HiveFact(...)

    # Layer 1: promote if policy allows
    if self._policy.should_promote(fact, self._agent_id):
        fact_id = self._hive_graph.promote_fact(self._agent_id, fact)
        promoted = True

    # Layer 2: publish event if promoted
    if promoted:
        self._event_bus.publish(make_event("FACT_PROMOTED", ...))

    # Layer 3: gossip if policy allows and peers exist
    if _HAS_GOSSIP and self._peers and self._policy.should_gossip(fact, ...):
        _run_gossip_round(self._hive_graph, self._peers, self._gossip_protocol)

    return {"fact_id": ..., "promoted": ..., "event_published": ..., "gossip_triggered": ...}
```

### Graceful Degradation Pattern

Use `try/except ImportError` at module level for optional dependencies:

```python
try:
    from .gossip import GossipProtocol, run_gossip_round as _run_gossip_round
    _HAS_GOSSIP = True
except ImportError:
    _HAS_GOSSIP = False
```

Then guard usage: `if _HAS_GOSSIP and ...`.
This pattern appears in every module in `hive_mind/`.

---

## 5. Wiring Into Existing Interfaces

The orchestrator connects to three existing interfaces:

| Interface                  | How It Connects                                                       |
| -------------------------- | --------------------------------------------------------------------- |
| `HiveGraph` (Layer 1)      | `hive_graph.promote_fact()` and `query_facts()` / `query_federated()` |
| `EventBus` (Layer 2)       | `event_bus.publish()`, `event_bus.poll()`, `event_bus.unsubscribe()`  |
| `GossipProtocol` (Layer 3) | `run_gossip_round(hive_graph, peers, protocol)`                       |

The orchestrator is injected with these at construction time — it does not create them.
This is the **dependency injection** pattern: let callers compose the system.

### Integration with CognitiveAdapter

The existing `cognitive_adapter._promote_to_hive()` still calls `hive.promote_fact()` directly.
To fully integrate the orchestrator, a caller can pass the orchestrator as the `hive_store`:

```python
# The orchestrator satisfies the duck-typed promote_fact interface
adapter = CognitiveAdapter(
    agent_name="agent_a",
    hive_store=orchestrator._hive_graph,  # or extend to inject orchestrator directly
)
```

Full CognitiveAdapter integration is a future enhancement tracked in DESIGN.md.

---

## 6. Writing the `__init__.py` Export

Always add new exports to `__init__.py` with a graceful try/except:

```python
try:
    from .orchestrator import (
        DefaultPromotionPolicy,
        HiveMindOrchestrator,
        PromotionPolicy,
    )
    __all__ += [
        "DefaultPromotionPolicy",
        "HiveMindOrchestrator",
        "PromotionPolicy",
    ]
except ImportError:
    _logger.debug("orchestrator module not available")
```

This keeps the package importable even if an optional dependency is missing.

---

## 7. Writing the Tests

Tests should validate **the contract, not the implementation**:

| Test category        | What to test                                            |
| -------------------- | ------------------------------------------------------- |
| Protocol compliance  | `isinstance(DefaultPromotionPolicy(), PromotionPolicy)` |
| Happy path           | High-confidence fact is promoted, event published       |
| Negative path        | Low-confidence fact is not promoted, no event           |
| Edge cases           | Confidence clamping, duplicate content deduplication    |
| Graceful degradation | No peers → gossip skipped with reason                   |
| Lifecycle            | `close()` does not raise, is idempotent                 |

Use pytest fixtures for repeated setup. Never test internal `_` attributes.

---

## 8. Summary: The Pattern for Future Modules

```
1. Read DESIGN.md + existing __init__.py.__all__
2. Find the seam: something described but not implemented
3. Write ONE responsibility sentence
4. Design the Protocol (if pluggable rules exist)
5. Design the return types (dicts with named keys)
6. Implement with graceful ImportError guards for optional deps
7. Wire to existing interfaces via constructor injection
8. Export from __init__.py with try/except
9. Write contract tests (29+ passing)
10. Document here
```

The key invariant: **a brick should be self-contained, regeneratable, and minimal**.
If you can't delete the module and recreate it from its interface alone, it's not a proper brick.

---

## Files Created

| File                                                          | Purpose                     |
| ------------------------------------------------------------- | --------------------------- |
| `src/amplihack/agents/goal_seeking/hive_mind/orchestrator.py` | The new module              |
| `tests/hive_mind/test_orchestrator.py`                        | Contract tests (29 passing) |
| `docs/hive_mind/MODULE_CREATION_GUIDE.md`                     | This document               |
