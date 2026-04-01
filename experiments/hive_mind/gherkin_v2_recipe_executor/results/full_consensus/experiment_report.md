# Gherkin v2 Recipe Step Executor Experiment Report

**Experiment ID**: `gherkin-v2-recipe-executor`
**Generated at**: `2026-04-01T07:06:35.815417+00:00`
**Matrix mode**: `full`
**Replay mode**: `False`
**Evaluation kind**: `agent_consensus_v1`
**Output dir**: `experiments/hive_mind/gherkin_v2_recipe_executor/results/full_consensus`

## Summary

- Total conditions: 24
- Completed conditions: 13
- Failed conditions: 11

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

| Condition                                    | Model           | Prompt                  | Status    | Cond   | Deps   | Retry  | T/O    | Output | SubRec | Gen(s) | Eval(s) | Eval Tokens |
| -------------------------------------------- | --------------- | ----------------------- | --------- | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------- | ----------- |
| claude_opus_4_6**english**r1                 | claude-opus-4.6 | english                 | completed | 1.0    | 0.0    | 1.0    | 1.0    | 0.6667 | 1.0    | 110.3  | 163.5   | 0           |
| claude_opus_4_6**english**r2                 | claude-opus-4.6 | english                 | completed | 1.0    | 0.5    | 1.0    | 1.0    | 0.0    | 1.0    | 109.7  | 300.0   | 0           |
| claude_opus_4_6**english**r3                 | claude-opus-4.6 | english                 | completed | 1.0    | 0.0    | 1.0    | 1.0    | 0.0    | 0.6667 | 111.4  | 225.0   | 0           |
| claude_opus_4_6**gherkin_only**r1            | claude-opus-4.6 | gherkin_only            | completed | 1.0    | 1.0    | 1.0    | 0.6667 | 1.0    | 1.0    | 121.3  | 86.4    | 0           |
| claude_opus_4_6**gherkin_only**r2            | claude-opus-4.6 | gherkin_only            | completed | 1.0    | 1.0    | 0.5    | 1.0    | 1.0    | 1.0    | 671.5  | 138.6   | 0           |
| claude_opus_4_6**gherkin_only**r3            | claude-opus-4.6 | gherkin_only            | completed | 1.0    | 0.3333 | 1.0    | 0.6667 | 1.0    | 1.0    | 339.5  | 209.5   | 0           |
| claude_opus_4_6**gherkin_plus_english**r1    | claude-opus-4.6 | gherkin_plus_english    | completed | 1.0    | 1.0    | 1.0    | 1.0    | 1.0    | 1.0    | 754.4  | 246.3   | 0           |
| claude_opus_4_6**gherkin_plus_english**r2    | claude-opus-4.6 | gherkin_plus_english    | completed | 1.0    | 1.0    | 1.0    | 0.3333 | 1.0    | 1.0    | 96.4   | 150.4   | 0           |
| claude_opus_4_6**gherkin_plus_english**r3    | claude-opus-4.6 | gherkin_plus_english    | completed | 0.5    | 0.5    | 0.5    | 0.0    | 0.5    | 0.5    | 285.6  | 84.8    | 0           |
| claude_opus_4_6**gherkin_plus_acceptance**r1 | claude-opus-4.6 | gherkin_plus_acceptance | completed | 0.6667 | 0.6667 | 0.6667 | 0.6667 | 0.6667 | 0.6667 | 749.5  | 138.9   | 0           |
| claude_opus_4_6**gherkin_plus_acceptance**r2 | claude-opus-4.6 | gherkin_plus_acceptance | completed | 1.0    | 1.0    | 1.0    | 1.0    | 1.0    | 1.0    | 100.0  | 195.3   | 0           |
| claude_opus_4_6**gherkin_plus_acceptance**r3 | claude-opus-4.6 | gherkin_plus_acceptance | completed | 1.0    | 1.0    | 1.0    | 1.0    | 1.0    | 1.0    | 270.0  | 196.4   | 0           |
| gpt_5_4**english**r1                         | gpt-5.4         | english                 | failed    | --     | --     | --     | --     | --     | --     | 305.6  | 0.0     | 0           |
| gpt_5_4**english**r2                         | gpt-5.4         | english                 | failed    | --     | --     | --     | --     | --     | --     | 304.4  | 0.0     | 0           |
| gpt_5_4**english**r3                         | gpt-5.4         | english                 | failed    | --     | --     | --     | --     | --     | --     | 306.2  | 0.0     | 0           |
| gpt_5_4**gherkin_only**r1                    | gpt-5.4         | gherkin_only            | failed    | --     | --     | --     | --     | --     | --     | 303.9  | 0.0     | 0           |
| gpt_5_4**gherkin_only**r2                    | gpt-5.4         | gherkin_only            | failed    | --     | --     | --     | --     | --     | --     | 303.9  | 0.0     | 0           |
| gpt_5_4**gherkin_only**r3                    | gpt-5.4         | gherkin_only            | failed    | --     | --     | --     | --     | --     | --     | 303.9  | 0.0     | 0           |
| gpt_5_4**gherkin_plus_english**r1            | gpt-5.4         | gherkin_plus_english    | completed | 1.0    | 1.0    | 0.0    | 1.0    | 1.0    | 1.0    | 298.5  | 201.5   | 0           |
| gpt_5_4**gherkin_plus_english**r2            | gpt-5.4         | gherkin_plus_english    | failed    | --     | --     | --     | --     | --     | --     | 303.9  | 0.0     | 0           |
| gpt_5_4**gherkin_plus_english**r3            | gpt-5.4         | gherkin_plus_english    | failed    | --     | --     | --     | --     | --     | --     | 304.0  | 0.0     | 0           |
| gpt_5_4**gherkin_plus_acceptance**r1         | gpt-5.4         | gherkin_plus_acceptance | failed    | --     | --     | --     | --     | --     | --     | 306.3  | 0.0     | 0           |
| gpt_5_4**gherkin_plus_acceptance**r2         | gpt-5.4         | gherkin_plus_acceptance | failed    | --     | --     | --     | --     | --     | --     | 304.7  | 0.0     | 0           |
| gpt_5_4**gherkin_plus_acceptance**r3         | gpt-5.4         | gherkin_plus_acceptance | failed    | --     | --     | --     | --     | --     | --     | 305.5  | 0.0     | 0           |

## Per-Variant Statistics

| Variant                 | N   | Cond           | Deps           | Retry          | T/O            | Output         | SubRec         | AVG   |
| ----------------------- | --- | -------------- | -------------- | -------------- | -------------- | -------------- | -------------- | ----- |
| english                 | 3   | 1.000 +/-0.000 | 0.167 +/-0.717 | 1.000 +/-0.000 | 1.000 +/-0.000 | 0.222 +/-0.956 | 0.889 +/-0.478 | 0.713 |
| gherkin_only            | 3   | 1.000 +/-0.000 | 0.778 +/-0.956 | 0.833 +/-0.717 | 0.778 +/-0.478 | 1.000 +/-0.000 | 1.000 +/-0.000 | 0.898 |
| gherkin_plus_acceptance | 3   | 0.889 +/-0.478 | 0.889 +/-0.478 | 0.889 +/-0.478 | 0.889 +/-0.478 | 0.889 +/-0.478 | 0.889 +/-0.478 | 0.889 |
| gherkin_plus_english    | 4   | 0.875 +/-0.398 | 0.875 +/-0.398 | 0.625 +/-0.762 | 0.583 +/-0.795 | 0.875 +/-0.398 | 0.875 +/-0.398 | 0.785 |

## Token Usage Summary

- Total generation tokens: 0
- Total evaluation tokens: 0
- Total generation time: 7370.7s
- Total evaluation time: 2336.6s

## Failures

- `gpt_5_4__english__r1`: Live generation failed for gpt_5_4**english**r1: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__english__r2`: Live generation failed for gpt_5_4**english**r2: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__english__r3`: Live generation failed for gpt_5_4**english**r3: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_only__r1`: Live generation failed for gpt_5_4**gherkin_only**r1: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_only__r2`: Live generation failed for gpt_5_4**gherkin_only**r2: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_only__r3`: Live generation failed for gpt_5_4**gherkin_only**r3: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_plus_english__r2`: Live generation failed for gpt_5_4**gherkin_plus_english**r2: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_plus_english__r3`: Live generation failed for gpt_5_4**gherkin_plus_english**r3: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_plus_acceptance__r1`: Live generation failed for gpt_5_4**gherkin_plus_acceptance**r1: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_plus_acceptance__r2`: Live generation failed for gpt_5_4**gherkin_plus_acceptance**r2: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__gherkin_plus_acceptance__r3`: Live generation failed for gpt_5_4**gherkin_plus_acceptance**r3: Agent execution timed out.; runtime_error=timeout

## Notes

- Evaluation uses agent_consensus_v1: multiple independent LLM agents judge each feature.
- Consensus score = fraction of agents voting PASS per feature.
- Statistics include mean, 95% CI (t-distribution) when N >= 2.
