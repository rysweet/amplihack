---
title: How to maintain and extend the refactored LearningAgent
description: Task-oriented guidance for choosing the right module, changing behavior safely, and validating the split LearningAgent implementation.
last_updated: 2026-03-30
review_schedule: quarterly
owner: goal-seeking
doc_type: howto
related:
  - ../GOAL_SEEKING_AGENTS.md
  - ../concepts/learning-agent-module-architecture.md
  - ../reference/learning-agent-module-reference.md
  - ../tutorials/learning-agent-refactor-tutorial.md
---

# How to maintain and extend the refactored LearningAgent

This guide shows how to change the refactored `LearningAgent` without rebuilding a monolith by accident.

## Prerequisites

- [ ] You know whether your change affects learning, retrieval, temporal reasoning, or synthesis.
- [ ] You have read the [LearningAgent module architecture](../concepts/learning-agent-module-architecture.md).
- [ ] You are preserving the existing `LearningAgent` public methods.

## 1. Choose the owning module first

Pick the destination before touching code.

| If you are changing...                           | Edit...                   |
| ------------------------------------------------ | ------------------------- |
| question classification or routing metadata      | `intent_detector.py`      |
| temporal parsing or transition chain logic       | `temporal_reasoning.py`   |
| generated Python for temporal lookups            | `code_synthesis.py`       |
| arithmetic helpers or fact validation            | `knowledge_utils.py`      |
| batch extraction or storage                      | `learning_ingestion.py`   |
| which facts are retrieved                        | `retrieval_strategies.py` |
| final answer wording or completeness scoring     | `answer_synthesizer.py`   |
| construction, lifecycle, or compatibility wiring | `learning_agent.py`       |

If more than one row applies, start with the lowest-level module and keep the facade changes minimal.

## 2. Keep the facade thin

Use `learning_agent.py` only for:

- construction
- shared state
- action registration
- lifecycle
- delegation to owner modules

Do not move new business logic back into the facade just because it is already imported there.

## 3. Add behavior in the owner module

For example, to add a new retrieval strategy:

1. extend `retrieval_strategies.py`
2. reuse helpers from `knowledge_utils.py` or `temporal_reasoning.py` if needed
3. keep `answer_synthesizer.py` focused on answer generation, not retrieval
4. expose the new path by delegation, not by bypassing the facade

For example, to tune an intent:

1. update the label or metadata in `intent_detector.py`
2. keep the retrieval branch selection in `answer_synthesizer.py` or `retrieval_strategies.py`
3. add or update tests in the matching test file

## 4. Preserve the public API

The following signatures must stay callable:

```python
async def learn_from_content(self, content: str) -> dict[str, Any]
async def answer_question(
    self,
    question: str,
    question_level: str = "L1",
    return_trace: bool = False,
    _skip_qanda_store: bool = False,
    _force_simple: bool = False,
) -> str | tuple[str, ReasoningTrace | None]
async def answer_question_agentic(
    self,
    question: str,
    max_iterations: int = 3,
    return_trace: bool = False,
) -> str | tuple[str, ReasoningTrace | None]
def get_memory_stats(self) -> dict[str, Any]
def flush_memory(self) -> None
def close(self) -> None
```

Also preserve these compatibility expectations:

- `LearningAgent` still imports from `learning_agent.py`
- `GoalSeekingAgent` callers do not need code changes
- `__init__.py` behavior stays backward compatible

## 5. Update the module-aligned tests

Put the test next to the responsibility you changed.

| Change type                      | Test file                          |
| -------------------------------- | ---------------------------------- |
| constructor or lifecycle         | `test_learning_agent_core.py`      |
| ingestion or storage             | `test_learning_agent_ingestion.py` |
| retrieval logic                  | `test_learning_agent_retrieval.py` |
| temporal or generated-code logic | `test_learning_agent_temporal.py`  |
| intent or arithmetic behavior    | `test_math_intent.py`              |
| answer refinement behavior       | `test_agentic_answer_mode.py`      |
| top-level agent compatibility    | `test_goal_seeking_agent.py`       |

## 6. Run focused validation

Run the goal-seeking checks from the repository root:

```bash
uv run ruff check src/amplihack/agents/goal_seeking tests/agents/goal_seeking
uv run pyright src/amplihack/agents/goal_seeking tests/agents/goal_seeking
uv run python -m pytest tests/agents/goal_seeking/
```

If you only changed one area, run its module-aligned tests first and then run the full goal-seeking test suite.

## Configuration tasks

### Configure a specific model

Pass `model` when constructing the agent:

```python
from amplihack.agents.goal_seeking.learning_agent import LearningAgent

agent = LearningAgent(
    agent_name="release-notes",
    model="claude-opus-4-6",
)
```

If you omit `model`, `LearningAgent` falls back to `EVAL_MODEL`.

### Enable hierarchical memory

```python
from pathlib import Path

from amplihack.agents.goal_seeking.learning_agent import LearningAgent

agent = LearningAgent(
    agent_name="timeline-analyst",
    storage_path=Path("./memory"),
    use_hierarchical=True,
)
```

When hierarchical mode is enabled, the agent stores richer provenance and temporal metadata through the cognitive or hierarchical memory adapters.

### Use a prompt variant

```python
from amplihack.agents.goal_seeking.learning_agent import LearningAgent

agent = LearningAgent(
    agent_name="variant-check",
    prompt_variant=3,
)
```

Use prompt variants for evaluation or controlled experiments. The refactor does not change the prompt-variant interface.

## Common maintenance patterns

### Add a new temporal shortcut

Edit `temporal_reasoning.py` when the answer can be derived from stored transitions without full synthesis.

Use this when:

- the query asks for latest, earliest, before, after, or delta-style answers
- the answer is deterministic from stored state changes

### Add a new aggregation retrieval

Edit `retrieval_strategies.py` when the question is about:

- counts
- unique entities
- list-all enumerations
- meta-memory summaries

Keep factual aggregation separate from final narrative synthesis.

### Change answer wording

Edit `answer_synthesizer.py` when you are changing:

- prompt templates
- completeness evaluation criteria
- how retrieved facts are combined into final prose

Do not move answer-formatting rules into retrieval code.

## Troubleshooting

### Circular imports appear after extraction

**Symptom**: importing `LearningAgent` pulls higher-level modules back into leaf modules.

**Fix**:

1. move the helper to the lower-level owner module
2. keep `learning_agent.py` as the importer of last resort
3. avoid leaf modules importing the facade

### The facade starts growing again

**Symptom**: new helper methods accumulate in `learning_agent.py`.

**Fix**: move the helper to the responsible module and delegate from the facade.

### A new test does not have an obvious home

**Symptom**: a test touches multiple modules.

**Fix**: place it with the module that owns the behavior being asserted. Use higher-level compatibility tests only when the behavior is genuinely cross-cutting.

## See also

- [LearningAgent module reference](../reference/learning-agent-module-reference.md)
- [LearningAgent module architecture](../concepts/learning-agent-module-architecture.md)
- [Tutorial: trace the refactored LearningAgent end to end](../tutorials/learning-agent-refactor-tutorial.md)
