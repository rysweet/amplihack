# Workflow Enforcement Skill

Guides Claude to complete all workflow steps by providing tracking patterns and emphasizing mandatory steps.

**Implementation Status**: This is a SPECIFICATION skill that provides guidance for Claude self-compliance. Actual blocking requires Claude to follow this guidance.

## Problem Statement

In PR #1606, the agent skipped mandatory code review steps (Steps 10, 16-17 of DEFAULT_WORKFLOW.md), completing implementation and creating a PR without executing review. This skill was created in response to Issue #1607.

## Quick Start

The skill auto-activates when you begin a DEFAULT_WORKFLOW. To invoke explicitly:

```
User: "Invoke the workflow-enforcement skill"
Claude: *loads skill, creates workflow_state.yaml, displays progress*
```

## Key Features

1. **State Tracking Pattern**: Recommends tracking in TodoWrite or `.claude/runtime/workflow_state.yaml`
2. **Visual Progress**: Shows `[######............] 6/22 Steps Complete` after each step
3. **Mandatory Gates (Guidance)**: Reminds Claude to complete Step 10 before Step 15 (PR creation)
4. **Completion Validation (Guidance)**: Reminds Claude that Steps 10, 16, 17 are required before Step 21

## Mandatory Steps

| Step | Name                           | Enforcement Point            |
| ---- | ------------------------------ | ---------------------------- |
| 10   | Pre-commit code review         | Before Step 15 (PR creation) |
| 16   | PR review                      | Before Step 21 (mergeable)   |
| 17   | Review feedback implementation | Before Step 21 (mergeable)   |

## State File Format

Location: `.claude/runtime/workflow_state.yaml`

```yaml
workflow_id: "session_20251125_143022"
workflow_name: DEFAULT
task_description: "Add authentication feature"
started_at: "2025-11-25T14:30:22"
current_step: 5
steps:
  0: { status: completed, timestamp: "2025-11-25T14:30:22" }
  5: { status: in_progress }
  10: { status: pending, mandatory: true }
mandatory_steps: [10, 16, 17]
```

## Integration Points

- **TodoWrite**: Step numbers in todos should match workflow_state.yaml
- **workflow_tracker.py**: Historical logging (complements state tracking)
- **power_steering**: Uses state for `dev_workflow_complete` consideration

## Design Philosophy

- **Ruthless Simplicity**: Single YAML state file
- **Guidance over Enforcement**: Provides patterns; Claude self-compliance determines effectiveness
- **Fail-Open**: On errors, log and continue (never block users on bugs)
- **Modular**: Self-contained with clear integration points

## Limitations

- This is guidance, not automated enforcement
- Relies on Claude reading and following the skill
- For hard enforcement, implement pre-commit or CI checks

## Related Files

- `.claude/workflow/DEFAULT_WORKFLOW.md` - Canonical workflow definition
- `.claude/tools/amplihack/hooks/workflow_tracker.py` - Historical logging
- `.claude/tools/amplihack/considerations.yaml` - Power steering checks

## Reference

- Issue #1607: Workflow Enforcement - Prevent Agent Skipping of Mandatory Steps
- PR #1606: Example of workflow violation that prompted this skill
