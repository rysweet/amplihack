# Workflow Publish Import Validation

**Scoped publish-validation stage that runs immediately before the current commit/push step.**

> [Home](../index.md) > [Features](README.md) > Workflow Publish Import Validation

## Quick Navigation

- [How to configure workflow publish import validation](../howto/configure-workflow-publish-import-validation.md)
- [Tutorial: workflow publish import validation](../tutorials/workflow-publish-import-validation.md)
- [Workflow publish import validation reference](../reference/workflow-publish-import-validation.md)

---

## Status

This page describes the scoped publish-validation behavior implemented for issue 4064.

Current tree state:

- `amplifier-bundle/recipes/default-workflow.yaml` still uses **Step 15** for
  **Commit and Push**, and now runs publish import validation immediately before
  the commit is created
- `scripts/pre-commit/build_publish_validation_scope.py` builds the exact
  scoped Python validation file from the staged publish manifest
- `scripts/pre-commit/check_imports.py` supports `--files-from` for exact-list
  validation without repo-wide fallback
- the subsequent `git commit` skips only the repo-wide pre-commit
  `check-imports` hook because Step 15 already ran the scoped validator

Older issue discussion called this work "Step 15". That shorthand remains
accurate because the validation now runs as a publish-only substep inside the
existing commit/push stage, without renumbering the workflow.

---

## What It Does

The publish-validation stage now:

1. read the exact repo-relative staged publish manifest emitted by Step 15
2. keep manifest-listed `.py` files as seed files
3. derive allowed roots from those seed files
4. expand only repo-local Python dependencies that resolve inside those
   already-allowed roots
5. write an exact scoped `.py` file list
6. run `check_imports.py --files-from <scope-file>`
7. create the commit with `SKIP=check-imports` so pre-commit does not rerun the
   repo-wide import hook against all staged Python files

It does **not** fall back to a repository-wide Python scan in scoped mode. The goal is strict validation for the thing being published, not for unrelated files elsewhere in the repo.

### Optional Dependency Behavior

`textual` and `amplifier_core` stay optional. Their absence matters only when
the scoped validation set includes a file that genuinely imports them.

| Dependency       | Publish fails when                                                | Publish does not fail when                                             |
| ---------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `textual`        | A file inside the scoped validation set imports `textual`.        | Only files outside the staged publish surface import `textual`.        |
| `amplifier_core` | A file inside the scoped validation set imports `amplifier_core`. | Only files outside the staged publish surface import `amplifier_core`. |

### `.claude/scenarios/**` Behavior

Unrelated `.claude/scenarios/**` scripts are out of scope for workflow
publishes. The publish-validation stage does not discover, glob, or
validate those files unless they are explicitly part of the staged publish
surface. Scenario-only imports therefore cannot block an unrelated publish.

---

## Boundary Rules

| Rule                                     | Behavior                                                                                                                                            | Why it matters                                                                                      |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Publish-only insertion point             | The new validation stage will run immediately before the current commit/push step.                                                                  | Resolves the current "Step 15" naming mismatch without pretending the renumbering already happened. |
| Manifest-first scope                     | Validation starts from the exact staged publish manifest.                                                                                           | Avoids validating unrelated repo files.                                                             |
| Root-derived allowlist                   | Dependency expansion may add files only under roots already derived from manifest seed files.                                                       | Prevents hidden jumps into unrelated repository areas.                                              |
| `src/<package>/` roots                   | A seed under `src/<package>/...` may expand within that same top-level package root.                                                                | Keeps package resolution predictable.                                                               |
| `amplifier-bundle` roots                 | A seed under `amplifier-bundle/modules/<name>/...` stays inside that module; other `amplifier-bundle/<subtree>/...` seeds stay inside that subtree. | Stops sibling bundle modules from being pulled in implicitly.                                       |
| Cross-root imports require both roots    | A bundle wrapper can reach `src/amplihack/...` only when the manifest already seeded that `src` root too.                                           | Avoids inventing hidden aliases between bundle wrappers and runtime packages.                       |
| No repository fallback                   | `check_imports.py --files-from` validates exactly the scoped file list.                                                                             | Stops broad scans from reappearing.                                                                 |
| No repo-wide hook rerun                  | The later `git commit` skips only the pre-commit `check-imports` hook after the scoped run succeeds.                                                | Prevents commit-time fallback to all staged Python files.                                           |
| Empty Python surface is explicit success | A publish with no scoped Python files exits cleanly after reporting zero validated files.                                                           | Keeps non-Python publishes from failing for the wrong reason.                                       |
| Real missing imports still fail          | A missing import in a scoped file still stops the publish.                                                                                          | Preserves the safety value of the new stage.                                                        |

---

## Execution Shape

The publish path now looks like this:

```text
--- Publish Import Validation ---
publish_manifest=/tmp/amplihack-publish-manifest-424242.txt
validation_scope=/tmp/amplihack-publish-scope-424242.txt
seed_count=3
expanded_local_dep_count=2
validated_count=5
python scripts/pre-commit/check_imports.py --files-from "$validation_scope"
SKIP=check-imports git commit -m "..."
```

If the staged publish surface contains no Python files, the stage reports an empty Python surface and succeeds without attempting repo-wide import checks.

---

## What Happens When Something Is Wrong

The publish-validation stage fails when any of these conditions is
true:

- the publish manifest is missing, unreadable, or contains unsafe paths
- a scoped Python file uses a missing required import
- a scoped Python file imports `textual` or `amplifier_core` and the dependency is not installed
- the helper cannot normalize the scoped file list into safe repo-relative files

Example relevant failure:

```text
❌ IMPORT VALIDATION FAILED - FIX BEFORE COMMITTING

Import Errors:

  tests/fixtures/workflow_publish/relevant_missing_import.py:
    FAILED: No module named 'definitely_missing_module'
```

That failure is intentional because the missing import belongs to the staged publish surface.

---

## Where To Go Next

- Use the [workflow worktree isolation overview](../worktree-support.md) to understand why Step 15 revalidates the worktree and branch before scoped publish validation and commit creation.
- Use the [configuration guide](../howto/configure-workflow-publish-import-validation.md) to review the manifest, root-boundary, and scoped-validator contract.
- Use the [tutorial](../tutorials/workflow-publish-import-validation.md) for a design walkthrough of optional-dependency and scenario exclusions.
- Use the [reference page](../reference/workflow-publish-import-validation.md) for the workflow contract, helper CLI, and `--files-from` semantics.
