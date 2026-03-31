# TLA+ Prompt Language Experiment Report

**Experiment ID**: `tla-prompt-language-v1`
**Generated at**: `2026-03-31T07:40:10.974757+00:00`
**Matrix mode**: `smoke`
**Replay mode**: `False`
**Evaluation kind**: `heuristic_signal_v2`
**Output dir**: `/tmp/tla-experiment-live.pQjsmw`

## Summary

- Total conditions: 8
- Completed conditions: 6
- Failed conditions: 2

## Condition Table

| Condition | Model | SDK | Prompt | Status | Heuristic Baseline | Heuristic Invariant | Heuristic Proof | Heuristic Local | Heuristic Progress | Heuristic Coverage |
|-----------|-------|-----|--------|--------|--------------------|---------------------|-----------------|-----------------|--------------------|--------------------|
| claude_opus_4_6__english__r1 | claude-opus-4.6 | claude | english | completed | 0.4286 | 0.5 | 0.0 | 0.0 | 0.0 | 0.2857 |
| claude_opus_4_6__tla_only__r1 | claude-opus-4.6 | claude | tla_only | completed | 0.8571 | 0.75 | 1.0 | 1.0 | 1.0 | 0.8571 |
| claude_opus_4_6__tla_plus_english__r1 | claude-opus-4.6 | claude | tla_plus_english | completed | 0.4286 | 0.5 | 1.0 | 0.0 | 0.0 | 0.4286 |
| claude_opus_4_6__tla_plus_refinement__r1 | claude-opus-4.6 | claude | tla_plus_refinement | completed | 0.8571 | 0.75 | 1.0 | 1.0 | 1.0 | 0.8571 |
| gpt_5_4__english__r1 | gpt-5.4 | copilot | english | completed | 0.7143 | 0.75 | 0.0 | 0.0 | 1.0 | 0.5714 |
| gpt_5_4__tla_only__r1 | gpt-5.4 | copilot | tla_only | failed | -- | -- | -- | -- | -- | -- |
| gpt_5_4__tla_plus_english__r1 | gpt-5.4 | copilot | tla_plus_english | completed | 0.5714 | 0.5 | 1.0 | 0.0 | 1.0 | 0.5714 |
| gpt_5_4__tla_plus_refinement__r1 | gpt-5.4 | copilot | tla_plus_refinement | failed | -- | -- | -- | -- | -- | -- |

## Artifacts

| Condition | Generated Artifact | Evaluation | Raw Response |
|-----------|--------------------|------------|--------------|
| claude_opus_4_6__english__r1 | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__english__r1/generated_artifact.md | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__english__r1/evaluation.json | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__english__r1/raw_response.txt |
| claude_opus_4_6__tla_only__r1 | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_only__r1/generated_artifact.md | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_only__r1/evaluation.json | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_only__r1/raw_response.txt |
| claude_opus_4_6__tla_plus_english__r1 | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_plus_english__r1/generated_artifact.md | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_plus_english__r1/evaluation.json | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_plus_english__r1/raw_response.txt |
| claude_opus_4_6__tla_plus_refinement__r1 | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_plus_refinement__r1/generated_artifact.md | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_plus_refinement__r1/evaluation.json | /tmp/tla-experiment-live.pQjsmw/claude_opus_4_6__tla_plus_refinement__r1/raw_response.txt |
| gpt_5_4__english__r1 | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__english__r1/generated_artifact.md | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__english__r1/evaluation.json | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__english__r1/raw_response.txt |
| gpt_5_4__tla_only__r1 | -- | -- | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__tla_only__r1/raw_response.txt |
| gpt_5_4__tla_plus_english__r1 | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__tla_plus_english__r1/generated_artifact.md | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__tla_plus_english__r1/evaluation.json | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__tla_plus_english__r1/raw_response.txt |
| gpt_5_4__tla_plus_refinement__r1 | -- | -- | /tmp/tla-experiment-live.pQjsmw/gpt_5_4__tla_plus_refinement__r1/raw_response.txt |

## TLC Validation

- Runner: `tlc`
- Return code: `0`
- Command: `/usr/local/bin/tlc -config DistributedRetrievalContract.cfg -metadir /tmp/tla-tlc-fmcjon58 DistributedRetrievalContract`

## Failures

- `gpt_5_4__tla_only__r1`: Live generation failed for gpt_5_4__tla_only__r1: Agent execution timed out.; runtime_error=timeout
- `gpt_5_4__tla_plus_refinement__r1`: Live generation failed for gpt_5_4__tla_plus_refinement__r1: Agent execution timed out.; runtime_error=timeout

## Notes

- Scores in this report are heuristic local signals, not authoritative eval scores.
- Authoritative grading and packaged reports still belong in `amplihack-agent-eval`.
