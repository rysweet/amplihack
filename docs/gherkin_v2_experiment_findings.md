# Gherkin v2 Experiment Findings: Recipe Step Executor

Issue: #3969 | PR: #3975 | Date: 2026-03-31

## Summary

Tested 4 prompt variants (English baseline, Gherkin-only, Gherkin+English,
Gherkin+Acceptance) for generating a complex `RecipeStepExecutor` with 6
interacting behavioral features. Evaluated via 20 heuristic checks across 6
feature dimensions.

## Key Findings

### 1. Gherkin+English hybrid outperforms both baselines

| Variant                 | Avg Score |
| ----------------------- | --------- |
| english (baseline)      | 0.903     |
| gherkin_only            | 0.792     |
| gherkin_plus_english    | **0.944** |
| gherkin_plus_acceptance | **0.944** |

Hybrid variants consistently score 4.5% higher than English baseline. The gain
comes from dependency handling and retry logic where formal scenarios disambiguate
expected behavior.

### 2. Gherkin-only is unreliable

Scored 1.000 in one run but 0.792 in another. Without English guidance, the model
misses implementation details like timeout-no-retry semantics and exponential
backoff parameters. Gherkin specifies WHAT, not HOW.

### 3. Timeout semantics is the hardest feature

Highest variance across all variants (0.33 to 1.00). The negative constraint
"timed-out steps are NOT retried" is frequently missed. Formal scenarios that
explicitly test this interaction improve scores.

### 4. Smaller gain than TLA+ (~5% vs ~51%)

Expected: Claude Opus 4.6 scores 0.903 on behavioral tasks (high baseline) vs
0.57 on distributed systems tasks. Formal specs add the most value where the
baseline is weakest.

### 5. GPT-5.4 copilot SDK timed out on all conditions

Infrastructure limitation, not a prompt issue. Prevents cross-model comparison.

## Implications for Prompt Strategy

- **Behavioral tasks with complex interactions**: Use Gherkin+English hybrid
- **Concurrent/distributed systems**: Use TLA+ formal specifications
- **Simple features with obvious behavior**: Plain English suffices
- **Never use Gherkin-only**: Always pair with implementation guidance

## Experiment Assets

- Experiment directory: `experiments/hive_mind/gherkin_v2_recipe_executor/`
- Scoring module: `src/amplihack/eval/gherkin_prompt_experiment.py`
- Tests: `tests/eval/test_gherkin_prompt_experiment.py` (33 passing)
- Reference implementation: `experiments/hive_mind/gherkin_v2_recipe_executor/reference/`
