# Fallback Cascade Command

## Usage

`/cascade <TASK_DESCRIPTION>`

## Purpose

Execute fallback cascade pattern for resilient operations. Graceful degradation from optimal → pragmatic → minimal ensures reliable completion.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Read the workflow file**: `.claude/workflow/CASCADE_WORKFLOW.md`
2. **Create a comprehensive todo list** using TodoWrite with all workflow steps
3. **Execute each step systematically**, marking todos as in_progress and completed
4. **Follow the cascade pattern**:
   - Attempt primary (optimal) approach with timeout
   - If fails, attempt secondary (pragmatic) approach
   - If fails, attempt tertiary (minimal) approach
   - Report degradation level
5. **Document cascade path** taken and degradation
6. **Track decisions** in `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`

## When to Use

Use for **operations with multiple viable approaches**:

- External API calls (primary service, backup service, cached fallback)
- Code generation (GPT-4, Claude, cached templates)
- Data retrieval (database, cache, defaults)
- Complex computations (exact algorithm, approximation, heuristic)

## Cost-Benefit

- **Cost:** 1.1-2x execution time (only on failures)
- **Benefit:** 95%+ reliability vs 70-80% single approach
- **ROI Positive when:** Operation reliability > availability requirements

## Task Description

Execute the following task with fallback cascade:

```
{TASK_DESCRIPTION}
```

## Configuration

The workflow can be customized by editing `.claude/workflow/CASCADE_WORKFLOW.md`:

- Timeout strategy: Aggressive (5/2/1s), Balanced (30/10/5s), Patient (120/30/10s)
- Fallback types: Service, Quality, Freshness
- Degradation notification: Silent, Warning, Explicit, Interactive
- Number of cascade levels: 2-4

## Success Metrics

From research (PR #946):

- Reliability Improvement: 95%+ vs 70-80% single approach
- Graceful Degradation: 98% of failures handled successfully
- User Impact: 90%+ users unaware of fallbacks occurring
