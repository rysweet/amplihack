# Gherkin v2 Experiment Findings

Issue: #3969 | Date: 2026-03-31

## Summary

The Gherkin v2 experiment tested whether Cucumber/Gherkin behavioral
specifications improve code generation quality on a harder target (recipe step
executor with 6 interacting features). The experiment ran 8 conditions (4 prompt
variants × 2 models) in a smoke matrix with live generation.

## Key Findings

1. **Gherkin+English hybrid (0.944) outperforms plain English (0.903)** —
   consistent across both runs. The 4.5% improvement comes from dependency
   handling and timeout semantics.

2. **Gherkin-only is unreliable** — scored 1.000 in one run but 0.792 in
   another. Without implementation guidance, the model sometimes misses
   non-obvious constraints (timeout-no-retry).

3. **Timeout semantics is the hardest feature** — highest variance across all
   variants (0.33 to 1.00). Negative behavioral constraints ("do NOT retry
   timed-out steps") benefit most from formal scenarios.

4. **GPT-5.4 copilot SDK timed out** on all conditions across both runs.
   Cross-model comparison not possible. Infrastructure investigation needed.

5. **Gherkin improvement (~5%) is smaller than TLA+ improvement (~51%)** because
   the English baseline is already high (0.903 vs 0.57 for TLA+). Formal specs
   add the most value where the baseline is weakest.

## Implications for Prompt Strategy

- **Use Gherkin+English hybrid** for behavioral/feature tasks with complex
  interactions
- **Use TLA+** for concurrent/distributed systems with state invariants
- **Plain English suffices** for simple features with obvious behavior
- **Never use Gherkin-only** — always pair with implementation guidance

## Experiment Location

- Experiment: `experiments/hive_mind/gherkin_v2_recipe_executor/`
- Scoring module: `src/amplihack/eval/gherkin_prompt_experiment.py`
- Tests: `tests/eval/test_gherkin_prompt_experiment.py` (33 tests, all passing)
- Results: `experiments/hive_mind/gherkin_v2_recipe_executor/results/smoke_live_20260331_211256/`
