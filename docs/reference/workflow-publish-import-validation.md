# Workflow Publish Import Validation Reference

> [Home](../index.md) > Reference > Workflow Publish Import Validation

Field-level contract for the scoped publish-validation stage used by workflow publishes.

## Contents

- [Status and Naming](#status-and-naming)
- [Definitions](#definitions)
- [Workflow Contract](#workflow-contract)
- [Allowlist Boundary and Root Resolution](#allowlist-boundary-and-root-resolution)
- [Publish Manifest Format](#publish-manifest-format)
- [Scope Builder Helper](#scope-builder-helper)
- [Scoped Mode for Import Checking](#scoped-mode-for-import-checking)
- [Counts and Logs](#counts-and-logs)
- [Failure Semantics](#failure-semantics)
- [Security Invariants](#security-invariants)
- [Non-Goals](#non-goals)

---

## Status and Naming

This page documents the contract implemented for issue 4064.

Current tree state:

- `amplifier-bundle/recipes/default-workflow.yaml` still defines **Step 15** as
  **Commit and Push**, and now runs the scoped publish import validation before
  creating the commit
- `scripts/pre-commit/build_publish_validation_scope.py` builds the scoped
  validation file from the staged publish manifest
- `scripts/pre-commit/check_imports.py` supports `--files-from` scoped mode
- the later `git commit` skips only the pre-commit `check-imports` hook because
  the scoped validator already ran inside Step 15

The import validation remains a **publish-only substep inserted immediately
before the current commit/push step**. Older issue discussion used "Step 15" as
shorthand, and this reference keeps that shorthand without renumbering the workflow.

---

## Definitions

| Term                      | Meaning                                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| publish manifest          | Newline-delimited repo-relative file list produced by Step 15 from the staged publish surface.                                              |
| seed file                 | A `.py` file that appears directly in the publish manifest.                                                                                 |
| expanded local dependency | A repo-local `.py` file reached by import resolution from a seed file and still inside an already-allowed root.                             |
| validation scope          | The final deduplicated newline-delimited `.py` file list passed to `check_imports.py --files-from`.                                         |
| allowed root              | A repo subtree derived from a manifest seed file that bounds dependency expansion.                                                          |
| publish-relevant surface  | The staged publish artifacts plus repo-local Python dependencies reachable from those artifacts without escaping the already-allowed roots. |

---

## Workflow Contract

The publish-validation stage performs these operations in order:

1. read the staged publish manifest
2. normalize and validate manifest paths
3. keep published `.py` files as seed files
4. derive the allowed roots from those seed files
5. expand only resolvable repo-local Python dependencies inside those
   already-allowed roots
6. write the final validation scope file
7. report `seed_count`, `expanded_local_dep_count`, and `validated_count`
8. run `check_imports.py --files-from <scope-file>`
9. create the commit while skipping the repo-wide pre-commit `check-imports`
   hook

### Required Invariants

| Invariant                           | Contract                                                                                |
| ----------------------------------- | --------------------------------------------------------------------------------------- |
| Publish-only insertion point        | The new stage runs immediately before the current commit/push step.                     |
| Exact scope                         | The stage validates only the files in the generated validation scope.                   |
| No repo-wide fallback               | Scoped mode does not rediscover or glob unrelated repository files.                     |
| No repo-wide hook rerun             | After the scoped run, `git commit` suppresses only the pre-commit `check-imports` hook. |
| Optional dependency neutrality      | `textual` and `amplifier_core` matter only when the scoped files import them.           |
| Scenario isolation                  | `.claude/scenarios/**` does not block unrelated workflow publishes.                     |
| Fail closed on real in-scope errors | Missing imports inside the validation scope still fail the publish.                     |
| Explicit empty-scope success        | No scoped Python files means success after a reported no-op, not silent skipping.       |

---

## Allowlist Boundary and Root Resolution

The scope builder must derive an allowlist of roots from the manifest's Python
seed files. Dependency expansion may add only repo-local `.py` files that
resolve under one of those already-allowed roots. It must never create a new
top-level root during expansion.

### Derived Root Rules

| Seed path shape                       | Derived root                                                         | Notes                                                                                 |
| ------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `src/<package>/...`                   | `src/<package>/`                                                     | Top-level runtime package root.                                                       |
| `amplifier-bundle/modules/<name>/...` | `amplifier-bundle/modules/<name>/`                                   | Stay inside that bundle module unless another root was separately seeded.             |
| `amplifier-bundle/<subtree>/...`      | `amplifier-bundle/<subtree>/`                                        | `tools`, `recipes`, and other sibling bundle subtrees are not inferred automatically. |
| `.claude/scenarios/<name>/...`        | `.claude/scenarios/<name>/` only when explicitly seeded              | Scenario files stay out of unrelated publishes by default.                            |
| Other Python files                    | Closest owning package directory, or the containing script directory | Do not escalate to a repo-wide root.                                                  |

### Cross-Root Rule

A dependency may resolve into another root only when that root was already
derived from a manifest seed.

Example:

```text
manifest seeds:
  amplifier-bundle/tools/orch_helper.py
  src/amplihack/recipes/recipe_command.py

allowed roots:
  amplifier-bundle/tools/
  src/amplihack/
```

In that case, dependency expansion may move between those two roots because
both were seeded explicitly. If the manifest seeds only
`amplifier-bundle/tools/orch_helper.py`, the builder must **not** infer a hidden
alias that broadens the scope into `src/amplihack/`.

This rule is deliberate: bundle wrappers that rely on runtime package files
must seed both roots when both belong to the intended publish surface.

---

## Publish Manifest Format

The publish manifest is a UTF-8 text file with one repo-relative path per line.

### Accepted Input

```text
amplifier-bundle/tools/orch_helper.py
src/amplihack/recipes/__init__.py
src/amplihack/recipes/recipe_command.py
```

### Rejected Input

- absolute paths
- `..` traversal
- CR, LF, or NUL inside a path entry
- directories
- missing files
- files that resolve outside the repository root

Duplicate entries are allowed in the manifest input but are removed after
normalization.

---

## Scope Builder Helper

Helper script that will turn the publish manifest into the exact Python file
list that the new stage validates.

### Synopsis

```bash
python scripts/pre-commit/build_publish_validation_scope.py \
  --manifest <path> \
  --output <path> \
  [--repo-root <path>]
```

### Arguments

| Argument             | Required | Meaning                                                                                 |
| -------------------- | -------- | --------------------------------------------------------------------------------------- |
| `--manifest <path>`  | Yes      | Path to the newline-delimited publish manifest.                                         |
| `--output <path>`    | Yes      | Path where the scoped validation file is written.                                       |
| `--repo-root <path>` | No       | Repository root used for path normalization. Defaults to the current working directory. |

### Output Contract

The helper does two things on success:

1. writes the scoped validation file named by `--output`
2. prints JSON to stdout with these fields:

```json
{
  "seed_count": 2,
  "expanded_local_dep_count": 1,
  "validated_count": 3
}
```

The scope file contains repo-relative `.py` files only, one per line.

### Resolution Rules

- manifest-derived `.py` files become seed files
- non-Python manifest entries remain part of the publish but do not enter import
  smoke validation
- dependency expansion follows only repo-local Python imports that resolve
  inside the already-allowed roots
- the helper must not create new top-level roots during expansion
- unresolved third-party imports are left for `check_imports.py` to validate
  during smoke import
- expansion is cycle-safe and deduplicated

### Exit Codes

| Code | Meaning                                                  |
| ---- | -------------------------------------------------------- |
| `0`  | Scope built successfully.                                |
| `1`  | Manifest missing, unreadable, or contains invalid paths. |

---

## Scoped Mode for Import Checking

Scoped mode for `scripts/pre-commit/check_imports.py`.

### Synopsis

```bash
python scripts/pre-commit/check_imports.py FILES...
python scripts/pre-commit/check_imports.py --files-from <path>
```

### Arguments

| Argument              | Required | Meaning                                                                                                                       |
| --------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `FILES...`            | No       | Existing positional file list for legacy callers. Mutually exclusive with `--files-from`.                                     |
| `--files-from <path>` | No       | Read the exact repo-relative validation scope from a newline-delimited file. The new publish-validation stage uses this mode. |

### Scope-File Rules

When `--files-from` is supplied:

- `--files-from` and positional `FILES...` are mutually exclusive
- the scope file is UTF-8 text with one repo-relative `.py` path per line
- blank lines are ignored
- comments are not supported
- leading and trailing whitespace is trimmed before validation
- paths are normalized and deduplicated, preserving first occurrence
- absolute paths, traversal paths, directories, missing files, out-of-repo
  paths, and non-`.py` entries fail before import testing starts
- validation runs against that exact list
- the script does not fall back to repository-wide file discovery
- an empty scope file is valid and exits successfully after reporting that no
  Python files were checked
- Step 15 may then skip the pre-commit `check-imports` hook because the scoped
  validation already executed explicitly

Without `--files-from`, `check_imports.py` keeps its existing positional-file
behavior.

### Exit Codes

| Code | Meaning                                                      |
| ---- | ------------------------------------------------------------ |
| `0`  | Import validation succeeded, including the empty-scope case. |
| `1`  | Type-import validation or smoke-import validation failed.    |
| `2`  | Invalid CLI usage or invalid `--files-from` input.           |

---

## Counts and Logs

The new stage should log these fields before running `check_imports.py`:

| Field                      | Meaning                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| `publish_manifest`         | Path to the manifest emitted by the publish-selection path.         |
| `validation_scope`         | Path to the scoped `.py` file list passed to `check_imports.py`.    |
| `seed_count`               | Count of unique seed files taken directly from the manifest.        |
| `expanded_local_dep_count` | Count of additional repo-local files added by dependency expansion. |
| `validated_count`          | Count of files passed to `check_imports.py --files-from`.           |

`validated_count` equals `seed_count + expanded_local_dep_count`.

---

## Failure Semantics

| Condition                                                    | Result                                                          |
| ------------------------------------------------------------ | --------------------------------------------------------------- |
| Manifest missing or unreadable                               | The new stage fails before import smoke testing starts.         |
| Manifest contains unsafe or out-of-repo paths                | The new stage fails.                                            |
| Validation scope is empty                                    | The new stage succeeds after reporting an empty Python surface. |
| A scoped file imports missing `textual`                      | The new stage fails.                                            |
| A scoped file imports missing `amplifier_core`               | The new stage fails.                                            |
| Only unrelated files import `textual`                        | The new stage does not fail for that reason.                    |
| Only unrelated files import `amplifier_core`                 | The new stage does not fail for that reason.                    |
| Imports exist only in unrelated `.claude/scenarios/**` files | The new stage does not fail for that reason.                    |
| A scoped file imports any genuinely missing required module  | The new stage fails.                                            |

Example relevant failure:

```text
❌ IMPORT VALIDATION FAILED - FIX BEFORE COMMITTING

Import Errors:

  tests/fixtures/workflow_publish/relevant_missing_import.py:
    FAILED: No module named 'definitely_missing_module'
```

---

## Security Invariants

The scoped validation contract enforces these invariants:

- manifest and scope paths are normalized exactly once
- no absolute or traversal paths enter the scope
- no resolved file outside the repository root enters the scope
- dependency expansion is AST-only and repo-local
- the scope builder does not execute arbitrary code while building the scope
- `check_imports.py` still executes top-level module code for the scoped files
  it smoke-imports, so publish runs must not rely on secrets or privileged
  ambient access
- cycle-safe deduplication prevents recursive local import graphs from
  expanding forever

If the workflow cannot preserve these invariants, it fails closed.

---

## Non-Goals

This feature does not do any of the following:

- disable the new validation stage
- add a global allowlist that hides legitimate `textual` or `amplifier_core`
  failures
- validate unrelated repository files "just in case"
- make `.claude/scenarios/**` part of the import-validation surface for
  unrelated workflow publishes
- infer hidden cross-root aliases from bundle wrappers to runtime packages
- replace scenario-asset validation with Python import smoke tests

Future publishes that intentionally include scenario assets can define a
separate validation contract. That is outside the scope of this feature.

---

## See Also

- [Workflow worktree isolation overview](../worktree-support.md)
- [Workflow publish import validation overview](../features/workflow-publish-import-validation.md)
- [How to configure workflow publish import validation](../howto/configure-workflow-publish-import-validation.md)
- [Tutorial: workflow publish import validation](../tutorials/workflow-publish-import-validation.md)
