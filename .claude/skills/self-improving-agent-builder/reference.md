# Self-Improving Agent Builder - Reference

## Complete API

### Improvement Loop Execution

The loop is orchestrated by Claude Code following this skill's instructions.
Each phase delegates to subprocess sub-agents for isolation.

#### Phase 1: BUILD - Agent Modification

**First iteration (no patches):**

- Verify agent file exists at the expected path for the SDK type
- Run a baseline sanity check (import test)
- No modifications

**Subsequent iterations (with patches from IMPROVE):**

- Apply patches proposed by error_analyzer
- Patches target specific functions identified by failure taxonomy
- Each patch is applied as a git-tracked edit (reviewable diff)

**SDK type to agent path mapping:**

```python
AGENT_PATHS = {
    "mini": "src/amplihack/agents/goal_seeking/wikipedia_learning_agent.py",
    "claude": "src/amplihack/agents/goal_seeking/sdk_adapters/claude_sdk.py",
    "copilot": "src/amplihack/agents/goal_seeking/sdk_adapters/copilot_sdk.py",
    "microsoft": "src/amplihack/agents/goal_seeking/sdk_adapters/microsoft_sdk.py",
}
```

**Supporting files (may also be modified):**

```python
SUPPORTING_FILES = {
    "mini": [
        "src/amplihack/agents/goal_seeking/agentic_loop.py",
        "src/amplihack/agents/goal_seeking/hierarchical_memory.py",
        "src/amplihack/agents/goal_seeking/cognitive_adapter.py",
        "src/amplihack/agents/goal_seeking/memory_retrieval.py",
    ],
    "claude": ["src/amplihack/agents/goal_seeking/sdk_adapters/base.py"],
    "copilot": ["src/amplihack/agents/goal_seeking/sdk_adapters/base.py"],
    "microsoft": ["src/amplihack/agents/goal_seeking/sdk_adapters/base.py"],
}
```

#### Phase 2: EVAL - Progressive Test Suite

**Subprocess command:**

```bash
python -m amplihack.eval.progressive_test_suite \
  --agent-name "eval-{sdk_type}-iter{N}" \
  --output-dir "{output_dir}/iteration_{N}" \
  --levels L1,L2,L3,L4,L5,L6
```

For advanced levels (L7-L12), additional flags:

```bash
# L7: Teaching eval
--levels L7 --teaching-mode

# L8-L10: Metacognition, causal, counterfactual
--levels L8,L9,L10

# L11-L12: Novel skill acquisition, far transfer
--levels L11,L12
```

**3-run median calculation:**

Run the eval 3 times in parallel and take median scores per level.
This is essential because single LLM runs are unreliable. The progressive
test suite supports `--parallel-runs 3` for this.

**Score output format (scores.json):**

```json
{
  "scores": {
    "L1": {"median": 0.83, "runs": [0.83, 0.87, 0.80]},
    "L2": {"median": 1.0, "runs": [1.0, 1.0, 0.95]},
    "L3": {"median": 0.88, "runs": [0.88, 0.92, 0.85]},
    "overall": {"median": 0.88, "runs": [0.88, 0.90, 0.86]}
  },
  "details": [...]
}
```

#### Phase 3: AUDIT - Quality Checks

**Audit checklist (automated grep-based checks):**

```bash
# Silent exception blocks
grep -n "except.*:$\|except Exception:" {agent_file} | grep -v "logger\."

# Stubs and placeholders
grep -n "pass$\|NotImplementedError\|TODO\|FIXME\|HACK" {agent_file}

# Missing close/cleanup
grep -c "def close" {agent_file}  # Should be >= 1

# Tool registration completeness
grep -c "AgentTool(" {agent_file}  # Should be >= 7
```

**Parallel agent audit (optional, for comprehensive review):**

Deploy reviewer and security agents on the agent file for deeper analysis.

#### Phase 4: IMPROVE - Error Analysis

**Error analyzer usage:**

```python
from amplihack.eval.self_improve import analyze_eval_results

# level_results from Phase 2
analyses = analyze_eval_results(
    level_results=level_results,
    score_threshold=0.6,  # Questions below 60% are failures
)

for analysis in analyses:
    print(f"Failure: {analysis.failure_mode}")
    print(f"Component: {analysis.affected_component}")
    print(f"Prompt template: {analysis.prompt_template}")
    print(f"Score: {analysis.score:.0%}")
    print(f"Focus: {analysis.suggested_focus}")
```

**Failure taxonomy (from error_analyzer.py):**

| Failure Mode               | Component                              | Fix Type      |
| -------------------------- | -------------------------------------- | ------------- |
| retrieval_insufficient     | agentic_loop.py::\_plan_retrieval      | Prompt        |
| temporal_ordering_wrong    | learning_agent.py::\_synthesize        | Prompt        |
| intent_misclassification   | learning_agent.py::\_detect_intent     | Code + Prompt |
| fact_extraction_incomplete | learning_agent.py::\_extract_facts     | Prompt        |
| synthesis_hallucination    | learning_agent.py::\_synthesize        | Prompt        |
| update_not_applied         | hierarchical_memory.py                 | Code          |
| contradiction_undetected   | learning_agent.py::\_detect_intent     | Prompt        |
| procedural_ordering_lost   | learning_agent.py::\_extract_facts     | Prompt        |
| teaching_coverage_gap      | teaching_session.py::\_teacher_respond | Prompt        |
| counterfactual_refusal     | learning_agent.py::\_synthesize        | Prompt        |

**Fix priority:**

1. Prompt template fixes (80% of failures, safest)
2. Retrieval strategy changes (moderate risk)
3. Code logic changes (highest risk, needs careful validation)

#### Phase 5: RE-EVAL - Regression Gate

**Promotion criteria:**

```python
def should_promote(baseline_scores, new_scores, config):
    """Decide whether to commit or revert changes."""
    overall_delta = new_scores["overall"] - baseline_scores["overall"]

    # Check per-level regressions
    for level in new_scores:
        if level == "overall":
            continue
        delta = new_scores[level] - baseline_scores[level]
        if delta < -(config.regression_tolerance / 100):
            return "REVERT", f"{level} regressed by {abs(delta):.1%}"

    if overall_delta >= (config.improvement_threshold / 100):
        return "COMMIT", f"Net improvement: +{overall_delta:.1%}"

    return "COMMIT_WARN", f"Marginal improvement: +{overall_delta:.1%}"
```

**Git operations:**

```bash
# COMMIT: Changes improve scores
git add -A
git commit -m "improve(agent): +{delta}% overall ({sdk_type}, iteration {N})"

# REVERT: Changes cause regression
git checkout -- src/amplihack/agents/

# COMMIT_WARN: Marginal improvement
git add -A
git commit -m "improve(agent): marginal +{delta}% ({sdk_type}, iteration {N}) [review]"
```

### Subprocess Isolation

Each phase runs in a subprocess to prevent state leakage between iterations.
The agent's memory database is isolated per eval run using unique agent names.

```python
agent_name = f"eval-{sdk_type}-iter{iteration}-run{run_number}"
```

This ensures:

- Fresh memory for each eval run (no carryover from learning phase)
- Parallel runs don't interfere with each other
- Deterministic evaluation conditions

### Files That Must Not Be Modified

The improvement loop must NEVER modify:

- `src/amplihack/eval/grader.py` (grading criteria)
- `src/amplihack/eval/test_levels.py` (test data)
- `src/amplihack/eval/metacognition_grader.py` (grading rubrics)
- `src/amplihack/eval/self_improve/error_analyzer.py` (analysis logic)
- Any test fixtures or expected answers

### Iteration Log Format

Each iteration produces a structured log:

```json
{
  "iteration": 1,
  "sdk_type": "mini",
  "timestamp": "2026-02-20T10:30:00Z",
  "phases": {
    "build": { "status": "ok", "patches_applied": 0 },
    "eval": { "status": "ok", "scores": { "L1": 0.83, "overall": 0.88 } },
    "audit": { "status": "ok", "findings": 2 },
    "improve": { "status": "ok", "analyses": 3, "patches_proposed": 2 },
    "re_eval": { "status": "ok", "scores": { "L1": 0.87, "overall": 0.9 } },
    "decision": "COMMIT",
    "delta": "+2.3%"
  }
}
```

Logs are saved to `{output_dir}/iteration_{N}/iteration_log.json`.
