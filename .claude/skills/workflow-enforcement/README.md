# Workflow Enforcement Skill

Guides Claude to complete all workflow steps by providing tracking patterns and emphasizing mandatory steps.

**Implementation Status**: This is a SPECIFICATION skill that provides guidance for Claude self-compliance. Actual blocking requires Claude to follow this guidance - it cannot force compliance.

## Problem Statement

In PR #1606, the agent skipped mandatory code review steps (Steps 10, 16-17 of DEFAULT_WORKFLOW.md), completing implementation and creating a PR without executing review. This skill was created in response to Issue #1607.

## Quick Start

The skill auto-activates when you begin a DEFAULT_WORKFLOW. To invoke explicitly:

```
User: "Invoke the workflow-enforcement skill"
Claude: *loads skill, creates workflow_state.yaml or TodoWrite entries, displays progress*
```

**Minimal Usage (TodoWrite)**:

```
1. At Step 0, create TodoWrite entries for all 22 steps
2. Display progress: [0/22] Step 0: Workflow Preparation
3. Before Step 15, verify Step 10 is completed
4. Before Step 21, verify Steps 10, 16, 17 are completed
```

## Key Features

1. **State Tracking Pattern**: Track progress via TodoWrite or `~/.amplihack/.claude/runtime/workflow_state.yaml`
2. **Visual Progress**: `[######............] 6/22 Steps Complete` after each step
3. **Mandatory Gates (Guidance)**: Reminds Claude to complete Step 10 before Step 15 (PR creation)
4. **Completion Validation (Guidance)**: Steps 10, 16, 17 required before Step 21
5. **Power Steering Integration**: Session-end verification via `dev_workflow_complete` check

## Mandatory Steps

| Step | Name                           | Enforcement Point            |
| ---- | ------------------------------ | ---------------------------- |
| 0    | Workflow Preparation           | Before any implementation    |
| 10   | Pre-commit code review         | Before Step 15 (PR creation) |
| 16   | PR review                      | Before Step 21 (mergeable)   |
| 17   | Review feedback implementation | Before Step 21 (mergeable)   |

## State File Format

**Template**: `~/.amplihack/.claude/templates/workflow_state.yaml.template`
**Active**: `~/.amplihack/.claude/runtime/workflow_state.yaml`

```yaml
workflow_id: "session_20251125_143022"
workflow_name: DEFAULT
task_description: "Add authentication feature"
started_at: "2025-11-25T14:30:22"
current_step: 10
steps:
  0: { status: completed, timestamp: "2025-11-25T14:30:22", mandatory: true }
  10: { status: in_progress, mandatory: true }
  16: { status: pending, mandatory: true }
  17: { status: pending, mandatory: true }
mandatory_steps: [0, 10, 16, 17]
checkpoints:
  before_step_15:
    required_steps: [10]
  before_step_21:
    required_steps: [10, 16, 17]
```

## Visual Progress Examples

**Standard**:

```
WORKFLOW PROGRESS [10/22] [##########............] Step 10: Pre-commit review
Mandatory gates: 0[X] 10[>] 16[ ] 17[ ]
```

**Detailed**:

```
+======================================================================+
|                    DEFAULT WORKFLOW - Progress                        |
+======================================================================+
|  Progress: 10/22 steps (45%)                                         |
|  [##########............] 10/22                                       |
+----------------------------------------------------------------------+
|  MANDATORY GATES:                                                    |
|    [X] Step 0  - Workflow Preparation      COMPLETED                 |
|    [>] Step 10 - Pre-commit Review         IN PROGRESS               |
|    [ ] Step 16 - PR Review                 PENDING                   |
|    [ ] Step 17 - Feedback Implementation   PENDING                   |
+======================================================================+
```

## Integration Points

- **TodoWrite**: Step numbers in todos should match workflow_state.yaml
- **workflow_tracker.py**: Historical logging (complements state tracking)
- **power_steering**: Uses `dev_workflow_complete` consideration for session-end checks

## Honest Limitations

- **Guidance only**: Cannot force Claude to comply
- **Auto-activation dependent**: Relies on triggers being matched
- **No real-time blocking**: Only session-end verification exists
- **Same cognitive patterns**: The issues that cause step-skipping can cause this skill to be ignored

## Future Work

1. **Phase 2**: Power steering reads workflow_state.yaml directly
2. **Phase 3**: Pre-commit hook integration for hard blocking
3. **Phase 4**: CI gate for workflow compliance

## Design Philosophy

- **Ruthless Simplicity**: Single YAML state file
- **Zero-BS**: Honest about being guidance, not enforcement
- **Fail-Open**: On errors, log and continue
- **Modular**: Self-contained with clear integration points

## Related Files

- `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` - Canonical workflow definition
- `~/.amplihack/.claude/templates/workflow_state.yaml.template` - State file template
- `~/.amplihack/.claude/tools/amplihack/hooks/workflow_tracker.py` - Historical logging
- `~/.amplihack/.claude/tools/amplihack/considerations.yaml` - Power steering checks

## Reference

- Issue #1607: Workflow Enforcement - Prevent Agent Skipping of Mandatory Steps
- PR #1606: Example of workflow violation that prompted this skill
