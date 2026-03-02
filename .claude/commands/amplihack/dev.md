---
name: dev
version: 3.0.0
description: |
  Primary entry point for all development and investigation work.
  Thin alias to the dev-orchestrator skill, which classifies tasks,
  decomposes into workstreams, and executes via recipe runner.
triggers:
  - "implement"
  - "build"
  - "create"
  - "fix"
  - "refactor"
  - "investigate"
  - "develop"
  - "make"
  - "add feature"
invokes:
  - type: skill
    name: dev-orchestrator
dependencies:
  required:
    - amplifier-bundle/recipes/smart-orchestrator.yaml
examples:
  - "/dev add user authentication"
  - "/dev build a webui and an API for user management"
  - "/dev fix the login timeout bug"
  - "/dev investigate how the caching layer works"
  - "/dev implement OAuth and add structured logging"
---

## EXECUTION INSTRUCTIONS (DO THIS IMMEDIATELY)

This command is a thin alias to the `dev-orchestrator` skill.

**YOUR VERY FIRST ACTION** must be to invoke the skill:

```
Skill(skill="dev-orchestrator")
```

Pass the task description below as context when invoking the skill.

Do NOT classify, read files, create task lists, or run the recipe runner
directly. The dev-orchestrator skill handles all of that.

## Task Description

```
{TASK_DESCRIPTION}
```
