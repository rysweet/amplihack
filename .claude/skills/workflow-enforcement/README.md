# Workflow Enforcement Skill

Prevents workflow step skipping by tracking completion state and blocking on mandatory steps.

## Problem Statement

In PR #1606, the agent skipped mandatory code review steps (Steps 10, 16-17 of DEFAULT_WORKFLOW.md), completing implementation and creating a PR without executing review. This skill was created in response to Issue #1607.

## Quick Start

The skill auto-activates when you begin a DEFAULT_WORKFLOW. To invoke explicitly:

```
User: "Invoke the workflow-enforcement skill"
Claude: *loads skill, creates workflow_state.yaml, displays progress*
```

## Key Features

1. **State Tracking**: Persists workflow progress to `.claude/runtime/workflow_state.yaml`
2. **Visual Progress**: Shows `[######............] 6/22 Steps Complete` after each step
3. **Mandatory Gates**: Blocks Step 15 (PR creation) until Step 10 (review) is complete
4. **Completion Validation**: Requires Steps 10, 16, 17 before Step 21 (mergeable)

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
- **Zero-BS**: Actually blocks skipped steps (not just warnings)
- **Fail-Open**: On errors, log and continue (never block users on bugs)
- **Modular**: Self-contained with clear integration points

## Related Files

- `.claude/workflow/DEFAULT_WORKFLOW.md` - Canonical workflow definition
- `.claude/tools/amplihack/hooks/workflow_tracker.py` - Historical logging
- `.claude/tools/amplihack/considerations.yaml` - Power steering checks

## Reference

- Issue #1607: Workflow Enforcement - Prevent Agent Skipping of Mandatory Steps
- PR #1606: Example of workflow violation that prompted this skill
