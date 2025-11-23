---
name: ultrathink-orchestrator
version: 1.0.0
description: Auto-invokes ultrathink workflow for any work request (default orchestrator)
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
---

# Ultrathink Orchestrator Skill

## Purpose

Automatically trigger ultrathink workflow orchestration for development tasks that don't match more specific skills. Invokes workflow skills (default-workflow or investigation-workflow) based on task type.

## Auto-Activation

**Priority**: 5 (LOW - other skills checked first)
**Triggers**: Common work request patterns (implement, create, build, add, fix, etc.)

## Behavior

When activated:

1. **Detect Task Type**: Identify if task is investigation or development
   - **Investigation keywords**: investigate, explain, understand, how does, why does, analyze, research, explore, examine, study
   - **Development keywords**: implement, build, create, add feature, fix, refactor, deploy
2. **Select Appropriate Workflow**:
   - Investigation: `investigation-workflow` skill (6 phases)
   - Development: `default-workflow` skill (15 steps)
   - Hybrid: Both workflows sequentially
3. **Estimate Complexity**: Analyze task complexity (simple/moderate/complex)
4. **Confirm with User**: Ask for confirmation before proceeding
5. **Invoke Workflow Skill**: Execute the selected workflow skill
   - **Fallback**: If skill not found, read markdown workflow file

## Task Type Detection

**Investigation Tasks**:
- Contain keywords: investigate, explain, understand, how does, why does, analyze, research, explore, examine, study
- Examples: "Investigate authentication", "Explain how routing works", "Understand the database schema"

**Development Tasks**:
- Contain keywords: implement, build, create, add feature, fix, refactor, deploy
- Examples: "Implement JWT auth", "Add user registration", "Fix login bug"

**Hybrid Tasks**:
- Contain both investigation and development keywords
- Examples: "Investigate auth system, then add OAuth support"
- Runs investigation workflow first, then development workflow

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
I detected a [COMPLEXITY] [TASK_TYPE] request: "[USER REQUEST]"

Would you like me to use /ultrathink to orchestrate this work?
- Workflow: [workflow-name] ([N] steps/phases)
- Estimated scope: [X] files, [Y] steps
- Time estimate: [Z] minutes

[Yes] - Proceed with ultrathink orchestration
[No] - I'll work on this directly without workflow
[Custom] - Let me clarify the requirements first
```

## Implementation

When confirmed, invoke the appropriate workflow skill:

### Development Tasks
```
Invoke the `default-workflow` skill to execute this task following
the 15-step development workflow in DEFAULT_WORKFLOW.md.
```

### Investigation Tasks
```
Invoke the `investigation-workflow` skill to execute this task following
the 6-phase investigation workflow in INVESTIGATION_WORKFLOW.md.
```

### Hybrid Tasks
```
1. First invoke `investigation-workflow` skill (6 phases)
2. Then invoke `default-workflow` skill (15 steps), using investigation insights
```

## Workflow Integration

**Workflow Skills** (preferred):
- Uses `Skill(skill="default-workflow")` for development
- Uses `Skill(skill="investigation-workflow")` for investigation
- Auto-detects task type from keywords

**Fallback** (if skills not available):
- Reads `.claude/workflow/DEFAULT_WORKFLOW.md`
- Reads `.claude/workflow/INVESTIGATION_WORKFLOW.md`
- Provides same functionality via markdown workflows

## Safeguards

1. **Always confirm**: Never auto-execute without user approval
2. **Task type awareness**: Automatically select appropriate workflow
3. **Complexity awareness**: Show estimated scope before proceeding
4. **Escape hatch**: Provide option to work without workflow
5. **Clarity option**: Allow user to clarify requirements

## When NOT to Activate

- User explicitly said "don't use workflow"
- Task is trivial (< 5 lines of code)
- Higher-priority skill already matched
- User is asking questions, not requesting work

## Example Activations

### Development Task Example

**User**: "Implement JWT authentication for the API"

**This Skill**:
```
I detected a MODERATE development request: "Implement JWT authentication for the API"

Would you like me to use /ultrathink to orchestrate this work?
- Workflow: default-workflow (15 steps)
- Estimated scope: 6-8 files, 8 steps
- Time estimate: 45-60 minutes

[Yes] [No] [Custom]
```

### Investigation Task Example

**User**: "Investigate how the reflection system works"

**This Skill**:
```
I detected a MODERATE investigation request: "Investigate how the reflection system works"

Would you like me to use /ultrathink to orchestrate this work?
- Workflow: investigation-workflow (6 phases)
- Estimated scope: 10-15 files, deep analysis
- Time estimate: 30-40 minutes

[Yes] [No] [Custom]
```

### Hybrid Task Example

**User**: "Investigate auth system, then add OAuth support"

**This Skill**:
```
I detected a COMPLEX hybrid request: "Investigate auth system, then add OAuth support"

Would you like me to use /ultrathink to orchestrate this work?
- Workflow: investigation-workflow (6 phases) → default-workflow (15 steps)
- Estimated scope: 15+ files, comprehensive work
- Time estimate: 90-120 minutes

[Yes] [No] [Custom]
```

## Related

- Default Workflow: `.claude/skills/default-workflow/`
- Investigation Workflow: `.claude/skills/investigation-workflow/`
- Ultrathink Command: `.claude/commands/amplihack/ultrathink.md`
- Workflow Files: `.claude/workflow/DEFAULT_WORKFLOW.md`, `.claude/workflow/INVESTIGATION_WORKFLOW.md`
