---
name: amplihack:investigation
version: 1.0.0
description: Run the 6-phase investigation workflow via Recipe Runner
triggers:
  - "investigate code"
  - "understand system"
  - "deep analysis"
  - "explore codebase"
invokes:
  - type: recipe
    name: investigation-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/investigation-workflow.yaml
examples:
  - "/amplihack:investigation How does the authentication system work?"
  - "/amplihack:investigation Analyze the recipe runner architecture"
---

# Investigation Workflow Command

## Usage

`/amplihack:investigation <INVESTIGATION_QUESTION>`

## Purpose

Directly invoke the 6-phase investigation workflow recipe. Use for understanding existing code, systems, and architecture without making changes.

Unlike `/ultrathink` which auto-detects the workflow type, this command always runs `investigation-workflow` without classification overhead.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Attempt Recipe Runner execution** (preferred):

   ```python
   from amplihack.recipes import run_recipe_by_name
   result = run_recipe_by_name(
       "investigation-workflow",
       adapter=sdk_adapter,
       user_context={
           "investigation_question": "{INVESTIGATION_QUESTION}",
           "codebase_path": ".",
           "investigation_type": "code",
           "depth": "deep"
       }
   )
   ```

2. **Fallback to Skill** (if Recipe Runner unavailable):

   ```
   Skill(skill="investigation-workflow")
   ```

3. **Final fallback to Markdown** (if skill unavailable):

   ```
   Read(file_path="~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md")
   ```

4. **Create TodoWrite entries** for all 6 phases and execute systematically.

## Phases

1. Scope Definition - Define boundaries and success criteria
2. Exploration Strategy - Plan agent deployment
3. Parallel Deep Dives - Deploy multiple agents simultaneously
4. Verification - Hypothesis-based testing
5. Synthesis - Generate comprehensive findings
6. Knowledge Capture - Update DISCOVERIES.md and PATTERNS.md

## Investigation Question

```
{INVESTIGATION_QUESTION}
```
