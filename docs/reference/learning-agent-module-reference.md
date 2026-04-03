---
title: LearningAgent Module Reference
description: Public API, configuration surface, file ownership, and validation references for the refactored LearningAgent.
last_updated: 2026-03-30
review_schedule: quarterly
owner: goal-seeking
doc_type: reference
related:
  - ../GOAL_SEEKING_AGENTS.md
  - ../concepts/learning-agent-module-architecture.md
  - ../howto/maintain-learning-agent-modules.md
  - ../tutorials/learning-agent-refactor-tutorial.md
---

# LearningAgent Module Reference

## Overview

`LearningAgent` is the shared goal-seeking engine responsible for:

- learning facts from content
- retrieving knowledge from memory
- reasoning about temporal changes
- synthesizing final answers with an LLM

The refactor preserves the existing public API while moving implementation details into focused modules.

## Compatibility imports

| Import                                                                   | Status                               | Notes                                                                       |
| ------------------------------------------------------------------------ | ------------------------------------ | --------------------------------------------------------------------------- |
| `from amplihack.agents.goal_seeking.learning_agent import LearningAgent` | Primary compatibility path           | Stable import path for direct callers                                       |
| `from amplihack.agents.goal_seeking import LearningAgent`                | Supported for backward compatibility | Import works even though `LearningAgent` is not added to `__all__`          |
| `from amplihack.agents.goal_seeking import GoalSeekingAgent`             | Preferred public entry point         | `GoalSeekingAgent` delegates learning and answering work to `LearningAgent` |

## Constructor

```python
LearningAgent(
    agent_name: str = "learning_agent",
    model: str | None = None,
    storage_path: Path | None = None,
    use_hierarchical: bool = False,
    prompt_variant: int | None = None,
    **kwargs: Any,
)
```

### Constructor parameters

| Parameter          | Type           | Default            | Description                                                                 |
| ------------------ | -------------- | ------------------ | --------------------------------------------------------------------------- |
| `agent_name`       | `str`          | `"learning_agent"` | Memory namespace and runtime identity                                       |
| `model`            | `str \| None`  | `None`             | Explicit LLM model override                                                 |
| `storage_path`     | `Path \| None` | `None`             | Custom memory storage location                                              |
| `use_hierarchical` | `bool`         | `False`            | Use cognitive or hierarchical memory adapters instead of the flat retriever |
| `prompt_variant`   | `int \| None`  | `None`             | Load a synthesis prompt variant instead of the default prompt               |
| `**kwargs`         | `Any`          | -                  | Reserved compatibility surface for callers and wrappers                     |

## Public methods

### `learn_from_content`

```python
async def learn_from_content(self, content: str) -> dict[str, Any]
```

Extracts facts from content, attaches source and temporal metadata, stores the resulting facts, and optionally stores a summary concept map.

**Returns**

| Key               | Meaning                                    |
| ----------------- | ------------------------------------------ |
| `facts_extracted` | Number of facts extracted from the content |
| `facts_stored`    | Number of facts written to memory          |
| `content_summary` | Short summary of the learned content       |

### `answer_question`

```python
async def answer_question(
    self,
    question: str,
    question_level: str = "L1",
    return_trace: bool = False,
    _skip_qanda_store: bool = False,
    _force_simple: bool = False,
) -> str | tuple[str, ReasoningTrace | None]
```

Runs the standard answer pipeline:

1. detect intent
2. select retrieval strategy
3. perform math or temporal preprocessing when needed
4. synthesize the final answer

**Parameters**

| Parameter           | Type   | Default  | Description                                                               |
| ------------------- | ------ | -------- | ------------------------------------------------------------------------- |
| `question`          | `str`  | required | Question to answer                                                        |
| `question_level`    | `str`  | `"L1"`   | Difficulty hint for prompt selection and synthesis style                  |
| `return_trace`      | `bool` | `False`  | Return a `ReasoningTrace` alongside the answer                            |
| `_skip_qanda_store` | `bool` | `False`  | Internal flag used to skip writing Q and A history facts                  |
| `_force_simple`     | `bool` | `False`  | Internal flag used to force exhaustive simple retrieval in fallback cases |

### `answer_question_agentic`

```python
async def answer_question_agentic(
    self,
    question: str,
    max_iterations: int = 3,
    return_trace: bool = False,
) -> str | tuple[str, ReasoningTrace | None]
```

Runs the single-shot answer pipeline first, checks completeness, searches for missing facts, and re-synthesizes only when that adds information.

### `get_memory_stats`

```python
def get_memory_stats(self) -> dict[str, Any]
```

Returns memory statistics from the active backend.

### `flush_memory`

```python
def flush_memory(self) -> None
```

Flushes memory caches without discarding stored knowledge.

### `close`

```python
def close(self) -> None
```

Closes the underlying memory backend and releases agent resources.

## Module ownership map

The eight primary files are the stable ownership boundaries for the refactor.

| File                      | Owns                                                                       |
| ------------------------- | -------------------------------------------------------------------------- |
| `learning_agent.py`       | constructor, shared state, lifecycle, retry helpers, public delegation     |
| `learning_ingestion.py`   | ingestion pipeline, fact batch preparation, source labels, summary storage |
| `answer_synthesizer.py`   | answer synthesis, completeness evaluation, prompt assembly                 |
| `retrieval_strategies.py` | retrieval selection, simple/entity/concept/aggregation strategies          |
| `intent_detector.py`      | intent classification and routing metadata                                 |
| `temporal_reasoning.py`   | transition chains, temporal lookups, temporal parsing                      |
| `code_synthesis.py`       | generated Python for hard temporal reasoning cases                         |
| `knowledge_utils.py`      | arithmetic validation, knowledge explanation, fact verification helpers    |

## Expected method placement

The refactor keeps these methods with their owning modules.

### `learning_ingestion.py`

- `learn_from_content`
- `_truncate_learning_content`
- `_extract_source_label`
- `_build_store_fact_kwargs`
- `_build_summary_store_kwargs`
- `prepare_fact_batch`
- `store_fact_batch`
- `_store_summary_concept_map`
- `_detect_temporal_metadata_fast`
- `_detect_temporal_metadata`
- `_extract_facts_with_llm`

### `intent_detector.py`

- `_detect_intent`
- `SIMPLE_INTENTS`
- `AGGREGATION_INTENTS`

### `temporal_reasoning.py`

- `_transition_chain_from_facts`
- `retrieve_transition_chain`
- `_extract_temporal_state_values`
- `_collapse_change_count_transitions`
- `_collapse_temporal_lookup_transitions`
- `_format_temporal_lookup_answer`
- `_parse_temporal_index`
- `_heuristic_temporal_entity_field`
- `_should_short_circuit_temporal_answer`

### `code_synthesis.py`

- `temporal_code_synthesis`
- `_code_generation_tool`

### `knowledge_utils.py`

- `_validate_arithmetic`
- `_compute_math_result`
- `_explain_knowledge`
- `_find_knowledge_gaps`
- `_verify_fact`
- `get_memory_stats`

### `retrieval_strategies.py`

- `_simple_retrieval`
- `_keyword_expanded_retrieval`
- `_entity_retrieval`
- `_concept_retrieval`
- `_aggregation_retrieval`
- `_get_summary_nodes`
- and the rest of the retrieval-adjacent helpers that support those strategies

### `answer_synthesizer.py`

- `answer_question`
- `answer_question_agentic`
- `_evaluate_answer_completeness`
- `_synthesize_with_llm`

## Registered actions

The facade still registers the same high-level actions on `ActionExecutor`.

| Action                | Backing behavior                                 |
| --------------------- | ------------------------------------------------ |
| `read_content`        | content ingestion input helper                   |
| `search_memory`       | memory lookup through the active backend         |
| `synthesize_answer`   | LLM synthesis via `answer_synthesizer.py`        |
| `calculate`           | deterministic arithmetic helper                  |
| `code_generation`     | temporal code generation via `code_synthesis.py` |
| `explain_knowledge`   | topic explanation helper                         |
| `find_knowledge_gaps` | knowledge gap analysis                           |
| `verify_fact`         | fact validation against stored knowledge         |

## Configuration surface

The refactor does not add new runtime configuration. It preserves the existing knobs.

### Constructor-driven configuration

| Knob               | Scope                    | Effect                                                              |
| ------------------ | ------------------------ | ------------------------------------------------------------------- |
| `model`            | extraction and synthesis | Chooses the LLM used for prompts and completions                    |
| `storage_path`     | memory backend           | Changes where memory data is stored                                 |
| `use_hierarchical` | memory backend           | Selects `CognitiveAdapter` or `FlatRetrieverAdapter` when available |
| `prompt_variant`   | synthesis                | Loads a variant prompt for eval or experimentation                  |

### Environment variables

| Variable     | Used when          | Effect                              |
| ------------ | ------------------ | ----------------------------------- |
| `EVAL_MODEL` | `model` is omitted | Provides the default LLM model name |

No new environment variables are introduced by the module split.

## Internal helper modules

Private support files may exist to keep the primary modules small. Two common patterns are expected:

- retrieval support helpers such as `_retrieval_core.py`, `_retrieval_entity.py`, and `_retrieval_meta.py`
- synthesis support helpers such as `_answer_prompting.py`

These files stay private implementation details. Callers should continue to target `LearningAgent`, not individual support modules.

## Test layout

| Test file                          | Scope                                 |
| ---------------------------------- | ------------------------------------- |
| `test_learning_agent_core.py`      | constructor, retry, lifecycle         |
| `test_learning_agent_ingestion.py` | ingestion and storage                 |
| `test_learning_agent_retrieval.py` | retrieval strategies and fallbacks    |
| `test_learning_agent_temporal.py`  | temporal reasoning and code synthesis |
| `test_math_intent.py`              | math and intent behavior              |
| `test_agentic_answer_mode.py`      | answer refinement behavior            |
| `test_goal_seeking_agent.py`       | higher-level agent compatibility      |

## Validation commands

The refactored LearningAgent is validated with focused checks:

```bash
uv run ruff check src/amplihack/agents/goal_seeking tests/agents/goal_seeking
uv run pyright src/amplihack/agents/goal_seeking tests/agents/goal_seeking
uv run python -m pytest tests/agents/goal_seeking/
```

## Related docs

- [Understanding the LearningAgent module architecture](../concepts/learning-agent-module-architecture.md)
- [How to maintain and extend the refactored LearningAgent](../howto/maintain-learning-agent-modules.md)
- [Tutorial: trace the refactored LearningAgent end to end](../tutorials/learning-agent-refactor-tutorial.md)
