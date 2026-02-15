---
name: amplihack:recipe
version: 1.0.0
description: Execute a deterministic YAML recipe workflow with code-enforced step ordering
triggers:
  - "run recipe"
  - "execute recipe"
  - "recipe workflow"
  - "deterministic workflow"
invokes:
  - type: module
    path: src/amplihack/recipes
philosophy:
  - principle: Ruthless Simplicity
    application: Code controls step ordering, not prompt instructions
  - principle: Zero-BS Implementation
    application: Every step must execute or fail - no skipping
dependencies:
  required:
    - src/amplihack/recipes
  optional:
    - amplifier-bundle/recipes
examples:
  - '/amplihack:recipe run default-workflow --context ''{"task_description": "Add auth"}'''
  - "/amplihack:recipe list"
  - "/amplihack:recipe run verification-workflow --dry-run"
  - "/amplihack:recipe validate my-recipe.yaml"
---

# Recipe Runner Command

Execute deterministic YAML recipe workflows with code-enforced step ordering.

## Usage

```
/amplihack:recipe <subcommand> [options]
```

## Subcommands

### run

Execute a recipe with code-enforced step ordering.

```
/amplihack:recipe run <recipe-name> [--context '{"key": "value"}'] [--dry-run] [--adapter auto|claude-sdk|cli]
```

**Arguments:**

- `recipe-name`: Name of recipe file (without .yaml) or path to YAML file
- `--context`: JSON object with context variables
- `--dry-run`: Show steps without executing
- `--adapter`: SDK adapter to use (default: auto-detect)

### list

List all available recipes.

```
/amplihack:recipe list
```

### validate

Validate a recipe YAML file.

```
/amplihack:recipe validate <recipe-path>
```

### show

Show recipe details (steps, context variables, metadata).

```
/amplihack:recipe show <recipe-name>
```

## How It Works

The Recipe Runner reads a YAML recipe file and executes each step sequentially using Python code. Unlike prompt-based workflow instructions, the model cannot skip steps because Python controls the execution loop.

```python
for step in recipe.steps:
    result = adapter.execute(step)  # Code-enforced - cannot skip
```

## Available Recipes

| Recipe                 | Steps | Description                                             |
| ---------------------- | ----- | ------------------------------------------------------- |
| default-workflow       | 52    | Full development lifecycle (requirements through merge) |
| verification-workflow  | 5     | Quick validation for trivial changes                    |
| investigation-workflow | 23    | Deep codebase analysis                                  |
| qa-workflow            | 4     | Simple Q&A workflow                                     |
| debate-workflow        | 17    | Multi-perspective decision making                       |
| consensus-workflow     | 59    | Critical code with multi-agent consensus                |
| n-version-workflow     | 23    | N independent implementations compared                  |
| cascade-workflow       | 10    | Graceful degradation with fallbacks                     |
| auto-workflow          | 9     | Autonomous multi-turn execution                         |
| guide                  | 1     | Interactive amplihack guide                             |

## Examples

```bash
# Run the default development workflow
/amplihack:recipe run default-workflow --context '{"task_description": "Add user auth", "repo_path": "."}'

# Dry run to preview steps
/amplihack:recipe run default-workflow --dry-run

# Quick validation workflow
/amplihack:recipe run verification-workflow --context '{"change_description": "Update config", "repo_path": "."}'

# List all recipes
/amplihack:recipe list
```
