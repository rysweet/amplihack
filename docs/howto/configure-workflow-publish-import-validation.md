# How to Configure Workflow Publish Import Validation

> [Home](../index.md) > How-To > Configure Workflow Publish Import Validation

This guide describes the workflow publish import validation contract now used by Step 15. The command shapes shown below are the current implementation surface.

---

## 1. Start from the Current Behavior

The current repo state is:

- `amplifier-bundle/recipes/default-workflow.yaml` still uses **Step 15** for
  **Commit and Push**
- that Step-15 command now writes a staged publish manifest, builds a scoped
  validation file, prints `seed_count`, `expanded_local_dep_count`, and
  `validated_count`, then runs `check_imports.py --files-from ...` before
  creating the commit
- that same commit call now sets `SKIP=check-imports` so pre-commit does not
  rerun the repo-wide import hook after scoped validation already succeeded
- `scripts/pre-commit/build_publish_validation_scope.py` owns scope building
- `scripts/pre-commit/check_imports.py` supports both positional files and
  `--files-from` scoped mode

The validation remains a **publish-only substep inserted immediately before the
current commit/push step**. The workflow numbering stays the same.

---

## 2. Start from the Staged Publish Manifest

The publish manifest is the source of truth for the validator. It is a
newline-delimited UTF-8 file with one repo-relative path per line:

```text
amplifier-bundle/tools/orch_helper.py
src/amplihack/recipes/__init__.py
src/amplihack/recipes/recipe_command.py
```

Path rules:

- manifest paths are repo-relative and point at files inside the repo
- no absolute paths
- no `..` traversal
- no control characters
- no directories
- no missing files

---

## 3. Derive the Allowed Roots

The scope builder should derive an allowlist of roots from the manifest's
Python seed files, then expand dependencies only inside those already-allowed
roots.

| Seed path shape                       | Derived root                                                         | Boundary rule                                                                                            |
| ------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `src/<package>/...`                   | `src/<package>/`                                                     | Expansion may stay inside that same top-level package root.                                              |
| `amplifier-bundle/modules/<name>/...` | `amplifier-bundle/modules/<name>/`                                   | Expansion stays inside that bundle module unless another root was separately seeded.                     |
| `amplifier-bundle/<subtree>/...`      | `amplifier-bundle/<subtree>/`                                        | `tools`, `recipes`, and other sibling bundle subtrees stay isolated unless the manifest seeded them too. |
| `.claude/scenarios/<name>/...`        | `.claude/scenarios/<name>/` only when explicitly seeded              | Scenario files stay out of unrelated publishes by default.                                               |
| Other Python files                    | Closest owning package directory, or the containing script directory | The builder must not escalate to a repo-wide root.                                                       |

Important cross-root rule: if a bundle wrapper depends on
`src/amplihack/...`, the manifest must seed that `src/amplihack/` root too.
The scope builder must not invent hidden aliases between bundle wrappers and
runtime packages.

---

## 4. Build the Validation Scope

The helper script turns the publish manifest into the exact Python file list that the publish-validation stage checks.

```bash
python scripts/pre-commit/build_publish_validation_scope.py \
  --manifest /tmp/workflow-publish-manifest.txt \
  --output /tmp/workflow-publish-scope.txt
```

Expected output:

```json
{
  "seed_count": 2,
  "expanded_local_dep_count": 1,
  "validated_count": 3
}
```

The output file should contain repo-relative `.py` paths only, one per line.
Non-Python assets remain part of the publish, but they do not enter import
smoke validation.

---

## 5. Validate Exactly That Scope

The scoped validator looks like this:

```bash
python scripts/pre-commit/check_imports.py \
  --files-from /tmp/workflow-publish-scope.txt
```

`--files-from` rules:

- mutually exclusive with positional `FILES...`
- input file is UTF-8 text with one repo-relative `.py` path per line
- blank lines are ignored
- comments are not supported
- paths are trimmed, normalized, deduplicated, and rejected if they escape the
  repo, refer to missing files, name directories, or are not `.py`
- validation runs against that exact list only; there is no repo-wide fallback
- an empty scope file is a valid "no Python files to check" success
- the later Step-15 `git commit` must skip only the pre-commit `check-imports`
  hook so the exact scoped run remains authoritative

Without `--files-from`, `check_imports.py` should keep its existing positional
behavior for legacy callers.

---

## 6. Read the Counts

The publish-validation stage reports three counts:

| Field                      | Meaning                                                                    |
| -------------------------- | -------------------------------------------------------------------------- |
| `seed_count`               | Published `.py` files taken directly from the manifest.                    |
| `expanded_local_dep_count` | Additional repo-local Python files pulled in through dependency expansion. |
| `validated_count`          | Total files sent to `check_imports.py --files-from`.                       |

Use the counts to see whether the scope is too narrow or too broad. A
sudden jump in `expanded_local_dep_count` usually means the staged publish
surface now depends on more local modules than before.

---

## 7. Know the Fixed Rules

These are contract rules, not tuning knobs:

- the publish-validation stage runs before the current commit/push step
- `.claude/scenarios/**` does not block unrelated workflow publishes.
- `textual` is only required when a scoped file imports it.
- `amplifier_core` is only required when a scoped file imports it.
- relevant missing imports inside the scoped validation set still fail the publish.
- an empty Python validation surface is an explicit success.
- the later Step-15 commit must not rerun the repo-wide `check-imports` hook.

If you need different behavior, change the workflow contract and its tests
together. Do not reintroduce repo-wide scanning or blanket allowlists.

---

## 8. Troubleshoot the Common Failures

| Symptom                                                 | Likely cause                                                                                     | What to do                                                       |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| `No module named 'textual'`                             | A scoped file really imports `textual`.                                                          | Install `textual` or remove the in-scope import.                 |
| `No module named 'amplifier_core'`                      | A scoped file really imports `amplifier_core`.                                                   | Install `amplifier_core` or remove the in-scope import.          |
| A scenario script blocks the publish                    | The scenario script was explicitly selected, or a custom wrapper bypassed scoped mode.           | Check the manifest and verify the new stage uses `--files-from`. |
| A bundle helper is missing `src/amplihack` dependencies | The manifest seeded the bundle root but not the `src/amplihack/` root it depends on.             | Seed both roots explicitly; do not rely on hidden aliasing.      |
| Helper rejects a path                                   | The manifest contains an unsafe, missing, or non-repo path.                                      | Rewrite the manifest with valid repo-relative file paths only.   |
| `validated_count=0` when you expected Python files      | The selected publish contains no `.py` files, or the Python files were not part of the manifest. | Check the manifest contents first.                               |

---

## Related Documentation

- [Workflow publish import validation overview](../features/workflow-publish-import-validation.md)
- [Tutorial: workflow publish import validation](../tutorials/workflow-publish-import-validation.md)
- [Workflow publish import validation reference](../reference/workflow-publish-import-validation.md)
