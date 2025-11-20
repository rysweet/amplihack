# Ultrathink Orchestrator Skill

**Status**: EXPERIMENTAL
**Version**: 1.0.0
**Priority**: 5 (LOW)

## Overview

Experimental skill that automatically invokes ultrathink workflow orchestration for development work requests.

## Purpose

Test the hypothesis: "Ultrathink workflow should be the default for all non-trivial development tasks."

## How It Works

1. Auto-activates on work request patterns (implement, create, fix, etc.)
2. Estimates task complexity (simple/moderate/complex)
3. Asks user for confirmation before proceeding
4. Invokes default-workflow skill if confirmed

## Safety Features

- **Always confirms**: Never auto-executes without user approval
- **Low priority**: Other specialized skills take precedence
- **Escape hatch**: Users can decline workflow orchestration
- **Clarity option**: Users can request clarification first

## Example

**User**: "Add user authentication to the API"

**Skill Response**:
```
I detected a MODERATE work request: "Add user authentication to the API"

Would you like me to use /ultrathink to orchestrate this work?
- Estimated scope: 6-8 files, 8 steps
- Workflow: default-workflow (13 steps)
- Time estimate: 45-60 minutes

[Yes] [No] [Custom]
```

## Experimental Evaluation

This skill will be evaluated based on:
- User acceptance rate (target: 80%+)
- Complexity estimation accuracy
- False positive rate on non-work requests
- User feedback

## Feedback

This is an experiment. Your feedback determines whether this becomes a standard feature or gets removed.

Report feedback via GitHub issues with label: `experiment/ultrathink-as-default`

## Related

- Default Workflow: `.claude/skills/default-workflow/`
- Ultrathink Command: `.claude/commands/amplihack/ultrathink.md`
- Migration Plan: `Specs/ATOMIC_DELIVERY_PLAN.md` (PR #6)
