---
title: "Recipe-runner reliability target reference"
description: "Reference for the planned merged-worktree reliability contract: canonical recipe resolution, large-context spill transport, bracket-condition support, and validation-facing Python and CLI surfaces."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: reference
---

# Recipe-runner reliability target reference

## Overview

This reference defines the target contracts for the recipe-runner reliability remediation.

Use it as a specification the implementation and validation should converge on. Do not read it as a claim that the current runtime already satisfies every item below.

It covers four targets:

- prompt transport across process boundaries
- downstream dereference of spilled `file://...` transport refs
- bracket-condition compatibility
- canonical recipe resolution in a merged source checkout

## Validation outcome categories

| Category | Definition |
| --- | --- |
| `fixed` | the target path ran and the required evidence is present |
| `partial` | part of the target path works, but at least one required downstream condition still fails |
| `still failing` | the original failure mode is still present |
| `blocked by infrastructure` | the environment failed before the target path could be exercised |

A structurally successful run that never exercises the target behavior is **hollow success** and must not be reported as `fixed`.

## Reliability targets

| Target | `fixed` means | `partial` means | `still failing` means | `blocked by infrastructure` means |
| --- | --- | --- | --- | --- |
| Large-context transport | no `E2BIG` or `Argument list too long`; workflow reaches the target steps | the outer transport survives, but a downstream layer still loses the task content | the launcher still fails with `E2BIG` or `Argument list too long` | runner, auth, or host environment fails before the large-context path runs |
| Spill dereference | child prompts render actual content instead of raw `file://...` refs | spill occurs, but a rendered child field still contains `file://...` | raw transport refs remain visible in agent-facing prompt fields | child steps never execute, so prompt rendering cannot be inspected |
| Bracket-condition compatibility | expressions such as `scope['has_ambiguities']` evaluate without parser errors | compatibility works in one path but malformed conditions still escape as run-anyway success | `Condition error: Parse error: unexpected character: '['` still appears | the workflow never reaches the guarded step |
| Recipe resolution | resolution evidence points at the repo-root `amplifier-bundle/recipes/` copy | the right file is listed somewhere, but the executed path is ambiguous | discovery still resolves to a stale packaged copy ahead of the repo-root bundle | resolution cannot run because the environment fails first |

## Canonical search policy

### Target behavior after remediation

For merged source checkouts, canonical recipe lookup prefers the repo-root bundle over stale packaged copies.

At minimum, these statements must both be true:

- `find_recipe("smart-orchestrator")` resolves to `amplifier-bundle/recipes/smart-orchestrator.yaml`
- the path logged by the runtime matches the same repo-root bundle copy

### Search-policy properties

| Property | Requirement |
| --- | --- |
| Canonicalization | candidate directories are resolved to absolute canonical paths before use |
| Deduplication | duplicate directories are removed before precedence is applied |
| Consistency | `discover_recipes()`, `find_recipe()`, and the Rust bridge all use the same precedence rules |
| Repo-root precedence | the repo-root `amplifier-bundle/recipes/` bundle wins ahead of `src/amplihack/amplifier-bundle/recipes/` in merged source checkouts |

Current discovery code still advertises last-match-wins behavior. Validation should record actual output until remediation lands.

## Spill transport contract

| Item | Value |
| --- | --- |
| Spill threshold | values at or above `32,768` UTF-8 bytes spill to an internal file |
| Transport representation | internal `file://...` URI used as a transport detail |
| Filesystem permissions | spill directory `0700`, spill files `0600` |
| Required dereference point | before child prompt assembly and downstream sub-recipe propagation |
| Forbidden success evidence | a raw `file://...` URI in a rendered child prompt or downstream task field |

The threshold and file permissions exist in current code. End-to-end dereference at every rendered child prompt path is still something validation must prove.

## Downstream prompt preservation

### Required fields

Validation is only complete when meaningful task text reaches the fields that child prompts actually render.

Examples of relevant downstream fields include:

- `investigation_question`
- task fields materialized into child prompt templates

Top-level fields such as `task_description` are not enough on their own.

Current workflow definitions do not automatically normalize `task_description` into `investigation_question`. Treat `investigation_question` as an example downstream field to inspect, not as proof that normalization already exists.

## Condition evaluation contract

| Condition form | Expected behavior |
| --- | --- |
| `scope['has_ambiguities']` | supported |
| `scope["has_ambiguities"]` | supported |
| missing or malformed expressions | fail closed with explicit failure, not silent step execution |
| no condition | step executes normally |

Current code still falls back to running the step when condition evaluation raises an exception. This table describes the behavior the remediation is meant to enforce.

## Python API surface

### `find_recipe(name, search_dirs=None) -> Path | None`

Returns the canonical YAML path for a recipe name.

Use this when validation needs concrete evidence about which copy of a bundled recipe will execute.

### `list_recipes(search_dirs=None) -> list[RecipeInfo]`

Returns discovered recipes as metadata records.

Use this to inspect the discovery surface, not to prove which colliding recipe file wins at runtime.

### `run_recipe_by_name(name, user_context=None, dry_run=False, recipe_dirs=None, working_dir='.', auto_stage=True, progress=False, agent_binary=None) -> RecipeResult`

Runs a recipe by name through the Rust-backed runner.

Use this as the preferred validation entrypoint when you want name-based resolution, streamed progress, and a `RecipeResult` object with `success`, `step_results`, `context`, and `log_path`.

### `RecipeResult`

| Field | Meaning |
| --- | --- |
| `recipe_name` | executed recipe name |
| `success` | overall success flag |
| `step_results` | per-step outcomes |
| `context` | final materialized context |
| `log_path` | runner log path when emitted by the runtime |

## CLI surface for validation

The CLI and the Python API have different lookup behavior.

### Python API

- accepts recipe names through `run_recipe_by_name()`
- resolves names through `find_recipe()`

### CLI

- `amplihack recipe run`, `show`, and `validate` take a **recipe file path**
- context values are passed with repeated `-c` or `--context` `KEY=VALUE` assignments

### Validation-oriented commands

```bash
python -m amplihack recipe list
python -m amplihack recipe validate amplifier-bundle/recipes/smart-orchestrator.yaml
python -m amplihack recipe show amplifier-bundle/recipes/smart-orchestrator.yaml --no-context
python -m amplihack recipe run amplifier-bundle/recipes/smart-orchestrator.yaml \
  -c task_description="Validate recipe-runner reliability on merged code" \
  -c repo_path="." \
  -c force_single_workstream="true" \
  --dry-run
```

## Context keys commonly used in reliability validation

| Key | Purpose |
| --- | --- |
| `task_description` | top-level validation prompt |
| `repo_path` | repository root for workflow execution |
| `force_single_workstream` | keeps orchestration on one workstream when the validation should stay linear |
| `investigation_question` | an example downstream analysis field to inspect in the current investigation workflow |

## Evidence checklist

Use this checklist before reporting `fixed`:

- [ ] the run used merged runtime code from the current checkout
- [ ] the run exercised a real workflow path
- [ ] no `E2BIG` or `Argument list too long` appeared
- [ ] no rendered child prompt leaked a raw `file://...` URI
- [ ] bracket-style conditions evaluated without `[` parser errors
- [ ] recipe resolution evidence pointed at the repo-root bundle
- [ ] the result was not hollow success
