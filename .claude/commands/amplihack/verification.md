---
name: amplihack:verification
version: 1.0.0
description: Run the 5-step verification workflow for trivial changes
triggers:
  - "trivial change"
  - "config update"
  - "doc update"
  - "simple fix"
invokes:
  - type: recipe
    name: verification-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/verification-workflow.yaml
examples:
  - "/amplihack:verification Update config.yaml timeout value"
  - "/amplihack:verification Fix typo in README"
---

# Verification Workflow Command

## Usage

`/amplihack:verification <CHANGE_DESCRIPTION>`

## Purpose

Directly invoke the 5-step verification workflow recipe. Use for trivial changes: config edits, documentation updates, presentational changes, and simple fixes under 10 lines.

If the change is more complex, escalate to `/amplihack:default-workflow` or `/amplihack:dev`.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Attempt Recipe Runner execution** (preferred):

   ```python
   from amplihack.recipes import run_recipe_by_name
   result = run_recipe_by_name(
       "verification-workflow",
       adapter=sdk_adapter,
       user_context={
           "change_description": "{CHANGE_DESCRIPTION}",
           "repo_path": "."
       }
   )
   ```

2. **Fallback to manual execution**:
   - Make the change
   - Verify it builds/passes
   - Commit and push
   - Create PR
   - Verify CI

## Steps

1. Make Change - Edit file(s) and verify syntax
2. Verify - Run tests and checks
3. Commit - Stage and commit changes
4. PR - Create pull request
5. CI - Verify CI passes

## Change Description

```
{CHANGE_DESCRIPTION}
```
