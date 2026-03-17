# Design: LearningAgent Integration into Goal-Seeking Agent Generator

**Status**: Draft — Awaiting Review
**Branch**: design/learning-agent-generator-integration
**Date**: 2026-03-17
**Author**: Architecture Investigation + Multi-Agent Review

---

## 1. Executive Summary

This document specifies how `LearningAgent` should become a **first-class structural
component** of every agent emitted by `goal_agent_generator`, so that all
benchmarked agents are consistently generated as goal-seeking-agent variants
across all four supported SDKs (claude, copilot, microsoft, mini).

Today the generator emits agents that use `AutoMode` and `amplihack-memory-lib`
experience storage — a different memory stack from the production eval path
(`GoalSeekingAgent` → `LearningAgent` → `CognitiveAdapter` / Kuzu).
This split causes benchmark agents to diverge from the production agent
architecture and makes cross-SDK comparisons unreliable.

The proposed change is **additive and non-breaking**: the generator gains a new
`--use-learning-agent` flag (defaulting to `True`) that wires the generated
`main.py` entry point through `sdk_adapters.create_agent()` instead of the bare
`AutoMode` launcher. No running eval infrastructure is touched.

---

## 2. Architecture Investigation Summary

### 2.1 Component Map

```
src/amplihack/
├── agents/
│   └── goal_seeking/
│       ├── goal_seeking_agent.py   ← OODA wrapper (production eval)
│       ├── learning_agent.py       ← Core learning engine (LLM extraction/synthesis)
│       ├── cognitive_adapter.py    ← Memory backend (Kuzu graph DB)
│       ├── hierarchical_memory.py  ← Graph-RAG memory tier
│       ├── memory_retrieval.py     ← MemoryRetriever (used by SDK adapters)
│       ├── agentic_loop.py         ← PERCEIVE→REASON→ACT→LEARN loop
│       └── sdk_adapters/
│           ├── base.py             ← GoalSeekingAgent ABC + lazy LearningAgent cache
│           ├── claude_sdk.py       ← ClaudeGoalSeekingAgent
│           ├── copilot_sdk.py      ← CopilotGoalSeekingAgent
│           ├── microsoft_sdk.py    ← MicrosoftGoalSeekingAgent
│           └── factory.py          ← create_agent(name, sdk=...) entry point
└── goal_agent_generator/
    ├── prompt_analyzer.py          ← NL → GoalDefinition
    ├── objective_planner.py        ← GoalDefinition → ExecutionPlan
    ├── skill_synthesizer.py        ← ExecutionPlan → List[SkillDefinition]
    ├── agent_assembler.py          ← → GoalAgentBundle (enable_memory uses memory-lib)
    ├── packager.py                 ← GoalAgentBundle → standalone agent directory
    └── cli.py                      ← amplihack new --file … --sdk …
```

### 2.2 The Two "GoalSeekingAgent" Classes (Name Collision)

There are **two distinct classes** with overlapping names:

| Class | Location | Role |
|---|---|---|
| `GoalSeekingAgent` (OODA) | `agents/goal_seeking/goal_seeking_agent.py` | Production eval agent. Hard-wraps `LearningAgent`. Used by the 5000-turn Azure eval. |
| `GoalSeekingAgent` (ABC) | `agents/goal_seeking/sdk_adapters/base.py` | Abstract base for the four SDK adapters. Lazily caches a `LearningAgent` for `learn_from_content` / `answer_question`. |

The `goal_agent_generator` uses **neither**. It generates a `main.py` that
imports `amplihack.launcher.auto_mode.AutoMode` and runs the agent through
Claude Code's auto-mode loop.

### 2.3 LearningAgent Integration Status

| Path | LearningAgent wired? | Notes |
|---|---|---|
| `goal_seeking_agent.py` (eval) | **Yes — always** | Instantiated in `__init__`, required. |
| `sdk_adapters/base.py` (SDK ABC) | **Yes — lazily** | `_get_learning_agent()` cache, created on first `learn_from_content` / `answer_question` call. |
| `sdk_adapters/claude_sdk.py` | **Inherited** | Via `base.py` lazy cache. |
| `sdk_adapters/copilot_sdk.py` | **Inherited** | Via `base.py` lazy cache. |
| `sdk_adapters/microsoft_sdk.py` | **Inherited** | Via `base.py` lazy cache. |
| `sdk_adapters/factory.py` | **Inherited** | Calls concrete subclass constructors. |
| `goal_agent_generator` (generated agents) | **No** | Uses `AutoMode` + `amplihack-memory-lib`. Different memory stack. |

### 2.4 Gap Analysis

**G1 — Generated agents don't use the SDK adapter chain.**
`GoalAgentPackager._write_main_script()` emits:
```python
from amplihack.launcher.auto_mode import AutoMode
auto_mode = AutoMode(sdk=..., prompt=..., ...)
auto_mode.run()
```
This bypasses `create_agent()` and the `LearningAgent` backend entirely.

**G2 — Memory stack mismatch.**
When `--enable-memory` is passed, the generator writes `amplihack-memory-lib`
`ExperienceStore` init code (successes/failures/patterns), not
`CognitiveAdapter` / Kuzu. The two memory systems are structurally incompatible.

**G3 — No SDK-aware `LearningAgent` construction.**
`LearningAgent.__init__` takes `agent_name`, `model`, `storage_path`,
`use_hierarchical`, `hive_store`, `prompt_variant`. None of these are passed
from the generator's bundle metadata today.

**G4 — `_MiniFrameworkAdapter` in `factory.py` uses `WikipediaLearningAgent`.**
The `mini` SDK path imports a `WikipediaLearningAgent`, not the generic
`LearningAgent`. Benchmark agents generated for `mini` would silently use a
narrower agent.

**G5 — No structural hook for OODA loop in generated agents.**
Generated agents run as single-shot prompts via `AutoMode`. The OODA loop
(`observe` → `orient` → `decide` → `act`) is never used in generated agents.

---

## 3. Proposed Design

### 3.1 Guiding Principles

1. **Structural, not post-hoc** — `LearningAgent` must be instantiated inside
   `__init__` of every generated agent entry point, not injected optionally later.
2. **SDK parity** — All four SDK targets (claude, copilot, microsoft, mini)
   emit agents that use the same `LearningAgent`-backed memory stack.
3. **Non-breaking** — No changes to the currently running 5000-turn eval
   infrastructure (`goal_seeking_agent.py`, `sdk_adapters/`, `hive_mind/`).
4. **Single source of truth** — `sdk_adapters/factory.py:create_agent()` is the
   canonical factory; generated agent entry points call it, not `AutoMode`.

### 3.2 Target Architecture

```
Generated agent entry point (main.py)
    │
    ▼
sdk_adapters.create_agent(name, sdk=sdk, ...)   ← canonical factory
    │
    ▼
{Claude|Copilot|Microsoft|Mini}GoalSeekingAgent (SDK adapter)
    │
    ├── _init_memory()  → MemoryRetriever (storage_path from bundle)
    │
    └── _get_learning_agent()  → LearningAgent (always, not lazy)
            │
            ├── CognitiveAdapter / Kuzu   (use_hierarchical=True)
            ├── AgenticLoop               (PERCEIVE→REASON→ACT→LEARN)
            ├── ActionExecutor            (search_memory, read_content, calculate)
            └── MemoryRetriever           (shared with SDK adapter)
```

The generated `main.py` drives the agent through the **OODA loop**
(`process()` / `run_ooda_loop()`) that `goal_seeking_agent.py` already
implements, rather than `AutoMode`.

### 3.3 Generator Changes

#### 3.3.1 `GoalAgentBundle` model — new field

```python
# models.py
@dataclass
class GoalAgentBundle:
    ...
    use_learning_agent: bool = True   # NEW: wire LearningAgent in generated main.py
    learning_agent_config: dict = field(default_factory=dict)  # NEW: model, hierarchical, etc.
```

#### 3.3.2 `AgentAssembler.assemble()` — new parameters

```python
def assemble(
    self,
    goal_definition: GoalDefinition,
    execution_plan: ExecutionPlan,
    skills: list[SkillDefinition],
    ...
    use_learning_agent: bool = True,      # NEW
    use_hierarchical: bool = True,        # NEW: default on (Graph-RAG quality)
    prompt_variant: int | None = None,    # NEW: A/B variant pass-through
) -> GoalAgentBundle:
```

When `use_learning_agent=True`:
- `bundle.use_learning_agent = True`
- `bundle.learning_agent_config = {"use_hierarchical": use_hierarchical, "prompt_variant": prompt_variant}`
- `metadata["memory_enabled"]` is set `True` automatically (LearningAgent implies memory)

#### 3.3.3 CLI — new flags

```
amplihack new --file my_goal.md                     # LearningAgent on by default
amplihack new --file my_goal.md --no-learning-agent # Opt-out to legacy AutoMode
amplihack new --file my_goal.md --no-hierarchical   # Flat Kuzu (lighter, faster)
```

Backward compatibility: `--enable-memory` continues to work; when
`--no-learning-agent` is given, it falls back to the existing `amplihack-memory-lib`
path.

#### 3.3.4 `GoalAgentPackager._write_main_script()` — new template

When `bundle.use_learning_agent is True`, emit this entry point instead of the
current `AutoMode` template:

```python
#!/usr/bin/env python3
"""
{bundle.name} — Goal-Seeking Agent (LearningAgent-backed)
Generated by Amplihack Goal Agent Generator
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).parent

def main() -> int:
    from amplihack.agents.goal_seeking.sdk_adapters import create_agent
    from amplihack.agents.goal_seeking.input_source import ListInputSource

    storage_path = AGENT_DIR / "memory"
    storage_path.mkdir(parents=True, exist_ok=True)

    agent = create_agent(
        name="{bundle.name}",
        sdk="{bundle.auto_mode_config['sdk']}",
        instructions=AGENT_DIR.joinpath("prompt.md").read_text(),
        storage_path=storage_path,
        enable_memory=True,
        use_hierarchical={bundle.learning_agent_config.get('use_hierarchical', True)},
    )

    # Feed content from execution plan phases, then the goal as a question
    inputs = _load_inputs(AGENT_DIR)
    src = ListInputSource(inputs)

    try:
        agent.run_ooda_loop(src)
    finally:
        agent.close()

    return 0


def _load_inputs(agent_dir: Path) -> list[str]:
    """Load inputs from prompt.md — content paragraphs first, goal question last."""
    prompt = agent_dir.joinpath("prompt.md").read_text()
    lines = [l.strip() for l in prompt.splitlines() if l.strip()]
    goal_line = next((l for l in lines if l.startswith("# Goal:")), None)
    question = goal_line.replace("# Goal:", "").strip() + "?" if goal_line else "What is the goal?"
    return [prompt, question]


if __name__ == "__main__":
    sys.exit(main())
```

### 3.4 SDK-Specific Interface Contracts

All four SDK variants expose the same public interface (inherited from
`sdk_adapters/base.py GoalSeekingAgent`):

| Method | Signature | Notes |
|---|---|---|
| `learn_from_content(content)` | `str → dict` | Delegates to `LearningAgent.learn_from_content()` |
| `answer_question(question)` | `str → str` | Delegates to `LearningAgent.answer_question()` |
| `process(input_data)` | `str → str` | Via `GoalSeekingAgent` OODA (if using OODA wrapper) |
| `run_ooda_loop(input_source)` | `InputSource → None` | Via `GoalSeekingAgent` OODA wrapper |
| `close()` | `→ None` | Closes LearningAgent + memory |

`create_agent()` is the only entry point the generated `main.py` needs.

#### SDK-Specific Notes

**Claude SDK (`claude_sdk.py`)**
- `_run_sdk_agent()` uses `ClaudeSDKClient.connect()` → `query()` → `receive_response()`
- `LearningAgent` is accessed via `_get_learning_agent()` cache in `base.py`
- Generated agents use `CLAUDE_AGENT_MODEL` env or `EVAL_MODEL`
- **Interface contract**: `create_agent(name, sdk="claude", instructions, storage_path, enable_memory=True)`

**Copilot SDK (`copilot_sdk.py`)**
- Tools registered as `CopilotTool` with async handlers wrapping `AgentTool.function`
- Session recreated per-call (`_ensure_client()`) to avoid event-loop issues
- `LearningAgent` wired via `_tool_learn` → `_get_learning_agent().learn_from_content()`
- **Interface contract**: `create_agent(name, sdk="copilot", instructions, storage_path, enable_memory=True, timeout=300)`

**Microsoft Agent Framework (`microsoft_sdk.py`)**
- Tools registered as `FunctionTool` objects; agent needs `OPENAI_API_KEY`
- `LearningAgent` wired via `_tool_learn` and `_tool_search`
- If `OPENAI_API_KEY` absent, SDK agent is `None`; eval uses `LearningAgent` directly via `_SDKAgentWrapper`
- **Interface contract**: `create_agent(name, sdk="microsoft", instructions, storage_path, enable_memory=True)`

**Mini (`factory.py` `_MiniFrameworkAdapter`)**
⚠️ **Gap G4** — currently uses `WikipediaLearningAgent`, not the generic `LearningAgent`.
**Fix required**: Replace `WikipediaLearningAgent` import in `_MiniFrameworkAdapter._create_sdk_agent()` with `LearningAgent`:

```python
# factory.py _MiniFrameworkAdapter._create_sdk_agent() — proposed change
from amplihack.agents.goal_seeking.learning_agent import LearningAgent
self._learning_agent = LearningAgent(
    agent_name=self.name,
    model=self._mini_model,
    storage_path=self.storage_path,
)
```

This is a one-line change in `factory.py` that aligns `mini` with the other SDKs.
No functional regression — `LearningAgent` is a strict superset of `WikipediaLearningAgent`.

### 3.5 LearningAgent Construction Parameters per SDK

All four SDK adapters should pass these parameters to `LearningAgent`:

| Parameter | Value | Rationale |
|---|---|---|
| `agent_name` | `self.name` (not `self.name + "_learning"`) | Avoids agent_id mismatch with pre-built DBs (bug #2661) |
| `model` | `os.environ.get("EVAL_MODEL", "claude-opus-4-6")` | Anthropic key reliable |
| `storage_path` | `self.storage_path` | Same path as SDK adapter's `MemoryRetriever` |
| `use_hierarchical` | `True` | Graph-RAG improves recall quality |
| `hive_store` | `None` (unless distributed mode) | Default single-agent |
| `prompt_variant` | `None` (or from bundle config) | A/B testing |

### 3.6 Benchmark Consistency Guarantee

After this change, `amplihack new --file goal.md --sdk {claude|copilot|microsoft|mini}`
will always emit an agent whose `main.py` calls `create_agent()` → SDK adapter →
lazy `LearningAgent`, using the exact same memory stack as the production
5000-turn Azure eval agent.

The only remaining difference between a generated agent and the production eval agent
is the OODA outer loop vs the SDK `run()` method — which is an intentional design
choice (production eval uses the event-driven OODA loop; generated agents use the
SDK's native agentic loop for interactive tasks).

---

## 4. Multi-Agent Review

### 4.1 Critic A — Adversarial Architecture Review

> *"What are the weak assumptions and failure modes?"*

**Critique 1: Lazy LearningAgent cache breaks concurrent/multi-process usage.**
The `_get_learning_agent()` pattern in `base.py` creates a single `LearningAgent`
on first call and caches it. In a multi-threaded benchmark harness that calls
`learn_from_content` and `answer_question` concurrently on the same agent,
`LearningAgent` internals (especially Kuzu transactions) may not be thread-safe.

**Resolution**: The design does not change the lazy cache pattern (that's in
existing eval code, not in the generator). Generated agents use a single
`run_ooda_loop()` call that is inherently sequential. For concurrent evaluation,
each worker should instantiate a separate agent. This is a documentation note,
not a blocker.

**Critique 2: The `mini` SDK fix is described as "no functional regression" but
`WikipediaLearningAgent` may have Wikipedia-specific behaviour that callers depend on.**
If any test imports `_MiniFrameworkAdapter` and checks for Wikipedia-specific
answer patterns, replacing the backend with generic `LearningAgent` would break those tests.

**Resolution accepted**: Before merging the `_MiniFrameworkAdapter` fix, run
`pytest tests/agents/goal_seeking/` and `tests/generator/` to confirm no
regressions. The fix should be guarded by a TODO comment and test marker until
validated.

**Critique 3: Generated `main.py` calls `run_ooda_loop()` which is on
`goal_seeking_agent.GoalSeekingAgent` (OODA class), not on the SDK adapter ABC.**
The SDK adapter ABC in `base.py` does NOT have `run_ooda_loop()`. Only the
OODA wrapper in `goal_seeking_agent.py` does. The proposed `main.py` template
calls `create_agent()` which returns an SDK adapter — so `run_ooda_loop()` would
raise `AttributeError`.

**Resolution (Critical)**: The generated `main.py` must either:
- (Option A) Wrap the SDK adapter in a `GoalSeekingAgent` (OODA) and use `process()` — this is cleaner but adds an extra layer.
- (Option B) Drive the SDK adapter directly: call `agent.learn_from_content(content)` then `agent.answer_question(question)` — matches how the eval harness actually works.
- (Option C) Teach the SDK adapter ABC to expose a `run_loop(inputs)` method that wraps `learn_from_content` / `answer_question` iteration.

**Recommended**: Option B for immediate correctness, Option C as follow-up for a cleaner API.

Updated `main.py` template (corrected):

```python
def main() -> int:
    from amplihack.agents.goal_seeking.sdk_adapters import create_agent

    agent = create_agent(
        name="{bundle.name}",
        sdk="{sdk}",
        instructions=AGENT_DIR.joinpath("prompt.md").read_text(),
        storage_path=AGENT_DIR / "memory",
        enable_memory=True,
    )

    prompt_text = AGENT_DIR.joinpath("prompt.md").read_text()
    goal_question = _extract_goal_question(prompt_text)

    try:
        agent.learn_from_content(prompt_text)
        answer = agent.answer_question(goal_question)
        print(f"[{agent.name}] ANSWER: {answer}")
    finally:
        agent.close()

    return 0
```

**Critique 4: `use_hierarchical=True` by default may fail if Kuzu is not
installed, silently degrading to flat retrieval.**
`LearningAgent.__init__` sets `use_hierarchical=False` if `CognitiveAdapter`
import fails (`HAS_COGNITIVE_MEMORY` flag). This silent fallback means benchmark
agents run in a degraded mode without the operator knowing.

**Resolution**: The generator should log a warning when `use_hierarchical=True`
but `HAS_COGNITIVE_MEMORY=False`. This is a monitoring/observability concern,
not a blocker for the design. Add to requirements.txt: `kuzu>=0.4`.

---

### 4.2 Critic B — Benchmark Validity Review

> *"Does this design actually guarantee consistent benchmark agents?"*

**Critique 5: "Consistent generation" is claimed but not enforced by tests.**
The design adds a `use_learning_agent` flag but nothing prevents a future PR
from adding another memory backend path and forgetting to wire `LearningAgent`.

**Resolution accepted**: Add a pytest fixture
`test_generated_agent_uses_learning_agent(sdk)` (parametrized over four SDKs)
that calls `create_agent()` from within a packaged agent and asserts
`_get_learning_agent() is not None`. This test goes in
`tests/generator/test_sdk_injection.py`.

**Critique 6: The `_SDKAgentWrapper` in eval harness uses a different code path.**
The eval harness (5000-turn Azure eval) wraps the SDK adapter via
`_SDKAgentWrapper` which directly calls `_learning_agent.learn_from_content()`
and `_learning_agent.answer_question()`. This is NOT the same as the OODA
loop or the `sdk_adapters` public API.

**Resolution**: This design does not touch the eval harness. The claim is only
that generated agents use the same **LearningAgent** as the eval harness — not
the same execution shell. This is correct by design: eval uses event-driven
OODA; generated agents use SDK-native agentic loops. The shared component is
`LearningAgent` and its memory stack.

**Critique 7: `bundle.auto_mode_config['sdk']` string interpolation in the
template is fragile — if `sdk` is an `SDKType` enum, the generated code will
have `SDKType.CLAUDE` as a string literal.**
The template writes `sdk="{bundle.auto_mode_config['sdk']}"` which could be
`"SDKType.claude"` instead of `"claude"`.

**Resolution accepted**: In `packager.py`, resolve the SDK value to its `.value`
string before template interpolation:
```python
sdk_str = str(bundle.auto_mode_config.get("sdk", "copilot")).lower()
sdk_str = sdk_str.replace("sdktype.", "")  # Normalize enum string
```

---

## 5. Final Design — Accepted Changes

### 5.1 Changes to Existing Files

| File | Change | Risk |
|---|---|---|
| `goal_agent_generator/models.py` | Add `use_learning_agent: bool = True` and `learning_agent_config: dict` to `GoalAgentBundle` | Low — additive |
| `goal_agent_generator/agent_assembler.py` | Add `use_learning_agent`, `use_hierarchical`, `prompt_variant` params; populate new bundle fields | Low — additive |
| `goal_agent_generator/packager.py` | New `main.py` template when `use_learning_agent=True`; SDK string normalization fix | Medium — changes generated output |
| `goal_agent_generator/cli.py` | Add `--no-learning-agent` and `--no-hierarchical` flags | Low — additive |
| `sdk_adapters/factory.py` | Fix `_MiniFrameworkAdapter` to use `LearningAgent` instead of `WikipediaLearningAgent` | Low — conditional on test validation |

### 5.2 New Files

| File | Purpose |
|---|---|
| `goal_agent_generator/templates/learning_agent_template.py` | Contains the new `main.py` template string and `_extract_goal_question()` helper |
| `tests/generator/test_learning_agent_integration.py` | Parametrized tests asserting all four SDK variants wire `LearningAgent` |

### 5.3 Trade-offs Accepted

| Trade-off | Decision |
|---|---|
| Generated agents use `learn_from_content` + `answer_question` directly (Option B) rather than OODA wrapper | Accept — matches eval harness exactly; OODA wrapper adds complexity for no benchmark benefit |
| `use_hierarchical=True` default may silently degrade | Accept with logging — Kuzu should be in requirements; log warning if unavailable |
| `_MiniFrameworkAdapter` fix blocked on test validation | Defer to follow-up PR; document as known gap |
| Concurrent safety of `LearningAgent` | Accept — out of scope; generated agents are single-threaded; document in README |

### 5.4 Out of Scope (Explicitly)

- Changes to `goal_seeking_agent.py` (OODA wrapper) — used by running eval, do not touch
- Changes to `hive_mind/` — distributed eval infrastructure, do not touch
- Changes to `memory_retrieval.py`, `flat_retriever_adapter.py` — currently under active fix branch, do not touch
- Changes to `continuous_eval.py` — eval runner, do not touch

---

## 6. Implementation Checklist

The following changes should be implemented in a follow-up PR after this design
is accepted. This document is design-only output.

- [ ] `models.py` — add `use_learning_agent`, `learning_agent_config` fields
- [ ] `agent_assembler.py` — pass-through new params to bundle
- [ ] `cli.py` — add `--no-learning-agent`, `--no-hierarchical` flags
- [ ] `templates/learning_agent_template.py` — new file with corrected `main.py` template
- [ ] `packager.py` — route to new template; SDK string normalization
- [ ] `tests/generator/test_learning_agent_integration.py` — 4-SDK parametrized test
- [ ] Validate `_MiniFrameworkAdapter` change against existing test suite before merging
- [ ] Update `goal_agent_generator/README.md` with new flags and architecture diagram

---

## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  amplihack new --file goal.md --sdk claude                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  goal_agent_generator pipeline        │
        │  PromptAnalyzer → GoalDefinition      │
        │  ObjectivePlanner → ExecutionPlan     │
        │  SkillSynthesizer → [SkillDefinition] │
        │  AgentAssembler → GoalAgentBundle     │
        │    use_learning_agent=True ← NEW      │
        │  GoalAgentPackager → agent_dir/       │
        └──────────────────┬───────────────────┘
                           │ emits
                           ▼
        ┌──────────────────────────────────────┐
        │  agent_dir/main.py  (NEW template)    │
        │                                       │
        │  create_agent(name, sdk="claude", …)  │
        │        │                              │
        │        ▼                              │
        │  ClaudeGoalSeekingAgent               │
        │  ├── _init_memory() → MemoryRetriever │
        │  └── _get_learning_agent() →          │
        │       LearningAgent                   │
        │       ├── CognitiveAdapter (Kuzu)     │
        │       ├── AgenticLoop                 │
        │       └── MemoryRetriever (shared)    │
        │                                       │
        │  agent.learn_from_content(prompt)     │
        │  agent.answer_question(goal?)         │
        └──────────────────────────────────────┘

SAME LearningAgent stack used by production 5000-turn Azure eval
```

---

## 8. References

- `src/amplihack/agents/goal_seeking/goal_seeking_agent.py` — OODA loop wrapper
- `src/amplihack/agents/goal_seeking/learning_agent.py` — core learning engine
- `src/amplihack/agents/goal_seeking/sdk_adapters/base.py` — SDK adapter ABC + LearningAgent cache
- `src/amplihack/agents/goal_seeking/sdk_adapters/factory.py` — `create_agent()` factory
- `src/amplihack/goal_agent_generator/` — generator pipeline
- `src/amplihack/goal_agent_generator/MEMORY_INTEGRATION.md` — existing memory integration docs
- `tests/generator/test_sdk_injection.py` — existing SDK injection tests
