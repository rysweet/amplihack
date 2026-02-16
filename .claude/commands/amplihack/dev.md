---
name: amplihack:dev
version: 1.0.0
description: Alias for /amplihack:default-workflow - Run the full 23-step development workflow
aliases_for: amplihack:default-workflow
triggers:
  - "dev workflow"
  - "start development"
invokes:
  - type: recipe
    name: default-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/default-workflow.yaml
examples:
  - "/amplihack:dev Add user authentication"
  - "/amplihack:dev Fix login timeout bug"
---

# Dev Command (Alias)

## Usage

`/amplihack:dev <TASK_DESCRIPTION>`

This is an alias for `/amplihack:default-workflow`. See that command for full documentation.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, execute exactly as `/amplihack:default-workflow`:

1. **Attempt Recipe Runner execution** (preferred):

   ```python
   from amplihack.recipes import run_recipe_by_name
   result = run_recipe_by_name(
       "default-workflow",
       adapter=sdk_adapter,
       user_context={
           "task_description": "{TASK_DESCRIPTION}",
           "repo_path": "."
       }
   )
   ```

2. **Fallback to Skill** (if Recipe Runner unavailable):

   ```
   Skill(skill="default-workflow")
   ```

3. **Final fallback to Markdown** (if skill unavailable):

   ```
   Read(file_path="~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md")
   ```

4. **Create TodoWrite entries** for all 23 steps and execute systematically.

## Task Description

```
{TASK_DESCRIPTION}
```
