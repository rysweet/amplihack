# Quality Audit Cycle Recipe Reference

Reference for the `quality-audit-cycle` recipe
(`amplifier-bundle/recipes/quality-audit-cycle.yaml`), version 4.0.0.

## Context Variables

| Variable                | Default         | Description                                       |
| ----------------------- | --------------- | ------------------------------------------------- |
| `target_path`           | `src/amplihack` | Directory to audit                                |
| `repo_path` [PLANNED]   | `.`             | Repository root; sets `working_dir` for agent steps |
| `min_cycles`            | `3`             | Minimum audit cycles (always run at least this many) |
| `max_cycles`            | `6`             | Maximum cycles (safety valve)                     |
| `validation_threshold`  | `2`             | Minimum validators that must agree (out of 3)     |
| `severity_threshold`    | `medium`        | Minimum severity to report (`low`/`medium`/`high`/`critical`) |
| `module_loc_limit`      | `300`           | Flag modules exceeding this LOC count             |
| `fix_all_per_cycle`     | `true`          | Must fix ALL confirmed findings before next cycle (#2842) |
| `categories`            | (all)           | Comma-separated category filter                   |
| `output_dir`            | `./eval_results/quality_audit` | Where to write audit output files   |

> **[PLANNED — #3638]**: `repo_path` is not yet implemented in the recipe
> context. Once added, agent steps will use it as `working_dir` so that
> `target_path` resolves relative to the repository root.

### Internal State Variables

These are managed by the recipe loop and should not be set manually:

`audit_findings`, `validated_findings`, `fix_results`, `fix_verification`,
`cycle_number`, `cycle_history`, `recurse_decision`, `self_improvement_results`

## Steps

| Step ID              | Type  | Purpose                                                |
| -------------------- | ----- | ------------------------------------------------------ |
| `seek`               | agent | Scan codebase for quality issues (escalating depth)    |
| `validate-1/2/3`    | agent | Three independent validators confirm/reject findings   |
| `merge-validations`  | agent | Merge validator outputs, require ≥`validation_threshold` agreement |
| `fix-confirmed`      | agent | Fix ALL confirmed findings (fix-all-per-cycle rule)    |
| `verify-fixes`       | bash  | Compare confirmed findings against fix results         |
| `accumulate-history` | bash  | Append cycle findings to history for next cycle's SEEK |
| `recurse-decision`   | bash  | Decide CONTINUE or STOP based on cycle count and new findings |
| `final-summary`      | agent | Produce consolidated audit report                      |
| `self-improvement`   | agent | Review the audit process itself for workflow improvements |

### Loop Behavior

```
Cycle 1: seek → validate(×3) → merge → fix → verify → accumulate → decision
Cycle 2: seek(deeper) → validate(×3) → merge → fix → verify → accumulate → decision
Cycle 3+: seek(deepest) → validate(×3) → merge → fix → verify → accumulate → decision
```

- **Minimum cycles** always run regardless of findings.
- **Continue past minimum** if any high/critical findings or >3 medium findings
  emerged in the current cycle.
- **Stop** at `max_cycles` unconditionally.

## Bash Step Safety

> **[PLANNED — #3638]**: The heredoc safety patterns described below are
> planned fixes. Until implemented, the `recurse-decision` and
> `accumulate-history` steps may fail when template variables contain JSON
> with special characters.

### The Problem

Bash steps receive context variables via `{{variable}}` template interpolation.
When a variable contains JSON (e.g., `{{validated_findings}}`), the raw JSON
is pasted into the bash script. Characters like `"`, `{`, `}`, `$`, and
backticks can be interpreted as bash syntax, causing errors like:

```
/bin/bash: line 3: crates/: Is a directory
/bin/bash: line 14: json: command not found
```

### Safe Pattern: Environment Variables + Quoted Heredocs

Pass JSON via environment variables and use quoted heredocs (`<<'EOF'`) to
prevent bash expansion:

```yaml
- id: "verify-fixes"
  type: "bash"
  command: |
    export VALIDATED={{validated_findings}}
    export FIX_RESULTS={{fix_results}}

    python3 - <<'PYEOF'
    import json, os
    validated = json.loads(os.environ.get('VALIDATED', '{}'))
    # ... process safely in Python ...
    PYEOF
```

**Why this works:** The `<<'PYEOF'` (single-quoted delimiter) prevents bash
from expanding `$variables` and backticks inside the heredoc. The JSON travels
via environment variables, which handle special characters correctly.

### Unsafe Pattern: Direct Interpolation in Bash

```yaml
# UNSAFE — template variables expand as bash code
- id: "bad-step"
  type: "bash"
  command: |
    FINDINGS={{validated_findings}}  # JSON becomes bash syntax
    echo "$FINDINGS" | python3 -c "import sys, json; ..."
```

This fails because `{{validated_findings}}` expands to raw JSON like
`{"validated": [...]}`, which bash interprets as command groups.

### Safe Pattern: Temp Files for Complex Data

For variables too large for environment variables, write to temp files:

```yaml
- id: "recurse-decision"
  type: "bash"
  command: |
    _TMPFILE=$(mktemp)
    trap 'rm -f "$_TMPFILE"' EXIT
    cat > "$_TMPFILE" <<__EOF__
    {{validated_findings}}
    __EOF__
    python3 -c "
    import json
    with open('$_TMPFILE') as f:
        data = json.loads(f.read())
    "
```

## Invocation

Use `run_recipe_by_name()` from Python:

```python
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "quality-audit-cycle",
    user_context={
        "target_path": "src/amplihack",
        "repo_path": ".",
        "min_cycles": "3",
        "max_cycles": "6",
    },
    progress=True,
)
```

> **Do not use** `amplihack recipe execute` — this CLI form is deprecated.
> `run_recipe_by_name()` is the canonical invocation, consistent with
> `dev-orchestrator` and all other recipe workflows.

## See Also

- [How to Run a Quality Audit](../howto/run-quality-audit.md) — task-focused guide
- [SKILL.md](../../amplifier-bundle/skills/quality-audit/SKILL.md) — skill activation
  and detection categories
