---
name: self-improving-agent-builder
version: 1.0.0
description: |
  Encodes a continuous improvement loop for goal-seeking agents: build, eval (L1-L12),
  audit, improve (error_analyzer), re-eval. Auto-commits improvements (+2% net, no
  regression >5%) and reverts failures. Works with all 4 SDK implementations.
  Auto-activates on "improve agent", "self-improving loop", "agent eval loop",
  "benchmark agents", "run improvement cycle".
source_urls:
  - https://github.com/rysweet/amplihack
---

# Self-Improving Agent Builder

## Purpose

Run a closed-loop improvement cycle on any goal-seeking agent implementation:

```
BUILD -> EVAL -> AUDIT -> IMPROVE -> RE-EVAL -> (repeat)
```

Each iteration measures L1-L12 progressive test scores, identifies failures
with `error_analyzer.py`, proposes targeted fixes, and gates promotion through
regression checks.

## When I Activate

- "improve agent" or "self-improving loop"
- "agent eval loop" or "run improvement cycle"
- "benchmark agents" or "compare SDK implementations"
- "iterate on agent scores" or "fix agent regressions"

## Quick Start

```
User: "Run the self-improving loop on the mini-framework agent for 3 iterations"

Skill: Executes 3 iterations of BUILD->EVAL->AUDIT->IMPROVE->RE-EVAL
       Reports per-iteration scores, net improvement, and commits/reverts.
```

## The Loop (5 Phases per Iteration)

### Phase 1: BUILD

Generate or modify the agent implementation. For existing agents, this phase
is a no-op on the first iteration (the current code IS the build). On
subsequent iterations, BUILD applies the patches proposed by IMPROVE.

**Inputs:**

- SDK type: `mini`, `claude`, `copilot`, or `microsoft`
- Agent path (auto-detected from SDK type if not specified)
- Patches from previous IMPROVE phase (iterations 2+)

**Agent paths by SDK type:**

```
mini:      src/amplihack/agents/goal_seeking/wikipedia_learning_agent.py
claude:    src/amplihack/agents/goal_seeking/sdk_adapters/claude_sdk.py
copilot:   src/amplihack/agents/goal_seeking/sdk_adapters/copilot_sdk.py
microsoft: src/amplihack/agents/goal_seeking/sdk_adapters/microsoft_sdk.py
```

### Phase 2: EVAL

Run the L1-L12 progressive test suite with 3-run parallel execution.
Scores are medians to reduce LLM stochasticity.

**Execution:**

```bash
python -m amplihack.eval.progressive_test_suite \
  --agent-name <agent_name> \
  --output-dir <output_dir>/iteration_N \
  --levels L1,L2,L3,L4,L5,L6,L7,L8,L9,L10,L11,L12
```

**Output:** `scores.json` with per-level medians and overall score.

### Phase 3: AUDIT

Quality audit of the agent code plus exception handling check.

**Checks performed:**

- No silent `except Exception: pass` blocks
- No stubs or placeholder implementations
- No TODO/FIXME comments in production code
- Proper logging in all error handlers
- Memory cleanup in `close()` methods
- Tool registration completeness (all 7 learning tools)

**Execution:** Use reviewer + security agents in parallel on the agent file.

### Phase 4: IMPROVE

Analyze failures from EVAL using `error_analyzer.py` and propose fixes.

**Execution:**

```python
from amplihack.eval.self_improve import analyze_eval_results

analyses = analyze_eval_results(level_results, score_threshold=0.6)
# Each ErrorAnalysis maps to:
#   failure_mode -> affected_component -> prompt_template
#   e.g., "retrieval_insufficient" -> "agentic_loop.py::_plan_retrieval"
```

**Fix strategy (priority order):**

1. Prompt template improvements (safest, highest impact)
2. Retrieval strategy adjustments
3. Code logic fixes (most risky, needs careful review)

### Phase 5: RE-EVAL

Re-run the same eval suite after applying fixes.

**Promotion gate:**

- Net improvement >= +2% overall score: COMMIT the changes
- Any single level regression > 5%: REVERT all changes
- Otherwise: COMMIT with warning about marginal improvement

**Git operations:**

```bash
# On success:
git add -A && git commit -m "improve: +X% agent score (iteration N)"

# On regression:
git checkout -- <modified_files>
```

## Configuration

| Parameter               | Default                       | Description                              |
| ----------------------- | ----------------------------- | ---------------------------------------- |
| `sdk_type`              | `mini`                        | Which SDK: mini/claude/copilot/microsoft |
| `max_iterations`        | `5`                           | Maximum improvement iterations           |
| `improvement_threshold` | `2.0`                         | Minimum % improvement to commit          |
| `regression_tolerance`  | `5.0`                         | Maximum % regression on any level        |
| `levels`                | `L1-L6`                       | Which levels to evaluate                 |
| `runs_per_eval`         | `3`                           | Parallel runs per eval (median)          |
| `output_dir`            | `./eval_results/self_improve` | Results directory                        |

## 4-Way Benchmark Mode

Compare all SDK implementations side by side:

```
User: "Run a 4-way benchmark comparing all SDK implementations"

Skill: Runs eval suite on mini, claude, copilot, microsoft
       Generates comparison table with scores, LOC, and coverage.
```

**Output format:**

```
| Metric        | Mini  | Claude | Copilot | Microsoft |
|---------------|-------|--------|---------|-----------|
| L1 (recall)   | 83%   | --     | --      | --        |
| L2 (synth)    | 100%  | --     | --      | --        |
| ...           |       |        |         |           |
| Overall       | 88%   | --     | --      | --        |
| LOC           | 2297  | 168    | 394     | 442       |
| Tests         | 274   | 426    | 566     | 638       |
```

## When to Read Supporting Files

- **reference.md**: Full API details, error taxonomy, subprocess isolation
- **examples.md**: Step-by-step walkthrough of improvement iterations

## Integration Points

- `src/amplihack/eval/progressive_test_suite.py`: L1-L12 eval runner
- `src/amplihack/eval/self_improve/error_analyzer.py`: Failure classification
- `src/amplihack/agents/goal_seeking/sdk_adapters/`: All 4 SDK implementations
- `src/amplihack/eval/metacognition_grader.py`: Advanced eval dimensions
- `src/amplihack/eval/teaching_session.py`: L7 teaching quality eval
