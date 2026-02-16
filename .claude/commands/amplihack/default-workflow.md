---
name: amplihack:default-workflow
version: 1.0.0
description: Run the full 23-step development workflow via Recipe Runner
aliases: [amplihack:dev]
triggers:
  - "full development workflow"
  - "complete workflow"
  - "23-step workflow"
invokes:
  - type: recipe
    name: default-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/default-workflow.yaml
examples:
  - "/amplihack:default-workflow Add JWT authentication to REST API"
  - "/amplihack:dev Fix null pointer in UserService"
---

# Default Workflow Command

## Usage

`/amplihack:default-workflow <TASK_DESCRIPTION>`
`/amplihack:dev <TASK_DESCRIPTION>`

## Purpose

Directly invoke the full 23-step development workflow recipe. This is the standard workflow for features, bug fixes, and refactoring.

Unlike `/ultrathink` which auto-detects the workflow type, this command always runs `default-workflow` without classification overhead.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

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

## Phases

1. Requirements Clarification (Steps 0-3)
2. Design (Steps 4-6)
3. Implementation (Steps 7-9)
4. Testing & Review (Steps 10-13)
5. Version & PR (Steps 14-16)
6. PR Review (Steps 17-18)
7. Merge (Steps 19-22)

## Task Description

```
{TASK_DESCRIPTION}
```
