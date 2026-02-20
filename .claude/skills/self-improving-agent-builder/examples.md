# Self-Improving Agent Builder - Examples

## Example 1: Single SDK Improvement Loop

**User request:** "Run the self-improving loop on the mini-framework agent"

**Execution:**

```
WORKFLOW: Self-Improving Agent Builder
SDK: mini
Max iterations: 5
Levels: L1-L6
Output: ./eval_results/self_improve/mini/

=== Iteration 1 ===

[BUILD] No patches to apply (baseline run)
  Agent: src/amplihack/agents/goal_seeking/wikipedia_learning_agent.py
  Status: OK (330 lines, 7 tools registered)

[EVAL] Running L1-L6 progressive test suite (3 runs, parallel)
  Run 1: L1=87%, L2=100%, L3=85%, L4=79%, L5=95%, L6=100%, Overall=91%
  Run 2: L1=83%, L2=95%, L3=88%, L4=75%, L5=90%, L6=100%, Overall=88%
  Run 3: L1=80%, L2=100%, L3=92%, L4=83%, L5=95%, L6=95%, Overall=91%
  Median: L1=83%, L2=100%, L3=88%, L4=79%, L5=95%, L6=100%, Overall=91%

[AUDIT] Quality checks on agent code
  - No silent exception blocks: PASS
  - No stubs/placeholders: PASS
  - close() method present: PASS
  - 7 learning tools registered: PASS
  - Audit findings: 0

[IMPROVE] Analyzing failures (threshold: 60%)
  - L4 Q2 scored 50%: procedural_ordering_lost
    Component: learning_agent.py::_extract_facts_with_llm
    Fix: Add step-ordering instruction to fact extraction prompt
  - L3 Q1 scored 55%: temporal_ordering_wrong
    Component: learning_agent.py::_synthesize_with_llm
    Fix: Add temporal delta calculation hint

[RE-EVAL] Running L1-L6 after fixes (3 runs, parallel)
  Median: L1=83%, L2=100%, L3=92%, L4=83%, L5=95%, L6=100%, Overall=92%
  Delta: +1.1% (below +2% threshold)
  Decision: COMMIT_WARN (marginal improvement)
  git commit -m "improve(agent): marginal +1.1% (mini, iteration 1) [review]"

=== Iteration 2 ===

[BUILD] Applying 2 patches from iteration 1 IMPROVE phase
  Patch 1: fact_extraction prompt - add step ordering
  Patch 2: synthesis prompt - add temporal computation hint

[EVAL] L1=87%, L2=100%, L3=92%, L4=83%, L5=95%, L6=100%, Overall=93%

[AUDIT] 0 findings

[IMPROVE] 1 failure cluster
  - L1 Q3 scored 55%: retrieval_insufficient
    Fix: Broaden retrieval query expansion

[RE-EVAL] Overall=94%, Delta: +1.0%
  Decision: COMMIT_WARN

=== Summary ===
  Iterations completed: 2/5
  Baseline overall: 91%
  Final overall: 94%
  Net improvement: +3%
  Commits: 2 (both marginal)
  Reverts: 0
```

## Example 2: 4-Way Benchmark Comparison

**User request:** "Run a 4-way benchmark comparing all SDK implementations"

**Execution:**

```
WORKFLOW: Self-Improving Agent Builder (Benchmark Mode)

Running L1-L6 eval on all 4 SDK implementations...

=== Mini Framework (baseline) ===
  Agent: wikipedia_learning_agent.py (330 LOC)
  L1=83%, L2=100%, L3=88%, L4=79%, L5=95%, L6=100%
  Overall: 91%
  Supporting code: 1967 LOC (agentic_loop, hierarchical_memory, etc.)
  Tests: 274 LOC (test_wikipedia_learning_agent.py)

=== Claude SDK ===
  Agent: claude_sdk.py (168 LOC)
  L1=--%, L2=--%, L3=--%, L4=--%, L5=--%, L6=--%
  Overall: N/A (requires claude-agents package)
  Tests: 426 LOC (test_claude_sdk_adapter.py)
  Note: SDK not installed; would need pip install claude-agents

=== Copilot SDK ===
  Agent: copilot_sdk.py (394 LOC)
  L1=--%, L2=--%, L3=--%, L4=--%, L5=--%, L6=--%
  Overall: N/A (requires github-copilot-sdk package)
  Tests: 566 LOC (test_copilot_sdk_adapter.py)
  Note: SDK not installed; would need pip install github-copilot-sdk

=== Microsoft SDK ===
  Agent: microsoft_sdk.py (442 LOC)
  L1=--%, L2=--%, L3=--%, L4=--%, L5=--%, L6=--%
  Overall: N/A (mock mode - agent-framework not importable)
  Tests: 638 LOC (test_microsoft_sdk_adapter.py)
  Note: Falls back to mock execution

=== Comparison Table ===

| Metric         | Mini    | Claude  | Copilot | Microsoft |
|----------------|---------|---------|---------|-----------|
| L1 (recall)    | 83%     | N/A     | N/A     | N/A       |
| L2 (synthesis) | 100%    | N/A     | N/A     | N/A       |
| L3 (temporal)  | 88%     | N/A     | N/A     | N/A       |
| L4 (procedural)| 79%     | N/A     | N/A     | N/A       |
| L5 (contradict)| 95%     | N/A     | N/A     | N/A       |
| L6 (incremental)| 100%  | N/A     | N/A     | N/A       |
| Overall        | 91%     | N/A     | N/A     | N/A       |
| Agent LOC      | 330     | 168     | 394     | 442       |
| Base class LOC | 425     | 425     | 425     | 425       |
| Support LOC    | 1,967   | 0       | 0       | 0         |
| Test LOC       | 274     | 426     | 566     | 638       |
```

## Example 3: Targeted Level Improvement

**User request:** "Improve the mini agent's L4 procedural learning score"

**Execution:**

```
WORKFLOW: Self-Improving Agent Builder
SDK: mini
Levels: L4 (targeted)
Max iterations: 3

=== Iteration 1 ===

[EVAL] L4 baseline: 79% (3-run median)
  Q1: 95% (direct recall of steps - OK)
  Q2: 50% (step ordering verification - FAIL)
  Q3: 92% (apply procedure to scenario - OK)

[IMPROVE] 1 failure:
  Q2 scored 50%: procedural_ordering_lost
  Component: learning_agent.py::_extract_facts_with_llm
  Evidence: Steps mentioned but sequence lost during extraction
  Fix: Add "IMPORTANT: Preserve step numbers and ordering" to extraction prompt

[RE-EVAL] L4: 83%, Delta: +4%
  Decision: COMMIT (+4% > +2% threshold)

=== Iteration 2 ===

[EVAL] L4: 88% (Q2 now 75%)

[IMPROVE] Q2 still below 90%
  Fix: Add explicit "Output steps as numbered list" instruction

[RE-EVAL] L4: 92%, Delta: +4%
  Decision: COMMIT

=== Summary ===
  L4 improved: 79% -> 92% (+13%)
  No regressions on other levels
```

## Example 4: Improvement with Regression Revert

**User request:** "Try to improve L3 temporal reasoning"

```
=== Iteration 1 ===

[EVAL] L3 baseline: 88%

[IMPROVE] Fix: Add arithmetic verification step to synthesis prompt

[RE-EVAL]
  L3: 92% (+4%) - IMPROVED
  L1: 70% (-13%) - REGRESSED!
  Decision: REVERT (L1 regression 13% > 5% tolerance)
  git checkout -- src/amplihack/agents/

Reason: The arithmetic verification prompt made simple recall
questions worse by adding unnecessary computation steps.

[IMPROVE] (adjusted) Fix: Gate arithmetic instructions behind
  is_complex_intent check instead of applying universally

[RE-EVAL]
  L3: 90% (+2%)
  L1: 83% (0%) - No regression
  Decision: COMMIT
```

## Example 5: Configuring the Loop

**Override defaults:**

```
User: "Run improvement loop with:
  - SDK: copilot
  - Max 3 iterations
  - Only L1-L3
  - 5 runs per eval
  - +3% threshold
  - 3% regression tolerance"

Skill: Using configuration:
  sdk_type: copilot
  max_iterations: 3
  levels: L1,L2,L3
  runs_per_eval: 5
  improvement_threshold: 3.0
  regression_tolerance: 3.0
  output_dir: ./eval_results/self_improve/copilot/
```
