# Gherkin Prompt Language Experiment Report

**Experiment ID**: `gherkin-prompt-language-v1`
**Generated at**: `2026-03-31T15:08:47.891668+00:00`
**Matrix mode**: `smoke`
**Replay mode**: `False`
**Evaluation kind**: `gherkin_heuristic_signal_v1`
**Output dir**: `/tmp/gherkin_smoke_results`

## Metric Semantics

| Report Column | Gherkin Meaning                            |
| ------------- | ------------------------------------------ |
| Baseline      | Scenario Coverage (12 scenario checks)     |
| Invariant     | Edge Case Handling (7 error scenarios)     |
| Proof         | Step Implementation (real code, not stubs) |
| Local         | Test Generation (tests matching scenarios) |
| Progress      | Behavioral Alignment (composite)           |
| Coverage      | Overall Coverage (composite)               |

## Summary

- Total conditions: 8
- Completed conditions: 7
- Failed conditions: 1

## Condition Table

| Condition                                    | Model           | Prompt                  | Status    | Scenario Cov | Edge Cases | Implementation | Tests | Behavioral | Overall |
| -------------------------------------------- | --------------- | ----------------------- | --------- | ------------ | ---------- | -------------- | ----- | ---------- | ------- |
| claude_opus_4_6**english**r1                 | claude-opus-4.6 | english                 | completed | 0.9167       | 0.8571     | 1.0            | 1.0   | 0.9246     | 0.9246  |
| claude_opus_4_6**gherkin_only**r1            | claude-opus-4.6 | gherkin_only            | completed | 0.0          | 0.0        | 0.0            | 0.0   | 0.0        | 0.0     |
| claude_opus_4_6**gherkin_plus_english**r1    | claude-opus-4.6 | gherkin_plus_english    | completed | 1.0          | 1.0        | 1.0            | 1.0   | 1.0        | 1.0     |
| claude_opus_4_6**gherkin_plus_acceptance**r1 | claude-opus-4.6 | gherkin_plus_acceptance | completed | 0.0          | 0.0        | 0.0            | 1.0   | 0.0        | 0.3333  |
| gpt_5_4**english**r1                         | gpt-5.4         | english                 | completed | 1.0          | 1.0        | 1.0            | 1.0   | 1.0        | 1.0     |
| gpt_5_4**gherkin_only**r1                    | gpt-5.4         | gherkin_only            | completed | 1.0          | 1.0        | 1.0            | 1.0   | 1.0        | 1.0     |
| gpt_5_4**gherkin_plus_english**r1            | gpt-5.4         | gherkin_plus_english    | completed | 1.0          | 1.0        | 1.0            | 1.0   | 1.0        | 1.0     |
| gpt_5_4**gherkin_plus_acceptance**r1         | gpt-5.4         | gherkin_plus_acceptance | failed    | --           | --         | --             | --    | --         | --      |

## Failures

- `gpt_5_4__gherkin_plus_acceptance__r1`: Live generation failed for gpt_5_4**gherkin_plus_acceptance**r1: Agent execution timed out.

## Notes

- Scores in this report are heuristic local signals, not authoritative eval scores.
- Scenario coverage checks for keyword presence of all 12 behavioral scenarios.
- Edge case handling checks the 7 error/negative scenarios specifically.
