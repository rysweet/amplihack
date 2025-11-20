---
name: ultrathink-orchestrator
version: 1.0.0
description: Auto-invokes ultrathink workflow for any work request (experimental default orchestrator)
auto_activate: true
priority: 5
triggers:
  - "implement"
  - "create"
  - "build"
  - "add"
  - "fix"
  - "update"
  - "refactor"
  - "design"
experimental: true
---

# Ultrathink Orchestrator Skill (EXPERIMENTAL)

**⚠️ EXPERIMENTAL FEATURE**: This skill automatically invokes ultrathink workflow for work requests.

## Purpose

Automatically trigger ultrathink workflow orchestration for development tasks that don't match more specific skills.

## Auto-Activation

**Priority**: 5 (LOW - other skills checked first)
**Triggers**: Common work request patterns (implement, create, build, add, fix, etc.)

## Behavior

When activated:

1. **Detect Work Request**: Identify that user is requesting implementation work
2. **Check Specificity**: Ensure no higher-priority skill matches better
3. **Estimate Complexity**: Analyze task complexity (simple/moderate/complex)
4. **Confirm with User**: Ask for confirmation before proceeding
5. **Invoke Ultrathink**: Execute default-workflow via ultrathink pattern

## Complexity Estimation

**Simple (1-3 files)**:
- Single function or small change
- Clear requirements
- No dependencies

**Moderate (4-10 files)**:
- Feature spanning multiple components
- Some ambiguity in requirements
- Few dependencies

**Complex (10+ files)**:
- Major feature or refactoring
- Unclear requirements
- Many dependencies
- Architecture changes

## Confirmation Pattern

```
I detected a [COMPLEXITY] work request: "[USER REQUEST]"

Would you like me to use /ultrathink to orchestrate this work?
- Estimated scope: [X] files, [Y] steps
- Workflow: default-workflow (13 steps)
- Time estimate: [Z] minutes

[Yes] - Proceed with ultrathink orchestration
[No] - I'll work on this directly without workflow
[Custom] - Let me clarify the requirements first
```

## Implementation

When confirmed, invoke the default-workflow skill:

```
Invoke the `default-workflow` skill to execute this task following
the 13-step development workflow in DEFAULT_WORKFLOW.md.
```

## Safeguards

1. **Always confirm**: Never auto-execute without user approval
2. **Complexity awareness**: Show estimated scope before proceeding
3. **Escape hatch**: Provide option to work without workflow
4. **Clarity option**: Allow user to clarify requirements

## When NOT to Activate

- User explicitly said "don't use workflow"
- Task is trivial (< 5 lines of code)
- Higher-priority skill already matched
- User is asking questions, not requesting work

## Example Activation

**User**: "Implement JWT authentication for the API"

**This Skill**:
```
I detected a MODERATE work request: "Implement JWT authentication for the API"

Would you like me to use /ultrathink to orchestrate this work?
- Estimated scope: 6-8 files, 8 steps
- Workflow: default-workflow (13 steps)
- Time estimate: 45-60 minutes

[Yes] [No] [Custom]
```

## Experimental Status

**Purpose**: Test viability of ultrathink as default orchestrator
**Risks**:
- May activate too aggressively
- Confirmation prompts may annoy users
- Complexity estimation may be inaccurate

**Success Criteria**:
- 80%+ user acceptance rate
- Accurate complexity estimates
- No false positives on non-work requests

**Feedback Welcome**: This is an experiment. User feedback determines if it becomes standard.
