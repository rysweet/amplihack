# Unified Spec Strategy: When to Use What

**Based on**: TLA+ experiment (#3497) + Gherkin experiment (#3962)

## The Decision Framework

The prompt-writer agent should select specification formalism based on two axes:

1. **Task novelty**: How well does the model's training data cover this task?
2. **Constraint complexity**: Are there non-obvious invariants or state rules?

```
                    High Constraint Complexity
                           │
              TLA+/Formal  │  TLA+ + Gherkin
              Predicates   │  (both formalisms)
                           │
   Low Task ───────────────┼─────────────── High Task
   Novelty                 │                Novelty
                           │
              Plain        │  Gherkin/BDD
              English      │  Scenarios
                           │
                    Low Constraint Complexity
```

## Quadrant Definitions

### Q1: Plain English (Low Novelty + Low Constraints)

**When**: CRUD operations, standard REST APIs, common patterns (auth, pagination,
file upload), UI components, data transformations.

**Why**: The model has extensive training examples. Formal specs add overhead
without adding signal. English is sufficient and faster to write.

**Evidence**: User auth API scored 1.0 with English alone (this experiment).

**Example tasks**:

- "Add a user registration endpoint"
- "Implement a todo list API"
- "Create a pagination component"

### Q2: TLA+ / Formal Predicates (Low Novelty + High Constraints)

**When**: Well-known patterns BUT with safety invariants — mutual exclusion,
ordering guarantees, resource accounting, state machines with subtle transition
rules.

**Why**: The model knows the pattern but may miss subtle constraints. Formal
predicates make invariants unambiguous.

**Evidence**: TLA+ specs doubled scores for distributed retrieval (0.43 → 0.86).

**Example tasks**:

- "Implement a distributed lock with mutual exclusion guarantee"
- "Build a request pipeline where failures must be surfaced, not swallowed"
- "Create a state machine where terminal states are irreversible"

### Q3: Gherkin/BDD Scenarios (High Novelty + Low Constraints)

**When**: Domain-specific features where the model lacks training examples, but
the constraints are behavioral (request/response contracts, business rules) not
state invariants.

**Why**: Gherkin scenarios enumerate the exact cases the code must handle. For
novel domains, this enumeration prevents the model from guessing wrong.

**Expected evidence**: Not yet validated in this experiment (user auth was too
common). Future experiment should use a novel domain.

**Example tasks**:

- "Implement the billing adjustment workflow for our custom ERP"
- "Build the specimen tracking API for the lab management system"
- "Create the compliance check endpoints for our industry-specific regulations"

### Q4: TLA+ + Gherkin (High Novelty + High Constraints)

**When**: Novel domain with both behavioral contracts AND state/concurrency
invariants. Rare but important.

**Why**: Gherkin covers the "what should happen" and TLA+ covers the "what must
always/never be true."

**Example tasks**:

- "Implement a distributed auction system with fairness guarantees"
- "Build a clinical trial randomization service with blinding invariants"

## Decision Heuristic for the prompt-writer Agent

```python
def select_spec_formalism(task_description: str) -> str:
    """Heuristic for the prompt-writer agent."""

    has_state_invariants = any(keyword in task_description.lower() for keyword in [
        "must never", "must always", "mutual exclusion", "atomicity",
        "ordering guarantee", "state machine", "concurrent",
        "distributed", "eventually", "safety invariant",
    ])

    is_novel_domain = not any(keyword in task_description.lower() for keyword in [
        "crud", "authentication", "login", "todo", "blog",
        "pagination", "file upload", "shopping cart", "chat",
    ])

    if has_state_invariants and is_novel_domain:
        return "tla_plus_gherkin"  # Both formalisms
    elif has_state_invariants:
        return "tla_plus"  # Formal predicates
    elif is_novel_domain:
        return "gherkin"  # Behavioral scenarios
    else:
        return "english"  # Plain language
```

## What This Experiment Revealed

1. **Formal specs are not universally beneficial.** They help when they add
   information the model doesn't already have.

2. **The TLA+ finding (spec > English) was driven by task novelty**, not by
   the inherent superiority of formal notation. User auth shows that for
   well-known tasks, English is just as good.

3. **Hybrid prompts (spec + English) can be worse** than spec alone — confirmed
   in both experiments. The TLA+ hybrid scored 0.43 (same as English). The
   explanation: when two description modes conflict, the model resolves the
   conflict unpredictably.

4. **The proportionality principle applies to specs too.** Don't formalize
   what the model already knows. Invest specification effort where it has
   the highest marginal return: novel domains and subtle constraints.

## Recommended Update to prompt-writer Agent

Add this to the Constraint Recognition Heuristic:

```markdown
### Spec Formalism Selection (added from #3962 experiment)

Before writing formal constraints, assess task novelty:

**Skip formalization when:**

- Task is a common web pattern (auth, CRUD, pagination, chat)
- Model training data likely covers the task comprehensively
- No state/concurrency invariants to express

**Use Gherkin/BDD when:**

- Domain-specific behavior that models haven't seen before
- Complex business rules with many edge cases
- Clear request/response contracts to enumerate

**Use TLA+/formal predicates when:**

- Concurrent or distributed state management
- Safety/liveness invariants that must hold
- State machines with non-obvious valid transitions

**Use both when:**

- Novel domain + state invariants (rare)
```
