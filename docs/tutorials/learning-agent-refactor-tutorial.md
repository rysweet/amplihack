---
title: "Tutorial: Trace the refactored LearningAgent end to end"
description: Learn the refactored LearningAgent by loading facts, asking direct and temporal questions, and mapping each step to its owning module.
last_updated: 2026-03-30
review_schedule: quarterly
owner: goal-seeking
doc_type: tutorial
related:
  - ../GOAL_SEEKING_AGENTS.md
  - ../concepts/learning-agent-module-architecture.md
  - ../howto/maintain-learning-agent-modules.md
  - ../reference/learning-agent-module-reference.md
---

# Tutorial: Trace the refactored LearningAgent end to end

In this tutorial, we will create a small `LearningAgent`, teach it a few timeline facts, ask direct and temporal questions, and connect each step back to the module that owns the behavior.

## What you will learn

- how to construct a `LearningAgent` after the refactor
- how learning flows through ingestion and storage
- how direct questions and temporal questions follow different paths
- how to map observed behavior back to the owning module

## Prerequisites

- Python environment with amplihack available
- familiarity with async Python
- basic understanding of goal-seeking agents

## Time required

Approximately 20 minutes.

---

## Step 1: Create a small tutorial script

Create `tutorial_learning_agent.py`:

```python
import asyncio
from pathlib import Path

from amplihack.agents.goal_seeking.learning_agent import LearningAgent


CONTENT = """
Title: Release timeline
Project Atlas shipped version 1.0 in January 2026.
Project Atlas shipped version 1.1 in February 2026.
Project Atlas shipped version 1.2 in March 2026.
The March release added 14 workflow fixes.
"""


async def main() -> None:
    agent = LearningAgent(
        agent_name="tutorial-learning-agent",
        storage_path=Path("./tutorial-memory"),
        use_hierarchical=True,
    )

    try:
        learning_result = await agent.learn_from_content(CONTENT)
        print("Learned:", learning_result)

        recall_answer = await agent.answer_question(
            "What version shipped in February 2026?"
        )
        print("Recall:", recall_answer)

        temporal_answer = await agent.answer_question_agentic(
            "How did the Project Atlas version change from January 2026 to March 2026?"
        )
        print("Temporal:", temporal_answer)

        print("Stats:", agent.get_memory_stats())
    finally:
        agent.close()


asyncio.run(main())
```

**Expected result**: you have a complete, minimal script that exercises learning, direct answering, temporal answering, and memory statistics.

## Step 2: Run the tutorial script

```bash
uv run python tutorial_learning_agent.py
```

You should see four outputs:

- a learning result dictionary
- a direct-answer response
- an agentic temporal response
- memory statistics

---

## Step 3: Map the learning path to modules

The call to `learn_from_content()` now crosses a small number of ownership boundaries:

1. `learning_agent.py` receives the public method call.
2. `learning_ingestion.py` prepares the fact batch.
3. `learning_ingestion.py` detects source labels and temporal metadata.
4. `learning_ingestion.py` stores facts and the optional summary concept map.
5. the configured memory backend persists the result.

The important point is that callers still use the old method name. The refactor changes the implementation layout, not the public learning surface.

## Step 4: Map the direct answer path

The call to:

```python
await agent.answer_question("What version shipped in February 2026?")
```

follows this path:

1. `learning_agent.py` delegates the request.
2. `intent_detector.py` classifies the question.
3. `retrieval_strategies.py` selects the retrieval path.
4. `answer_synthesizer.py` turns the retrieved facts into the final answer.

For a direct recall question, temporal code generation is usually not involved.

## Step 5: Map the temporal answer path

The call to:

```python
await agent.answer_question_agentic(
    "How did the Project Atlas version change from January 2026 to March 2026?"
)
```

adds the temporal and refinement layers:

1. `answer_synthesizer.py` runs the standard single-shot answer first.
2. `intent_detector.py` marks the question as temporal.
3. `retrieval_strategies.py` retrieves candidate facts.
4. `temporal_reasoning.py` assembles transition chains or direct temporal lookups.
5. `code_synthesis.py` generates deterministic Python when the temporal lookup is too complex for a simple shortcut.
6. `answer_synthesizer.py` evaluates completeness and re-synthesizes only if more facts are needed.

**Checkpoint**: you should now be able to explain why temporal logic lives outside the facade.

## Step 6: Inspect the module layout

After the refactor, the goal-seeking package contains these primary files:

```text
src/amplihack/agents/goal_seeking/
├── learning_agent.py
├── learning_ingestion.py
├── answer_synthesizer.py
├── retrieval_strategies.py
├── intent_detector.py
├── temporal_reasoning.py
├── code_synthesis.py
└── knowledge_utils.py
```

Keep this rule in mind:

- the facade owns state and delegation
- the leaf modules own behavior

---

## Step 7: Run the goal-seeking validation suite

From the repository root:

```bash
uv run ruff check src/amplihack/agents/goal_seeking tests/agents/goal_seeking
uv run pyright src/amplihack/agents/goal_seeking tests/agents/goal_seeking
uv run python -m pytest tests/agents/goal_seeking/
```

If you only changed a temporal path, start with:

```bash
uv run python -m pytest tests/agents/goal_seeking/test_learning_agent_temporal.py
```

**Expected result**: the module-aligned tests confirm that the refactor preserved behavior while keeping responsibilities separated.

## Summary

You used the refactored `LearningAgent` exactly as before, but the internal path is now clearer:

- learning work flows through `learning_ingestion.py`
- question classification lives in `intent_detector.py`
- retrieval stays in `retrieval_strategies.py`
- temporal logic lives in `temporal_reasoning.py` and `code_synthesis.py`
- final answer generation stays in `answer_synthesizer.py`

## Next steps

- Read the [LearningAgent module architecture](../concepts/learning-agent-module-architecture.md) for the rationale behind the split.
- Use the [LearningAgent module reference](../reference/learning-agent-module-reference.md) when you need exact signatures or ownership rules.
- Follow [How to maintain and extend the refactored LearningAgent](../howto/maintain-learning-agent-modules.md) before making changes.
