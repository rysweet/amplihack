---
name: amplihack:qa
version: 1.0.0
description: Run the minimal Q&A workflow for simple questions
triggers:
  - "quick question"
  - "simple question"
  - "what is"
invokes:
  - type: recipe
    name: qa-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/qa-workflow.yaml
examples:
  - "/amplihack:qa What does the cleanup agent do?"
  - "/amplihack:qa How do I run tests?"
---

# Q&A Workflow Command

## Usage

`/amplihack:qa <QUESTION>`

## Purpose

Directly invoke the minimal 3-step Q&A workflow recipe. Use for simple questions that can be answered in a single turn without code changes or deep exploration.

If the question turns out to be complex, the workflow will auto-escalate to investigation-workflow.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Attempt Recipe Runner execution** (preferred):

   ```python
   from amplihack.recipes import run_recipe_by_name
   result = run_recipe_by_name(
       "qa-workflow",
       adapter=sdk_adapter,
       user_context={
           "question": "{QUESTION}",
           "context_info": ""
       }
   )
   ```

2. **Fallback to Skill** (if Recipe Runner unavailable):
   - Read `~/.amplihack/.claude/workflow/Q&A_WORKFLOW.md` directly

3. **Answer concisely** - Q&A workflow is intentionally minimal.

## Question

```
{QUESTION}
```
