# Opus 4.5 vs Sonnet 4.5: Workflow Adherence Benchmark

**Date**: 2025-11-26
**Task**: Create a simple greeting utility using TDD approach
**Framework**: amplihack CLI with `/amplihack:ultrathink` orchestration

## Executive Summary

**Critical Finding**: When given identical instructions through the amplihack framework, Sonnet 4.5 followed the complete 22-step DEFAULT_WORKFLOW.md while Opus 4.5 exercised judgment and skipped most workflow steps, treating it as a "simple task."

## Results Comparison

| Metric                      | Opus 4.5 | Sonnet 4.5  | Difference       |
| --------------------------- | -------- | ----------- | ---------------- |
| **Duration**                | 3m 23s   | 27m 1s      | Sonnet 8x longer |
| **Turns**                   | 18       | 65          | Sonnet 3.6x more |
| **Cost**                    | $3.54    | $6.52       | Sonnet 1.8x more |
| **Workflow Steps Executed** | ~3       | 22 (full)   | Sonnet 7x more   |
| **GitHub Issue Created**    | No       | Yes (#1683) | -                |
| **PR Created**              | No       | Yes (#1685) | -                |
| **Tests Written**           | 1        | 7           | Sonnet 7x more   |

## Workflow Adherence Detail

### Opus 4.5 Behavior

**Steps Executed:**

- Created `greeting.py` with `greet()` function
- Created `test_greeting.py` with 1 test
- Ran the test
- Reported completion

**Steps Skipped:**

- No workflow file reading or todo creation (Steps 0-2)
- No GitHub issue creation (Step 3)
- No feature branch (Step 4)
- No design phase (Steps 5-7)
- No review passes (Steps 10-13)
- No PR creation or commit workflow (Steps 14-21)

**Model's Reasoning**: "This is a simple internal utility function. No user-facing documentation required for a basic greet() function."

### Sonnet 4.5 Behavior

**Steps Executed (Full 22-step workflow):**

- Read DEFAULT_WORKFLOW.md
- Created todos for all workflow steps
- Created GitHub Issue #1683
- Created feature branch
- Wrote comprehensive tests (7 tests)
- Implemented the function
- Ran all review passes
- Created PR #1685
- Addressed power-steering checks

**Model's Reasoning**: Followed the workflow literally, treating `/amplihack:ultrathink` as mandatory orchestration requiring full workflow execution.

## Token Usage

### Opus 4.5

| Model                     | Input Tokens | Output Tokens | Cache Read  | Cost      |
| ------------------------- | ------------ | ------------- | ----------- | --------- |
| claude-opus-4-5-20251101  | 1,413        | 4,048         | 931,520     | $2.98     |
| claude-haiku-4-5-20251001 | 9,681        | 288           | -           | $0.04     |
| claude-opus-4-1-20250805  | -            | 98            | -           | $0.51     |
| **Total**                 | **11,094**   | **4,434**     | **931,520** | **$3.54** |

### Sonnet 4.5

| Model                      | Input Tokens | Output Tokens | Cache Read    | Cost      |
| -------------------------- | ------------ | ------------- | ------------- | --------- |
| claude-sonnet-4-5-20250929 | 13,895       | 60,963        | 7,771,152     | $5.70     |
| claude-haiku-4-5-20251001  | 95,456       | 2,225         | -             | $0.14     |
| claude-opus-4-1-20250805   | -            | 2,239         | -             | $0.67     |
| **Total**                  | **109,351**  | **65,427**    | **7,771,152** | **$6.52** |

## Key Insights

### 1. Judgment vs Literal Interpretation

- **Opus**: Applies judgment to assess task complexity and optimizes for efficiency
- **Sonnet**: Interprets instructions literally and follows workflows completely

### 2. Cost-Thoroughness Trade-off

- **Opus**: 46% cheaper but produces minimal development artifacts
- **Sonnet**: More expensive but generates complete artifacts (issue, PR, comprehensive tests)

### 3. Enterprise Workflow Implications

- **Opus**: Better suited for rapid prototyping or truly simple tasks
- **Sonnet**: Better suited for enterprise workflows requiring consistency and auditability

### 4. Ultrathink Interpretation

Both models received `/amplihack:ultrathink` prefix, but interpreted it differently:

- **Opus**: "Think carefully about this task" → still exercised judgment to skip steps
- **Sonnet**: "Execute the full orchestration workflow" → followed all 22 steps

## Recommendations

1. **For Opus**: Workflow instructions need stronger language indicating workflow steps are MANDATORY regardless of perceived task complexity

2. **For Sonnet**: Current behavior is appropriate for enterprise workflows; may want lighter workflows for trivial tasks

3. **For Framework**: Consider task complexity classification to select appropriate workflow depth automatically

## Benchmark Artifacts

- **Opus Session**: `59aaa60b-a324-4186-b265-7cdafab1cd97`
- **Sonnet Session**: `0b225098-38dc-46fc-95d8-7594cab24937`
- **Trace Logs**: Available in respective worktree `.claude-trace/` directories

---

_Benchmark conducted using amplihack framework v0.3.x with DEFAULT_WORKFLOW.md_
