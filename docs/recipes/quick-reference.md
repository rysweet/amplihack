---
title: "Recipe CLI quick reference"
description: "One-page command summary for the current recipe CLI, including path-based run/show/validate commands and key=value context assignments."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: reference
---

# Recipe CLI quick reference

## Core commands

```bash
# List discovered recipes
python -m amplihack recipe list
python -m amplihack recipe list amplifier-bundle/recipes -f json

# Validate a recipe file
python -m amplihack recipe validate amplifier-bundle/recipes/smart-orchestrator.yaml

# Show a recipe file
python -m amplihack recipe show amplifier-bundle/recipes/smart-orchestrator.yaml --no-context

# Run a recipe file
python -m amplihack recipe run amplifier-bundle/recipes/default-workflow.yaml \
  -c task_description="Add auth" \
  -c repo_path="." \
  --dry-run
```

## Context arguments

```bash
-c task_description="Add auth"
-c repo_path="."
-c branch_name="feat/add-auth"
```

Rules:

- repeat `-c` or `--context` for each value
- each assignment must be `KEY=VALUE`
- quote values that contain spaces

## Use the Python API for bundled recipe names

```bash
python - <<'PY'
from amplihack.recipes import find_recipe, run_recipe_by_name
print(find_recipe("smart-orchestrator"))
print(run_recipe_by_name("smart-orchestrator", user_context={"task_description": "Describe docs", "repo_path": "."}, dry_run=True))
PY
```

## Common bundled recipe files

| Purpose | File |
| --- | --- |
| smart orchestration | `amplifier-bundle/recipes/smart-orchestrator.yaml` |
| full development workflow | `amplifier-bundle/recipes/default-workflow.yaml` |
| investigation workflow | `amplifier-bundle/recipes/investigation-workflow.yaml` |

## Exit behavior

| Command | Success | Failure |
| --- | --- | --- |
| `list` | `0` | `1` |
| `validate` | `0` | `1` |
| `show` | `0` | `1` |
| `run` | `0` on successful recipe result | `1` on validation or execution failure |
