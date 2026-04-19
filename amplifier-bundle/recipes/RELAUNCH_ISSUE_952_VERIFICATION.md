# Relaunch Issue #952 — Verification

This note records verification that the recipe fixes requested by
[issue #952](https://github.com/rysweet/amplihack/issues/952) are already
present on `main`. No further code changes were required.

## Fix 1 — `default-workflow.yaml` LBracket conditions

Originally the recipe used `not in [ ... ]` set-membership expressions in
several `condition:` clauses, which the recipe runner's expression parser
did not accept (LBracket parser error).

These were rewritten to chained `!=` form (logical AND of inequalities)
in commit **`71b87a93f`** (PR #4367,
*"fix: resolve step-07-write-tests LBracket parser error"*).

Verification:

```bash
$ grep -n "not in \[" amplifier-bundle/recipes/default-workflow.yaml
# (no matches)
```

Example of current form used in the file:

```yaml
condition: >
  resume_checkpoint != 'checkpoint-after-implementation'
  and resume_checkpoint != 'checkpoint-after-review-feedback'
```

## Fix 2 — `smart-orchestrator.yaml` multitask orchestrator path

The hard-coded multitask orchestrator path was replaced with a lookup
that resolves through `AMPLIHACK_HOME` (then `~/.amplihack`, then the
package, then the repo root) in commit **`6a4b19a23`** (PR #3771,
*"resolve orchestrator.py from AMPLIHACK_HOME"*).

Current invocation (around line 573):

```bash
ORCH_SCRIPT="$(python3 -m amplihack.runtime_assets multitask-orchestrator 2>/dev/null || true)"
```

The accompanying error message instructs operators to set
`AMPLIHACK_HOME` if resolution fails.

## Conclusion

Both fixes referenced by issue #952 are merged on `main`. This PR adds
this verification note so the relaunch task has an auditable artifact.
