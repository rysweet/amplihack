---
name: amplihack:hybrid
version: 1.0.0
description: Hybrid workflow - investigation first, then development
aliases: [amplihack:run]
triggers:
  - "investigate then implement"
  - "understand then build"
  - "research then develop"
  - "hybrid workflow"
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
  - "/amplihack:hybrid Understand the auth system then add OAuth support"
  - "/amplihack:run Investigate rate limiting, then implement it"
---

# Hybrid Workflow Command

## Usage

`/amplihack:hybrid <TASK_DESCRIPTION>`
`/amplihack:run <TASK_DESCRIPTION>`

## Purpose

Execute a two-phase hybrid workflow: investigate first, then develop. The investigation phase builds understanding that feeds directly into the development phase, producing better-informed implementations.

This is the recommended approach when working in unfamiliar code areas or when the task requires understanding existing systems before making changes.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST execute two phases sequentially:

### Phase 1: Investigation

1. **Extract the investigation aspect** from the task description.
   Parse the task to identify what needs to be understood before building.

2. **Attempt Recipe Runner execution** (preferred):

   ```python
   from amplihack.recipes import run_recipe_by_name

   # Phase 1: Investigation
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

3. **Fallback to Skill** (if Recipe Runner unavailable):
   ```
   Skill(skill="investigation-workflow")
   ```

### Phase 2: Development (with investigation context)

4. **Extract the development aspect** from the task description.

5. **Execute development workflow with investigation findings**:

   ```python
   # Phase 2: Development with investigation context
   dev_result = run_recipe_by_name(
       "default-workflow",
       adapter=sdk_adapter,
       user_context={
           "task_description": "[development aspect of TASK_DESCRIPTION]",
           "repo_path": ".",
           "investigation_findings": investigation_result.context,
           "architecture_insights": investigation_result.context.get("insights", {})
       }
   )
   ```

6. **Fallback to Skill** (if Recipe Runner unavailable):
   ```
   Skill(skill="default-workflow")
   ```

### Parsing the Task

The task description typically follows one of these patterns:

- "Investigate X, then implement Y"
- "Understand X and add Y"
- "Research X, then build Y"
- Single task that implicitly needs both (e.g., "Add OAuth to auth system" implies investigating auth first)

If no explicit investigation/development split, use the full task as both:

- Investigation: "How does [relevant system] work?"
- Development: The full task description

### Context Flow

Investigation findings flow into development:

- Architecture insights inform design decisions (Step 5)
- Code patterns discovered guide implementation style (Step 8)
- Identified risks shape testing strategy (Step 7)
- Integration points inform module boundaries (Step 9)

## Cost-Benefit

- **Cost:** ~1.5x execution time vs development alone
- **Benefit:** Better-informed implementation, fewer rework cycles
- **ROI Positive when:** Working in unfamiliar code or complex systems

## Task Description

```
{TASK_DESCRIPTION}
```
