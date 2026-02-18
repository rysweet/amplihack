---
name: amplihack:run
version: 1.0.0
description: Alias for /amplihack:hybrid - Investigation then development workflow
aliases_for: amplihack:hybrid
triggers:
  - "run workflow"
  - "investigate and build"
invokes:
  - type: recipe
    name: investigation-workflow
  - type: recipe
    name: default-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/investigation-workflow.yaml
    - amplifier-bundle/recipes/default-workflow.yaml
examples:
  - "/amplihack:run Understand the auth system then add OAuth support"
  - "/amplihack:run Add rate limiting to the API"
---

# Run Command (Alias)

## Usage

`/amplihack:run <TASK_DESCRIPTION>`

This is an alias for `/amplihack:hybrid`. See that command for full documentation.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, execute exactly as `/amplihack:hybrid`:

### Phase 1: Investigation

```python
from amplihack.recipes import run_recipe_by_name

investigation_result = run_recipe_by_name(
    "investigation-workflow",
    adapter=sdk_adapter,
    user_context={
        "investigation_question": "[investigation aspect of TASK_DESCRIPTION]",
        "codebase_path": ".",
        "investigation_type": "code",
        "depth": "deep"
    }
)
```

### Phase 2: Development (with investigation context)

```python
dev_result = run_recipe_by_name(
    "default-workflow",
    adapter=sdk_adapter,
    user_context={
        "task_description": "[development aspect of TASK_DESCRIPTION]",
        "repo_path": ".",
        "investigation_findings": investigation_result.context
    }
)
```

Fallback: Use workflow skills or markdown workflows if Recipe Runner unavailable.

## Task Description

```
{TASK_DESCRIPTION}
```
