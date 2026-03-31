# Gherkin v2 Recipe Step Executor Experiment Report

**Experiment ID**: `gherkin-v2-recipe-executor`
**Generated at**: `2026-03-31T21:45:01.691187+00:00`
**Matrix mode**: `smoke`
**Replay mode**: `False`
**Evaluation kind**: `gherkin_heuristic_v2`
**Output dir**: `experiments/hive_mind/gherkin_v2_recipe_executor/results/smoke_live_20260331_211256`

## Summary

- Total conditions: 8
- Completed conditions: 4
- Failed conditions: 4

## Metric Mapping

| Shared Metric Name       | Gherkin Feature       |
| ------------------------ | --------------------- |
| baseline_score           | Conditional Execution |
| invariant_compliance     | Dependency Handling   |
| proof_alignment          | Retry Logic           |
| local_protocol_alignment | Timeout Semantics     |
| progress_signal          | Output Capture        |
| specification_coverage   | Sub-recipe Delegation |

## Condition Table

| Condition                                    | Model           | Prompt                  | Status    | Conditional | Dependencies | Retry  | Timeout | Output | SubRecipe |
| -------------------------------------------- | --------------- | ----------------------- | --------- | ----------- | ------------ | ------ | ------- | ------ | --------- |
| claude_opus_4_6**english**r1                 | claude-opus-4.6 | english                 | completed | 1.0         | 0.75         | 1.0    | 0.6667  | 1.0    | 1.0       |
| claude_opus_4_6**gherkin_only**r1            | claude-opus-4.6 | gherkin_only            | completed | 1.0         | 0.75         | 0.6667 | 0.3333  | 1.0    | 1.0       |
| claude_opus_4_6**gherkin_plus_english**r1    | claude-opus-4.6 | gherkin_plus_english    | completed | 1.0         | 1.0          | 1.0    | 0.6667  | 1.0    | 1.0       |
| claude_opus_4_6**gherkin_plus_acceptance**r1 | claude-opus-4.6 | gherkin_plus_acceptance | completed | 1.0         | 1.0          | 1.0    | 0.6667  | 1.0    | 1.0       |
| gpt_5_4**english**r1                         | gpt-5.4         | english                 | failed    | --          | --           | --     | --      | --     | --        |
| gpt_5_4**gherkin_only**r1                    | gpt-5.4         | gherkin_only            | failed    | --          | --           | --     | --      | --     | --        |
| gpt_5_4**gherkin_plus_english**r1            | gpt-5.4         | gherkin_plus_english    | failed    | --          | --           | --     | --      | --     | --        |
| gpt_5_4**gherkin_plus_acceptance**r1         | gpt-5.4         | gherkin_plus_acceptance | failed    | --          | --           | --     | --      | --     | --        |

## Failures

- `gpt_5_4__english__r1`: Live generation failed for gpt_5_4**english**r1: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_only__r1`: Live generation failed for gpt_5_4**gherkin_only**r1: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_plus_english__r1`: Live generation failed for gpt_5_4**gherkin_plus_english**r1: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_plus_acceptance__r1`: Live generation failed for gpt_5_4**gherkin_plus_acceptance**r1: Agent execution timed out.; runtime_error=timeout

## Notes

- Scores are heuristic local signals based on keyword/pattern matching.
- Each feature score is the fraction of sub-checks that matched (0.0 to 1.0).
- Cross-feature interaction checks contribute to individual feature scores.
