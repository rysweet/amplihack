# Ultrathink Orchestrator Skill

**Version**: 1.0.0
**Priority**: 5 (LOW)

## Overview

Automatic workflow orchestration skill that invokes ultrathink for development work requests. Intelligently selects between investigation and development workflows based on task keywords.

## Purpose

Provide default orchestration for non-trivial development tasks by automatically triggering the appropriate workflow (investigation or development) when no more specific skill matches.

## How It Works

1. Auto-activates on work request patterns (implement, create, fix, investigate, etc.)
2. Detects task type: investigation, development, or hybrid
3. Estimates task complexity (simple/moderate/complex)
4. Asks user for confirmation before proceeding
5. Invokes the appropriate workflow skill:
   - **Investigation**: `investigation-workflow` skill
   - **Development**: `default-workflow` skill
   - **Hybrid**: Both workflows sequentially

## Task Type Detection

**Investigation Tasks**:

- Keywords: investigate, explain, understand, how does, why does, analyze, research, explore, examine, study
- Examples: "Investigate authentication", "Explain routing", "Understand database schema"

**Development Tasks**:

- Keywords: implement, build, create, add feature, fix, refactor, deploy
- Examples: "Implement JWT auth", "Add user registration", "Fix login bug"

**Hybrid Tasks**:

- Contains both investigation and development keywords
- Examples: "Investigate auth system, then add OAuth support"

## Safety Features

- **Always confirms**: Never auto-executes without user approval
- **Low priority**: Other specialized skills take precedence (priority 5)
- **Escape hatch**: Users can decline workflow orchestration
- **Clarity option**: Users can request clarification first
- **Task type awareness**: Automatically routes to appropriate workflow

## Example Interactions

### Development Task

**User**: "Add user authentication to the API"

**Skill Response**:

```
I detected a MODERATE development request: "Add user authentication to the API"

Would you like me to use /ultrathink to orchestrate this work?
- Workflow: default-workflow
- Estimated scope: 6-8 files
- Time estimate: 45-60 minutes

[Yes] [No] [Custom]
```

### Investigation Task

**User**: "Investigate how the reflection system works"

**Skill Response**:

```
I detected a MODERATE investigation request: "Investigate how the reflection system works"

Would you like me to use /ultrathink to orchestrate this work?
- Workflow: investigation-workflow
- Estimated scope: 10-15 files, deep analysis
- Time estimate: 30-40 minutes

[Yes] [No] [Custom]
```

### Hybrid Task

**User**: "Investigate auth system, then add OAuth support"

**Skill Response**:

```
I detected a COMPLEX hybrid request: "Investigate auth system, then add OAuth support"

Would you like me to use /ultrathink to orchestrate this work?
- Workflow: investigation-workflow → default-workflow
- Estimated scope: 15+ files, comprehensive work
- Time estimate: 90-120 minutes

[Yes] [No] [Custom]
```

## Workflow Integration

**Preferred Approach** (workflow skills):

- Uses `Skill(skill="default-workflow")` for development tasks
- Uses `Skill(skill="investigation-workflow")` for investigation tasks
- Automatic task type detection from keywords

**Fallback** (if skills not available):

- Reads `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md`
- Reads `~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md`
- Provides same functionality via markdown workflows

## Benefits

- **Consistent workflow execution**: All non-trivial work follows established patterns
- **Reduced cognitive load**: Automatic workflow selection based on task type
- **User control**: Always asks for confirmation before proceeding
- **Intelligent routing**: Chooses appropriate workflow (investigation vs development)
- **Quality assurance**: Ensures all work goes through proper review and validation

## Related

- Default Workflow Skill: `~/.amplihack/.claude/skills/default-workflow/`
- Investigation Workflow Skill: `~/.amplihack/.claude/skills/investigation-workflow/`
- Ultrathink Command: `~/.amplihack/.claude/commands/amplihack/ultrathink.md`
- Workflow Files: `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md`, `~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md`
