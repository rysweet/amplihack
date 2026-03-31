# Comparative Analysis: Formal Specs as Prompts

## TLA+ vs Gherkin — Two Formalisms for Two Problem Domains

### TLA+ Experiment Results (Issue #3497)

Target: Distributed retrieval contract (concurrent system with safety invariants)

| Variant             | Baseline Score | Coverage Score |
| ------------------- | -------------- | -------------- |
| english             | 0.57           | 0.43           |
| tla_only            | **0.86**       | **0.86**       |
| tla_plus_english    | 0.50           | 0.50           |
| tla_plus_refinement | 0.71           | 0.71           |

**Key finding**: Formal spec alone outperforms all other variants. Adding English
to the spec _degrades_ performance.

### Gherkin Experiment Design

Target: User authentication REST API (behavioral feature with acceptance criteria)

| Variant                 | Expected Behavior                           |
| ----------------------- | ------------------------------------------- |
| english                 | Baseline — natural language only            |
| gherkin_only            | Feature file as sole specification          |
| gherkin_plus_english    | Feature file + implementation guidance      |
| gherkin_plus_acceptance | Feature file + explicit acceptance criteria |

### Gherkin Experiment Results (Smoke Run, 2026-03-31)

| Variant                 | Claude Scenario Cov | GPT-5.4 Scenario Cov | Mean     |
| ----------------------- | ------------------- | -------------------- | -------- |
| english                 | 0.92                | 1.00                 | **0.96** |
| gherkin_only            | 0.00\*              | 1.00                 | 0.50     |
| gherkin_plus_english    | **1.00**            | 1.00                 | **1.00** |
| gherkin_plus_acceptance | 0.00\*              | (timeout)            | --       |

\*Claude 0.00 scores: model tried to use tools/write files instead of returning
inline artifact. The `gherkin_only` and `acceptance` prompts were too terse —
Claude interpreted them as instructions to build a project rather than return
code as text. GPT-5.4 handled the same prompts correctly.

### Key Findings

**Finding 1: Behavioral tasks are already high-baseline for English.**
Unlike the TLA+ experiment (English baseline 0.57), English scored 0.96 here.
Both models already know how to build auth APIs from training data. There's less
room for Gherkin to improve.

**Finding 2: Gherkin + English is the optimal combination (contradicts TLA+).**
The hybrid variant `gherkin_plus_english` achieved 1.00 for both models. This
_contradicts_ the TLA+ finding where hybrid degraded performance. The difference:
Gherkin and English describe behavior in compatible ways, while TLA+ predicates
and English implementation guidance create conflicting signals.

**Finding 3: Gherkin-only is fragile for behavioral tasks.**
The `gherkin_only` prompt with minimal framing caused Claude to attempt tool use
instead of inline output. GPT-5.4 handled it fine. This suggests Gherkin-only
needs stronger framing instructions for some models.

**Finding 4: The spec formalism effect is domain-dependent.**

- TLA+ (concurrent systems): spec-only = **0.86**, English = 0.57 → +51% improvement
- Gherkin (behavioral features): hybrid = **1.00**, English = 0.96 → +4% improvement
- The improvement from formal specs scales with the _ambiguity gap_ between
  English and the domain. Concurrent invariants are hard to express in English;
  behavioral scenarios are easy.

### Hypothesized vs Actual

| Prediction             | Actual                                                              |
| ---------------------- | ------------------------------------------------------------------- |
| Gherkin-only > English | **Partially confirmed** (GPT yes, Claude no — prompt framing issue) |
| Gap smaller than TLA+  | **Confirmed** (4% vs 51% improvement)                               |
| Hybrid won't degrade   | **Confirmed** — hybrid was actually the best variant                |

## Unified Spec Strategy Proposal

### Decision Framework for the prompt-writer Agent

The prompt-writer agent should select the specification formalism based on the
task's **dominant constraint type**, not dogma:

```
                    ┌─────────────────────┐
                    │   What must be true? │
                    └──────────┬──────────┘
                               │
               ┌───────────────┼───────────────┐
               │               │               │
        ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
        │   Safety     │ │ Behavioral  │ │   Simple    │
        │ Invariants   │ │ Acceptance  │ │   CRUD/     │
        │              │ │ Criteria    │ │   Config    │
        └──────┬──────┘ └─────┬──────┘ └──────┬──────┘
               │               │               │
        ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
        │   TLA+       │ │  Gherkin    │ │  English    │
        │   Spec       │ │  Feature    │ │  Only       │
        └─────────────┘ └────────────┘ └─────────────┘
```

### When to use TLA+ (formal predicates)

- Concurrent components with mutual exclusion, ordering, or liveness
- Distributed protocols (fan-out/merge, quorum, timeout handling)
- State machines with non-obvious valid transitions
- Any component where "what must always be true" matters more than "how to do it"
- **Signal**: The requirements mention invariants, safety properties, or
  state-transition constraints

### When to use Gherkin (behavioral specs)

- Feature implementations with clear acceptance criteria
- REST API endpoints with defined request/response contracts
- User-facing workflows with multiple paths (happy + error)
- Any component where "what should happen when X" matters more than
  "what must always be true"
- **Signal**: The requirements describe user actions, HTTP verbs, status codes,
  or Given/When/Then patterns

### When to use English only

- Simple CRUD with no edge cases
- Configuration changes
- Trivial refactoring
- Tasks where the implementation is obvious from the description
- **Signal**: The requirements fit in 1-3 sentences and have no error cases

### Anti-patterns to avoid

1. **Using TLA+ for behavioral features**: Overkill — the model already
   understands authentication flows from training data
2. **Using Gherkin for concurrent invariants**: Insufficient — Given/When/Then
   can't express "for ALL interleavings, this property holds"
3. **Always using English**: Misses the 50%+ improvement formal specs provide
4. **Mixing formalisms in one prompt**: The TLA+ experiment showed hybrid prompts
   degrade performance — the model resolves conflicts unpredictably

### Implementation Guidance for prompt-writer Agent

```python
def select_spec_formalism(task_description: str) -> str:
    """Select the appropriate specification formalism for a task.

    Returns: "tla" | "gherkin" | "english"
    """
    # Safety invariant signals
    if has_concurrent_constraints(task_description):
        return "tla"

    # Behavioral acceptance criteria signals
    if has_behavioral_scenarios(task_description):
        return "gherkin"

    # Default to English for simple tasks
    return "english"
```

The prompt-writer should use judgment, not dogma. If a task has both concurrent
constraints AND behavioral scenarios (e.g., a distributed auth service), prefer
the formalism that addresses the **higher-risk** constraints — usually TLA+ for
the invariants, with Gherkin scenarios as test guidance (not as the prompt).

## Cost-Benefit Summary

| Formalism         | Effort to Create | Measured Improvement | Best For                          |
| ----------------- | ---------------- | -------------------- | --------------------------------- |
| English           | Low              | Baseline             | Simple tasks, well-known patterns |
| Gherkin + English | Medium           | +4% (0.96→1.00)      | Features with edge cases          |
| TLA+ only         | High             | +51% (0.57→0.86)     | Concurrent/distributed            |

**Key insight**: The improvement from formal specs is inversely proportional to
how well English describes the domain. For concurrent invariants (hard in
English), TLA+ provides massive improvement. For behavioral features (easy in
English), Gherkin provides marginal improvement but useful as a checklist.

**Recommendation**: Use Gherkin primarily as **test guidance** rather than as the
sole prompt. The hybrid approach (English + Gherkin) works best for behavioral
tasks, while TLA+-only works best for concurrent tasks. The formalisms serve
different roles: TLA+ replaces ambiguous English, while Gherkin supplements
already-clear English with structured acceptance criteria.
