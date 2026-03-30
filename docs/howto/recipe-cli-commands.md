---
title: "Recipe CLI commands"
description: "Task-oriented guide to listing, validating, showing, and running recipe files with the current path-based CLI and repeated key=value context arguments."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: howto
---

# Recipe CLI commands

Use this guide when you need to inspect or execute recipe files from the command line.

## Prerequisites

- `python -m amplihack` or an installed `amplihack` command available
- `PYTHONPATH=src` when running from a source checkout
- the YAML file path for the recipe you want to inspect or run

## List available recipes

```bash
python -m amplihack recipe list
python -m amplihack recipe list -f json
python -m amplihack recipe list -t workflow
```

Use `list` to discover names and descriptions. `list` is discovery-oriented and can search all known recipe roots or a specific directory.

## Validate a recipe file

```bash
python -m amplihack recipe validate amplifier-bundle/recipes/smart-orchestrator.yaml
```

Use `validate` before a long run or when you are editing YAML.

## Show the details of a recipe file

```bash
python -m amplihack recipe show amplifier-bundle/recipes/smart-orchestrator.yaml --no-context
```

Use `show` when you need the step list and metadata for a concrete file.

## Run a recipe file

Pass context with repeated `-c` or `--context` assignments.

```bash
python -m amplihack recipe run amplifier-bundle/recipes/default-workflow.yaml \
  -c task_description="Add JWT authentication" \
  -c repo_path="." \
  -c branch_name="feat/jwt-auth" \
  --dry-run
```

### Values with spaces

`-c` accepts shell-quoted values with spaces and punctuation.

```bash
python -m amplihack recipe run amplifier-bundle/recipes/investigation-workflow.yaml \
  -c task_description="Explain how the auth pipeline handles refresh tokens" \
  -c repo_path="."
```

## Use the Python API when you want name resolution

The CLI is path-based for `run`, `show`, and `validate`.

Use the Python API when you want to execute a bundled recipe by name:

```bash
python - <<'PY'
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "smart-orchestrator",
    user_context={
        "task_description": "Validate merged workflow reliability",
        "repo_path": ".",
        "force_single_workstream": "true",
    },
    dry_run=True,
)
print(result)
PY
```

## Troubleshooting

### `run`, `show`, or `validate` cannot find the recipe

Pass a concrete YAML path such as `amplifier-bundle/recipes/smart-orchestrator.yaml`.

### You need the bundled recipe name that will actually execute

Use `find_recipe()` from the Python API.

### Your task description is long

Keep using `-c task_description="..."` on the CLI or pass `user_context` through the Python API. Large values may spill internally, but that transport detail is handled by the runner.

## See Also

- [Recipe Runner](../recipes/README.md)
- [Recipe CLI Reference](../reference/recipe-cli-reference.md)
- [How to Validate Recipe-Runner Reliability](./validate-recipe-runner-reliability.md)
