# Opus 4.5 vs Sonnet 4.5 Benchmark Report (v2)

**Date**: 2025-11-26
**Methodology**: Using `amplihack` CLI with `/amplihack:ultrathink` prefix
**Task**: Create a simple greeting utility (TDD approach)

## Executive Summary

**CRITICAL FINDING**: Sonnet 4.5 followed the 22-step DEFAULT_WORKFLOW.md **completely** while Opus 4.5 treated it as a "simple task" and skipped most workflow steps.

## Key Metrics Comparison

| Metric                   | Opus 4.5           | Sonnet 4.5           | Ratio     |
| ------------------------ | ------------------ | -------------------- | --------- |
| **Duration**             | 3m 23s (203,545ms) | 27m 1s (1,621,269ms) | 8x longer |
| **Turns**                | 18                 | 65                   | 3.6x more |
| **Cost**                 | $3.54              | $6.52                | 1.8x more |
| **Workflow Steps**       | ~3 (minimal)       | 22 (full)            | 7x more   |
| **GitHub Issue Created** | No                 | Yes (#1683)          | -         |
| **PR Created**           | No                 | Yes (#1685)          | -         |
| **Tests Written**        | 1                  | 7                    | 7x more   |

## Workflow Adherence Analysis

### Opus 4.5 Behavior

```
What Opus Did:
- Created greeting.py with greet() function
- Created test_greeting.py with 1 test
- Ran the test
- Reported completion

What Opus Skipped:
- Step 0-2: No workflow reading or todo creation
- Step 3: No GitHub issue created
- Step 4: No feature branch
- Step 5-7: No design phase
- Step 10-13: No review passes
- Step 14-21: No PR creation, no commit workflow
```

**Opus Reasoning**: "This is a simple internal utility function. No user-facing documentation required for a basic greet() function."

### Sonnet 4.5 Behavior

```
What Sonnet Did:
- Read DEFAULT_WORKFLOW.md
- Created todos for all 22 steps
- Created GitHub Issue #1683
- Created feature branch
- Wrote comprehensive tests (7 tests)
- Implemented the function
- Ran review passes
- Created PR #1685
- Addressed power-steering checks
```

**Sonnet Reasoning**: Followed the workflow literally, treating `/amplihack:ultrathink` as mandatory orchestration.

## Model Usage Breakdown

### Opus v2

```json
{
  "claude-haiku-4-5-20251001": {
    "inputTokens": 9681,
    "outputTokens": 288,
    "costUSD": 0.04
  },
  "claude-opus-4-5-20251101": {
    "inputTokens": 1413,
    "outputTokens": 4048,
    "cacheReadInputTokens": 931520,
    "costUSD": 2.98
  },
  "claude-opus-4-1-20250805": {
    "outputTokens": 98,
    "costUSD": 0.51
  }
}
```

### Sonnet v2

```json
{
  "claude-haiku-4-5-20251001": {
    "inputTokens": 95456,
    "outputTokens": 2225,
    "costUSD": 0.14
  },
  "claude-sonnet-4-5-20250929": {
    "inputTokens": 13895,
    "outputTokens": 60963,
    "cacheReadInputTokens": 7771152,
    "costUSD": 5.7
  },
  "claude-opus-4-1-20250805": {
    "outputTokens": 2239,
    "costUSD": 0.67
  }
}
```

## Key Findings

### 1. Workflow Judgment Difference

- **Opus**: Uses judgment to assess task complexity, skips workflow for "simple" tasks
- **Sonnet**: Follows workflow literally regardless of task complexity

### 2. Cost Efficiency vs Thoroughness Trade-off

- **Opus**: 1.8x cheaper but produces minimal artifacts
- **Sonnet**: More expensive but produces complete development artifacts (issue, PR, comprehensive tests)

### 3. Real-World Implications

- **For Simple Tasks**: Opus is faster and cheaper
- **For Production Workflows**: Sonnet follows enterprise practices better

### 4. Ultrathink Effectiveness

Both models received `/amplihack:ultrathink` prefix, but:

- Opus interpreted it as "think carefully" but still exercised judgment
- Sonnet interpreted it as "follow the full orchestration workflow"

## Recommendations

1. **For Opus**: The workflow instructions need to be more explicit about ALWAYS following the workflow regardless of perceived task complexity.

2. **For Sonnet**: Current behavior is appropriate for enterprise workflows but may be overkill for truly trivial tasks.

3. **For Benchmarking**: Use more complex tasks to see differentiation in quality, not just workflow adherence.

## Raw JSON Results

### Opus v2

- Session ID: 59aaa60b-a324-4186-b265-7cdafab1cd97
- Full results: `~/.amplihack/.claude/runtime/benchmarks/opus_v2/result.json`
- Trace log: `worktrees/benchmark-opus-v2/.claude-trace/log-2025-11-26-03-33-05.jsonl`

### Sonnet v2

- Session ID: 0b225098-38dc-46fc-95d8-7594cab24937
- Full results: `~/.amplihack/.claude/runtime/benchmarks/sonnet_v2/result.json`
- Trace log: `worktrees/benchmark-sonnet-v2/.claude-trace/log-2025-11-26-03-34-36.jsonl`

## Conclusion

**Sonnet 4.5 demonstrates significantly better workflow adherence** than Opus 4.5 when using the amplihack framework with ultrathink orchestration. Opus optimizes for efficiency and uses judgment to skip unnecessary steps, while Sonnet follows instructions literally.

For enterprise development workflows where consistency and auditability matter, Sonnet's behavior is preferable. For rapid prototyping or truly simple tasks, Opus's judgment-based approach may be more practical.

---

_Generated by amplihack benchmark v2 - 2025-11-26_
