---
title: "Recipe Runner"
description: "Overview of the Rust-backed recipe runner, its entrypoints, current CLI behavior, and the target-state reliability docs for merged-worktree orchestration."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: reference
---

# Recipe Runner

The recipe runner executes declarative YAML workflows in compiled Rust-backed control flow. It does not rely on prompt-only step enforcement.

The CLI and Python API descriptions in this page reflect current usage. The reliability docs linked near the end describe the behavior the project is building toward, not a blanket claim that every runtime path already matches that target.

## What It Does

The runner gives amplihack a deterministic way to execute workflows such as `smart-orchestrator`, `default-workflow`, and `investigation-workflow`.

Each run:

- loads a concrete YAML recipe
- expands template variables from runtime context
- executes bash, agent, and sub-recipe steps in controlled order
- returns a structured `RecipeResult`

## Choose the Right Entrypoint

### Python API: name-based resolution

Use the Python API when you want bundled recipe names such as `smart-orchestrator` to resolve automatically.

```python
from amplihack.recipes import find_recipe, run_recipe_by_name

print(find_recipe("smart-orchestrator"))

result = run_recipe_by_name(
    "smart-orchestrator",
    user_context={
        "task_description": "Validate merged workflow reliability",
        "repo_path": ".",
        "force_single_workstream": "true",
    },
    progress=True,
)
print(result)
```

### CLI: path-based execution

Use the CLI when you already know the exact YAML file you want.

```bash
python -m amplihack recipe validate amplifier-bundle/recipes/smart-orchestrator.yaml
python -m amplihack recipe show amplifier-bundle/recipes/smart-orchestrator.yaml --no-context
python -m amplihack recipe run amplifier-bundle/recipes/smart-orchestrator.yaml \
  -c task_description="Validate merged workflow reliability" \
  -c repo_path="." \
  -c force_single_workstream="true" \
  --dry-run
```

`run`, `show`, and `validate` take a recipe path. They do not resolve bundled recipe names for you.

## Context Passing

Pass runtime context with repeated `-c` or `--context` assignments.

```bash
python -m amplihack recipe run amplifier-bundle/recipes/default-workflow.yaml \
  -c task_description="Add user authentication" \
  -c repo_path="." \
  -c branch_name="feat/user-auth" \
  --dry-run
```

The Python API accepts the same data as a `user_context` dictionary.

## Recipe Discovery

The remediation target for merged source checkouts is simple:

- name-based resolution must be canonical and deterministic
- the repo-root `amplifier-bundle/recipes/` bundle must win ahead of stale packaged copies under `src/amplihack/amplifier-bundle/recipes/`
- discovery and direct lookup must agree about which YAML file is real

Use `find_recipe()` when you need proof of which path will execute.

## Large Context and Spill Transport

Large context values can spill to internal `file://...` transport refs.

That is only a transport detail. The target state is that downstream prompts receive real content instead of the URI. Validate rendered child prompts before claiming that guarantee is complete.

## Condition Evaluation

Existing workflows use bracket-style expressions such as `scope['has_ambiguities']`.

The target state is that malformed conditions fail closed instead of silently defaulting to running the guarded step. Use the reliability docs to validate the current implementation against that target.

## Documentation

Use the docs below based on what you need:

- [Recipe CLI Quick Reference](quick-reference.md) - short command lookup
- [Recipe CLI Commands How-To](../howto/recipe-cli-commands.md) - task-oriented CLI guide
- [Recipe CLI Reference](../reference/recipe-cli-reference.md) - complete CLI syntax and behavior
- [Tutorial: Validate recipe-runner reliability end to end](../tutorials/recipe-runner-reliability-validation.md) - full workflow validation
- [How to Validate Recipe-Runner Reliability](../howto/validate-recipe-runner-reliability.md) - short validation procedure
- [Understanding Recipe-Runner Reliability](../concepts/recipe-runner-reliability.md) - architecture and rationale
- [Recipe-Runner Reliability Reference](../reference/recipe-runner-reliability.md) - contracts and pass/fail rubric
