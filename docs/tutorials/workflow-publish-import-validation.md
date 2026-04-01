# Tutorial: Workflow Publish Import Validation

**Time to Complete**: 15 minutes
**Skill Level**: Intermediate
**Prerequisites**: Ability to inspect the repository tree and run the workflow-publish validation commands shown below.

This tutorial walks through the publish-validation feature shipped for issue 4064.

## What You'll Learn

By the end of this tutorial you will know how to:

1. confirm the current implementation surface
2. model the staged publish manifest
3. derive the allowed roots and scoped validation set
4. reason about optional dependencies and scenario exclusions
5. see how a relevant missing import fails in the shipped workflow

---

## Step 1: Confirm the Current Surface

The shipped surface looks like this:

```text
amplifier-bundle/recipes/default-workflow.yaml: Step 15 = Commit and Push, with scoped publish import validation before commit
scripts/pre-commit/build_publish_validation_scope.py: present
scripts/pre-commit/check_imports.py: supports --files-from mode
```

---

## Step 2: Model a Small Publish Manifest

Start with the publish surface you intend to validate:

```bash
cat > /tmp/workflow-publish-manifest.txt <<'EOF'
src/amplihack/recipes/__init__.py
src/amplihack/recipes/recipe_command.py
amplifier-bundle/tools/orch_helper.py
EOF
```

This manifest intentionally excludes `.claude/scenarios/**` and any files that
depend on `textual` or `amplifier_core`.

---

## Step 3: Derive the Allowed Roots

From that manifest, the scope builder should derive these roots:

```text
src/amplihack/
amplifier-bundle/tools/
```

The expansion rules are:

1. keep manifest-listed `.py` files as seeds
2. expand repo-local Python dependencies only inside those already-allowed
   roots
3. refuse to jump into new top-level roots that were not seeded by the manifest

That last rule is what keeps unrelated repo areas out of scope.

---

## Step 4: Build the Scope

The command shape looks like this:

```bash
python scripts/pre-commit/build_publish_validation_scope.py \
  --manifest /tmp/workflow-publish-manifest.txt \
  --output /tmp/workflow-publish-scope.txt
```

The expected scope file for the manifest above is:

```text
src/amplihack/recipes/__init__.py
src/amplihack/recipes/recipe_command.py
amplifier-bundle/tools/orch_helper.py
```

If any of those files import other repo-local Python modules that still resolve
inside `src/amplihack/` or `amplifier-bundle/tools/`, those files should be
appended before validation. If they resolve into a new root that the manifest
did not seed, the builder should stop there instead of broadening the scope.

---

## Step 5: Validate with Optional Dependencies Absent

Leave `textual` and `amplifier_core` uninstalled in the environment and run:

```bash
python scripts/pre-commit/check_imports.py \
  --files-from /tmp/workflow-publish-scope.txt
```

Expected result:

```text
Checking imports for 3 file(s)...

1. Validating type hint imports...

2. Testing module imports...
  ✅ src/amplihack/recipes/__init__.py: OK
  ✅ src/amplihack/recipes/recipe_command.py: OK
  ✅ amplifier-bundle/tools/orch_helper.py: OK

✅ All imports valid!
```

The publish passes because the new stage is checking only the selected scope,
not unrelated files elsewhere in the repository.

---

## Step 6: Confirm Scenario Files Stay Out of Scope

Search the generated scope file:

```bash
grep -n '^\\.claude/scenarios/' /tmp/workflow-publish-scope.txt
```

Expected result:

```text
# no output
```

That is the contract: scenario scripts that are not part of the staged
publish do not enter the new validation stage on their own.

---

## Step 7: See a Relevant Missing Import Fail

Now switch to a manifest that includes a Python file with a real missing import
in the staged publish surface. In a disposable branch or scratch checkout,
rewrite the manifest:

```bash
cat > /tmp/workflow-publish-manifest.txt <<'EOF'
tests/fixtures/workflow_publish/relevant_missing_import.py
EOF
```

and suppose that file contains:

```python
import definitely_missing_module
```

Run the same two commands again:

```bash
python scripts/pre-commit/build_publish_validation_scope.py \
  --manifest /tmp/workflow-publish-manifest.txt \
  --output /tmp/workflow-publish-scope.txt

python scripts/pre-commit/check_imports.py \
  --files-from /tmp/workflow-publish-scope.txt
```

Expected result:

```text
❌ IMPORT VALIDATION FAILED - FIX BEFORE COMMITTING

Import Errors:

  tests/fixtures/workflow_publish/relevant_missing_import.py:
    FAILED: No module named 'definitely_missing_module'
```

This is the important safeguard: scoped validation is narrower, not weaker.

---

## Step 8: Place the Stage in the Workflow

The publish path performs the same sequence automatically:

1. emit the staged publish manifest
2. build the scoped validation file
3. print `seed_count`, `expanded_local_dep_count`, and `validated_count`
4. run `check_imports.py --files-from <scope-file>`
5. create the commit with `SKIP=check-imports` so pre-commit does not rerun the
   repo-wide import hook

The important naming detail is that this stage should run **immediately before
the current commit/push step**. The docs should not lock in a final step number
until the workflow file is updated.

---

## Next Steps

- Use the [configuration guide](../howto/configure-workflow-publish-import-validation.md) to review the manifest, root-boundary, and scoped-validator contract.
- Use the [reference page](../reference/workflow-publish-import-validation.md) when wiring tests, CI, or custom publish wrappers.
- Use the [feature overview](../features/workflow-publish-import-validation.md) for the guarantees and trade-offs.
