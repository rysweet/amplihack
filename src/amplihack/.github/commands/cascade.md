# GitHub Copilot Command Reference: cascade

**Source**: `.claude/commands/amplihack/cascade.md`

---

## Command Metadata

- **name**: amplihack:cascade
- **version**: 1.0.0
- **description**: Fallback cascade pattern for resilient operations
- **triggers**: 
- **invokes**: 
- **- type**: workflow
- **path**: .claude/workflow/CASCADE_WORKFLOW.md
- **philosophy**: 
- **- principle**: Ruthless Simplicity
- **application**: Simple fallback hierarchy ensures completion
- **dependencies**: 
- **required**: 
- **optional**: 
- **examples**: 
- **- "/amplihack**: cascade Retrieve user data with multiple sources"

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/cascade.md

# Use patterns from this command
gh copilot suggest --context .github/commands/cascade.md "your task"
```

---

## Original Command Documentation


# Fallback Cascade Command

## Usage

`/amplihack:cascade <TASK_DESCRIPTION>`

## Purpose

Execute fallback cascade pattern for resilient operations. Graceful degradation from optimal → pragmatic → minimal ensures reliable completion.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Import the orchestrator**:

   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path.cwd() / ".claude/tools/amplihack"))
   from orchestration.patterns.cascade import run_cascade
   ```

2. **Execute the pattern**:

   ```python
   result = run_cascade(
       task_prompt="{TASK_DESCRIPTION}",
       fallback_strategy="quality",  # or "service", "freshness"
       timeout_strategy="balanced",  # or "aggressive", "patient"
       working_dir=Path.cwd()
   )
   ```

3. **Display results**:
   - Show final result and cascade level reached
   - Explain any degradation from optimal
   - Report which fallback succeeded
   - Report session_id for traceability
   - Link to logs: `.claude/runtime/logs/cascade_<timestamp>/`

4. **Manual fallback** (if orchestrator unavailable):
   - Read workflow: `.claude/workflow/CASCADE_WORKFLOW.md`
   - Execute steps manually with TodoWrite tracking

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
