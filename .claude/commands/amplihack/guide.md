---
name: amplihack:guide
version: 1.0.0
description: Interactive guide to amplihack features and workflows
triggers:
  - "help with amplihack"
  - "how to use amplihack"
  - "amplihack guide"
  - "onboarding"
invokes:
  - type: recipe
    name: guide
dependencies:
  required:
    - amplifier-bundle/recipes/guide.yaml
examples:
  - "/amplihack:guide How do workflows work?"
  - "/amplihack:guide What agents are available?"
---

# Amplihack Guide Command

## Usage

`/amplihack:guide <TOPIC>`

## Purpose

Interactive guide to amplihack features. Ask about workflows, agents, skills, hooks, recipes, or any amplihack concept and get a friendly, knowledgeable explanation.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Attempt Recipe Runner execution** (preferred):

   ```python
   from amplihack.recipes import run_recipe_by_name
   result = run_recipe_by_name(
       "guide",
       adapter=sdk_adapter,
       user_context={
           "topic": "{TOPIC}",
           "detail_level": "standard"
       }
   )
   ```

2. **Fallback to direct response**:
   - Use knowledge of amplihack to answer the question
   - Reference relevant files and documentation
   - Point to commands, skills, and agents as appropriate

## Topics

- **Workflows**: How the 9 workflow recipes work
- **Agents**: What agents are available and when to use them
- **Skills**: How skills auto-activate and extend capabilities
- **Commands**: Slash commands and their purposes
- **Recipes**: Recipe Runner and YAML recipe format
- **Philosophy**: Ruthless simplicity, bricks & studs, zero-BS

## Topic

```
{TOPIC}
```
