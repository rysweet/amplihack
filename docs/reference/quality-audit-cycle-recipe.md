# Quality Audit Cycle Recipe Reference

Reference for the `quality-audit-cycle` recipe
(`amplifier-bundle/recipes/quality-audit-cycle.yaml`), version 4.0.0.

## Context Variables

| Variable               | Default                        | Description                                                   |
| ---------------------- | ------------------------------ | ------------------------------------------------------------- |
| `target_path`          | `src/amplihack`                | Directory to audit                                            |
| `repo_path`            | `.`                            | Repository root; sets `working_dir` for agent steps           |
| `min_cycles`           | `3`                            | Minimum audit cycles (always run at least this many)          |
| `max_cycles`           | `6`                            | Maximum cycles (safety valve)                                 |
| `validation_threshold` | `2`                            | Minimum validators that must agree (out of 3)                 |
| `severity_threshold`   | `medium`                       | Minimum severity to report (`low`/`medium`/`high`/`critical`) |
| `module_loc_limit`     | `300`                          | Flag modules exceeding this LOC count                         |
| `fix_all_per_cycle`    | `true`                         | Must fix ALL confirmed findings before next cycle (#2842)     |
| `categories`           | (all)                          | Comma-separated category filter                               |
| `output_dir`           | `./eval_results/quality_audit` | Where to write audit output files                             |

### Internal State Variables

These are managed by the recipe loop and should not be set manually:

`audit_findings`, `validation_agent_1`, `validation_agent_2`, `validation_agent_3`,
`validated_findings`, `fix_results`, `fix_verification`,
`cycle_number`, `cycle_history`, `recurse_decision`, `summary`,
`self_improvement_results`

## Steps

| Step ID                | Type  | Purpose                                                            |
| ---------------------- | ----- | ------------------------------------------------------------------ |
| `seek`                 | agent | Scan codebase for quality issues (escalating depth)                |
| `validate-agent-1/2/3` | agent | Three independent validators confirm/reject findings               |
| `merge-validations`    | bash  | Merge validator outputs, require ≥`validation_threshold` agreement |
| `fix`                  | agent | Fix ALL confirmed findings (fix-all-per-cycle rule)                |
| `verify-fixes`         | bash  | Compare confirmed findings against fix results                     |
| `accumulate-history`   | bash  | Append cycle findings to history for next cycle's SEEK             |
| `recurse-decision`     | bash  | Decide CONTINUE or STOP based on cycle count and new findings      |
| `summary`              | agent | Produce consolidated audit report                                  |
| `self-improvement`     | agent | Review the audit process itself for workflow improvements          |

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

### The Problem

Bash steps receive context variables via `{{variable}}` template interpolation.
When a variable contains JSON (e.g., `{{validated_findings}}`), the raw JSON
is pasted into the bash script. Characters like `"`, `{`, `}`, `$`, and
backticks can be interpreted as bash syntax, causing errors like:

```
/bin/bash: line 3: crates/: Is a directory
/bin/bash: line 14: json: command not found
```

### Safe Pattern: Temp Files + Quoted Heredocs

Write JSON to temp files via single-quoted heredocs (`<<'EOF'`) so bash never
interprets the content, then read from the file in Python:

```yaml
- id: "verify-fixes"
  type: "bash"
  command: |
    _VALIDATED_TMPFILE=$(mktemp)
    _FIX_RESULTS_TMPFILE=$(mktemp)
    trap 'rm -f "$_VALIDATED_TMPFILE" "$_FIX_RESULTS_TMPFILE"' EXIT
    cat > "$_VALIDATED_TMPFILE" <<'__VALIDATED_EOF__'
    {{validated_findings}}
    __VALIDATED_EOF__
    cat > "$_FIX_RESULTS_TMPFILE" <<'__FIX_RESULTS_EOF__'
    {{fix_results}}
    __FIX_RESULTS_EOF__

    export VALIDATED_FILE="$_VALIDATED_TMPFILE"
    export FIX_RESULTS_FILE="$_FIX_RESULTS_TMPFILE"

    python3 - <<'PYEOF'
    import os
    from amplihack.utils.defensive import parse_llm_json
    with open(os.environ['VALIDATED_FILE']) as f:
        validated = parse_llm_json(f.read())
    # ... process safely in Python ...
    PYEOF
```

**Why this works:** The `<<'__VALIDATED_EOF__'` (single-quoted delimiter) prevents
bash from expanding `$variables` and backticks inside the heredoc. The JSON is
written to a temp file — never assigned to a shell variable — so special
characters like `{`, `}`, `$`, and backticks are inert. The `trap` ensures
cleanup on exit.

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

### Alternative: Inline Python via Quoted Heredoc

For simpler steps that only need one variable:

```yaml
- id: "recurse-decision"
  type: "bash"
  command: |
    _TMPFILE=$(mktemp)
    trap 'rm -f "$_TMPFILE"' EXIT
    cat > "$_TMPFILE" <<'__EOF__'
    {{validated_findings}}
    __EOF__

    python3 - <<'PYEOF'
    from amplihack.utils.defensive import parse_llm_json
    with open("'$_TMPFILE'") as f:
        data = parse_llm_json(f.read())
    PYEOF
```

> **Note:** The heredoc delimiter **must** be single-quoted (`<<'__EOF__'`).
> An unquoted delimiter (`<<__EOF__`) allows bash to expand `$` and backticks
> inside the heredoc, re-introducing the injection vulnerability.

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
