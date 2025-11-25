---
name: workflow-enforcement
version: 1.0.0
description: Workflow step compliance guidance with mandatory step reminders and visual progress tracking. Reminds Claude to complete all workflow steps before PR creation.
auto_activates:
  - "start workflow"
  - "beginning DEFAULT_WORKFLOW"
  - "Step 0: Workflow Preparation"
explicit_triggers:
  - /amplihack:workflow-enforcement
related_files:
  - .claude/workflow/DEFAULT_WORKFLOW.md
  - .claude/tools/amplihack/hooks/workflow_tracker.py
implementation_status: specification
---

# Workflow Enforcement Skill

## Purpose

Guides Claude to complete all workflow steps by:

1. Reminding about step completion tracking (use TodoWrite or `.claude/runtime/workflow_state.yaml`)
2. Emphasizing mandatory steps (10, 16-17) that must not be skipped
3. Providing visual progress indicator format
4. Defining expected blocking behavior at checkpoints

**Implementation Status**: This skill is currently a SPECIFICATION that guides Claude behavior. Actual blocking enforcement requires either:

- Claude self-compliance (current state)
- Future: Pre-commit hooks or CI checks (not yet implemented)

## The Problem (Issue #1607)

Agents routinely skip mandatory workflow steps, especially:

- **Step 10**: Pre-commit code review (MANDATORY)
- **Step 16**: PR review (MANDATORY)
- **Step 17**: Review feedback implementation (MANDATORY)

Root causes:

- **Completion Bias**: Agent considers "PR created" as completion instead of "PR merged after review"
- **Context Decay**: After heavy implementation, agent loses sight of remaining steps
- **Autonomy Misapplication**: Confuses "autonomous implementation" with "skip mandatory process"

## How It Works

### 1. State Tracking (Recommended Pattern)

When activated, Claude SHOULD track workflow state. Options:

- **TodoWrite**: Use step-numbered todos (built-in, always available)
- **YAML state file**: Create `.claude/runtime/workflow_state.yaml` for persistent tracking

Example YAML state format:

```yaml
workflow_id: "session_20251125_143022"
workflow_name: DEFAULT
task_description: "Add authentication feature"
started_at: "2025-11-25T14:30:22"
current_step: 5
steps:
  0: { status: completed, timestamp: "2025-11-25T14:30:22" }
  1: { status: completed, timestamp: "2025-11-25T14:31:05" }
  2: { status: completed, timestamp: "2025-11-25T14:35:00" }
  3: { status: completed, timestamp: "2025-11-25T14:38:00" }
  4: { status: completed, timestamp: "2025-11-25T14:40:00" }
  5: { status: in_progress, timestamp: "2025-11-25T14:45:00" }
  10: { status: pending, mandatory: true }
  16: { status: pending, mandatory: true }
  17: { status: pending, mandatory: true }
  21: { status: pending }
mandatory_steps: [10, 16, 17]
```

### 2. Progress Indicator

Display progress after each step completion:

```
WORKFLOW PROGRESS [5/22] [#####.................] Step 5: Research and Design
Mandatory gates remaining: Step 10 (Review), Step 16 (PR Review), Step 17 (Feedback)
```

### 3. Mandatory Step Enforcement (Self-Compliance)

**Note**: This is guidance for Claude self-compliance, not automated enforcement.

Before Step 15 (Open PR):

```
ENFORCEMENT CHECK: Validating pre-PR requirements...
[X] Step 10: Pre-commit code review - REQUIRED BEFORE PR
Status: NOT COMPLETED
ACTION: You MUST invoke the reviewer agent and complete Step 10 before proceeding to Step 15.
```

Before Step 21 (Ensure Mergeable):

```
ENFORCEMENT CHECK: Validating completion requirements...
[X] Step 10: Pre-commit code review - COMPLETED
[X] Step 16: PR review - COMPLETED
[X] Step 17: Review feedback - COMPLETED
Status: ALL MANDATORY STEPS COMPLETE
Proceed to Step 21.
```

## Execution Instructions

When this skill activates:

### At Workflow Start (Step 0)

1. Create or update `.claude/runtime/workflow_state.yaml`
2. Initialize all 22 steps (0-21) with `pending` status
3. Mark mandatory steps (10, 16, 17)
4. Display initial progress indicator

### At Each Step Completion

1. Update step status to `completed` with timestamp
2. Update `current_step` to next step
3. Display progress indicator
4. If approaching mandatory step, display reminder

### At Mandatory Checkpoints

**Before Step 15 (Open PR as Draft)**:

- Validate Step 10 is completed
- If not, BLOCK and require Step 10 completion

**Before Step 21 (Ensure Mergeable)**:

- Validate Steps 10, 16, 17 are all completed
- If any missing, BLOCK and list required steps

### At Workflow End

1. Verify all steps completed (or explicitly skipped with reason)
2. Log final state to workflow_tracker.py
3. Clear workflow_state.yaml for next workflow

## Integration with TodoWrite

When you use TodoWrite, ensure step numbers match workflow tracking:

```python
TodoWrite(todos=[
    {"content": "Step 5: Research and Design - Use architect agent", "status": "completed", "activeForm": "..."},
    {"content": "Step 6: Retcon Documentation Writing", "status": "in_progress", "activeForm": "..."},
    ...
])
```

TodoWrite is the primary tracking mechanism. YAML state file is optional for additional persistence.

## Blocking Behavior (Self-Compliance Pattern)

When mandatory steps are skipped, Claude SHOULD display and follow this pattern:

```
WORKFLOW ENFORCEMENT: BLOCKED

Cannot proceed to Step 15 (Open PR as Draft).

MISSING MANDATORY STEP:
  Step 10: Pre-commit code review

  This step is REQUIRED to ensure code quality before creating a PR.
  The reviewer agent MUST be invoked to complete this step.

ACTION REQUIRED:
  1. Invoke reviewer agent for comprehensive code review
  2. Invoke security agent for security review
  3. Mark Step 10 as completed
  4. Then proceed to Step 15

Reference: Issue #1607 - Workflow step skipping causes quality issues
```

## Visual Progress Formats

### Standard Progress Bar

```
[##########............] 10/22 Steps Complete
```

### Detailed Status

```
WORKFLOW: DEFAULT (session_20251125_143022)
TASK: Add authentication feature
PROGRESS: 10/22 steps complete (45%)

Completed: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
Current: Step 10 (Pre-commit review)
Remaining: 11-21

MANDATORY GATES:
[X] Step 10 - In Progress
[ ] Step 16 - Pending
[ ] Step 17 - Pending
```

## State File Location

**Path**: `.claude/runtime/workflow_state.yaml`

This file is:

- Created when workflow starts
- Updated on each step change
- Cleared when workflow completes
- Read by power-steering for enforcement

## Error Recovery

If state file is missing or corrupt:

1. Check TodoWrite for current step information
2. Reconstruct state from workflow_tracker.py logs
3. If unrecoverable, prompt user to confirm current step

## Philosophy Alignment

- **Ruthless Simplicity**: Single YAML file for state, no complex infrastructure
- **Guidance over Enforcement**: Provides clear guidance; Claude self-compliance determines effectiveness
- **Modular**: Self-contained skill with clear integration points
- **Fail-Open for Errors**: If tracking fails, log and continue (never block users on bugs)

## Limitations

This skill is a **specification**, not automated enforcement:

- Relies on Claude reading and following this skill's guidance
- No pre-commit hooks or CI checks currently enforce compliance
- The same cognitive patterns that cause step-skipping can also skip this skill's guidance
- For hard enforcement, consider implementing pre-commit or CI-based checks

## Related Components

- **DEFAULT_WORKFLOW.md**: Canonical workflow definition with Step 0 guidance
- **workflow_tracker.py**: Historical logging (JSONL format)
- **power_steering_checker.py**: Session-end enforcement (transcript-based)
- **considerations.yaml**: `dev_workflow_complete` consideration
