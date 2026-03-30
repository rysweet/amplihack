---
title: "Recipe CLI reference"
description: "Complete reference for the current path-based `amplihack recipe` CLI: list, validate, show, run, output formats, context parsing, and exit behavior."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: reference
---

# Recipe CLI reference

## Overview

The `amplihack recipe` subcommand group exposes four commands:

- `list`
- `validate`
- `show`
- `run`

`list` works on discovered recipe definitions.

`validate`, `show`, and `run` operate on a **recipe file path**.

## Command summary

| Command | Purpose |
| --- | --- |
| `amplihack recipe list [recipe_dir]` | discover recipes from the default search path or a specific directory |
| `amplihack recipe validate <recipe_path>` | validate a recipe YAML file |
| `amplihack recipe show <recipe_path>` | print recipe metadata and steps |
| `amplihack recipe run <recipe_path>` | execute a recipe file |

## Output formats

These commands accept `-f` or `--format` with one of:

- `table`
- `json`
- `yaml`

## `amplihack recipe list`

### Synopsis

```bash
python -m amplihack recipe list [recipe_dir] [-f table|json|yaml] [-t TAG] [-v]
```

### Arguments

| Argument | Meaning |
| --- | --- |
| `recipe_dir` | optional directory to search instead of the default discovery path |

### Options

| Option | Meaning |
| --- | --- |
| `-f`, `--format` | output format |
| `-t`, `--tags` | filter by tag; repeat to require multiple tags |
| `-v`, `--verbose` | show additional details |

### Example

```bash
python -m amplihack recipe list
python -m amplihack recipe list amplifier-bundle/recipes -f json
```

## `amplihack recipe validate`

### Synopsis

```bash
python -m amplihack recipe validate <recipe_path> [-f table|json|yaml] [-v]
```

### Arguments

| Argument | Meaning |
| --- | --- |
| `recipe_path` | path to the YAML file to validate |

### Options

| Option | Meaning |
| --- | --- |
| `-f`, `--format` | output format |
| `-v`, `--verbose` | show detailed validation information |

### Example

```bash
python -m amplihack recipe validate amplifier-bundle/recipes/smart-orchestrator.yaml
```

## `amplihack recipe show`

### Synopsis

```bash
python -m amplihack recipe show <recipe_path> [-f table|json|yaml] [--no-steps] [--no-context]
```

### Arguments

| Argument | Meaning |
| --- | --- |
| `recipe_path` | path to the YAML file to inspect |

### Options

| Option | Meaning |
| --- | --- |
| `-f`, `--format` | output format |
| `--no-steps` | hide step details |
| `--no-context` | hide context defaults |

### Example

```bash
python -m amplihack recipe show amplifier-bundle/recipes/smart-orchestrator.yaml --no-context
```

## `amplihack recipe run`

### Synopsis

```bash
python -m amplihack recipe run <recipe_path> [-c KEY=VALUE ...] [--dry-run] [-f table|json|yaml] [-v] [-w DIR]
```

### Arguments

| Argument | Meaning |
| --- | --- |
| `recipe_path` | path to the YAML file to execute |

### Options

| Option | Meaning |
| --- | --- |
| `-c`, `--context KEY=VALUE` | add or override a runtime context variable; repeat as needed |
| `--dry-run` | show the recipe result shape without executing real work |
| `-f`, `--format` | output format |
| `-v`, `--verbose` | print execution preamble and extra details |
| `-w`, `--working-dir` | working directory for recipe execution |

### Context parsing

The CLI accepts repeated `KEY=VALUE` assignments.

Values may contain spaces when shell-quoted.

```bash
python -m amplihack recipe run amplifier-bundle/recipes/investigation-workflow.yaml \
  -c task_description="Explain how the auth pipeline handles refresh tokens" \
  -c repo_path="." \
  --dry-run
```

If a `-c` token does not contain `=`, the CLI reports an error.

## Environment inference

When a recipe defines default context keys and a value is still empty after CLI merging, the CLI can infer values from environment variables.

| Key | Environment fallback |
| --- | --- |
| `task_description` | `AMPLIHACK_TASK_DESCRIPTION` or `AMPLIHACK_CONTEXT_TASK_DESCRIPTION` |
| `repo_path` | `AMPLIHACK_REPO_PATH` or `AMPLIHACK_CONTEXT_REPO_PATH` |
| any other key `foo` | `AMPLIHACK_CONTEXT_FOO` |

## CLI vs Python API

Use the CLI when you already know the YAML file path.

Use the Python API when you want name-based resolution through `find_recipe()` and `run_recipe_by_name()`.

```python
from amplihack.recipes import find_recipe, run_recipe_by_name

print(find_recipe("smart-orchestrator"))
result = run_recipe_by_name("smart-orchestrator", user_context={"task_description": "Describe docs", "repo_path": "."}, dry_run=True)
print(result)
```

## Exit behavior

| Command | Success | Failure | Interrupt |
| --- | --- | --- | --- |
| `list` | `0` | `1` | n/a |
| `validate` | `0` | `1` | n/a |
| `show` | `0` | `1` | n/a |
| `run` | `0` when `result.success` is true | `1` on validation or execution failure | `130` on `KeyboardInterrupt` |

## Notes

- `run`, `show`, and `validate` do not auto-resolve bundled recipe names.
- `list` reports discovered definitions, but name collisions should be confirmed with `find_recipe()` when exact precedence matters.
- reliability validation of bundled workflows is documented separately in [Recipe-Runner Reliability Reference](./recipe-runner-reliability.md).
