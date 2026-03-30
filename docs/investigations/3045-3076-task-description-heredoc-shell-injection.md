# Investigation: Shell Injection via Unquoted `{{task_description}}` in Bash Steps

**Issues:** #3045, #3076
**Date:** 2026-03-12
**Status:** FIXED
**File:** `amplifier-bundle/recipes/default-workflow.yaml`

---

## Problem

The recipe runner substitutes `{{task_description}}` with the raw user-supplied string
**before** passing the assembled script to bash. Any bash metacharacter in the value
(`'`, `"`, `` ` ``, `$()`, `;`, `\n`, etc.) could break the shell command or allow
unintended command execution.

Example: a task description of `fix user's 'login' bug` would produce malformed bash:

```bash
# BROKEN — single quotes terminate the format string prematurely
ISSUE_TITLE=$(printf '%s' fix user's 'login' bug | tr ...)
```

Issue #3041 previously fixed one location (`step-04-setup-worktree`) using a
single-quoted heredoc. Issues #3045 and #3076 tracked the remaining 6 unprotected
bash steps.

---

## Root Cause

Template substitution happens at the recipe-runner level, before bash interprets the
script. Inline interpolation of user-controlled text into a shell script is a classic
shell-injection surface. The single-quoted heredoc pattern (`<<'EOFTASKDESC'`) prevents
bash from interpreting any metacharacter in the substituted value.

---

## Fix Pattern (established in #3041)

```bash
TASK_DESC=$(cat <<'EOFTASKDESC'
{{task_description}}
EOFTASKDESC
)
# then use "$TASK_DESC" everywhere in the step
```

The single-quoted delimiter (`'EOFTASKDESC'`) tells bash not to expand `$`, backticks,
or any other special syntax inside the heredoc body. YAML block-scalar (`|`) strips the
leading indentation, so the delimiter lands at column 0 as required by bash.

---

## Locations Fixed

| Step ID                        | Command block context        | Vulnerability pattern                                 |
| ------------------------------ | ---------------------------- | ----------------------------------------------------- |
| `step-00-workflow-preparation` | Summary print at end of step | `printf 'Task: %s\n' {{task_description}}`            |
| `step-03-create-issue`         | GitHub issue creation        | Two bare `printf '%s' {{task_description}}`           |
| `step-15-commit-push`          | Git commit title             | `{{task_description}}` inside nested `$()` subshell   |
| `step-16-create-draft-pr`      | Draft PR creation            | Two bare `printf '%s' {{task_description}}`           |
| `step-22b-final-status`        | Workflow completion summary  | `printf '=== Task: %s ===\n' {{task_description}}`    |
| `workflow-complete`            | JSON output step             | `export TASK_VAL=$(printf '%s' {{task_description}})` |

**Not changed:**

- `step-04-setup-worktree` — already fixed in #3041
- All `agent:` / `prompt:` steps — `{{task_description}}` there is markdown prose,
  not a shell command argument; no injection risk

---

## Verification

After the fix, the following grep returns zero bash-step violations:

```bash
python3 -c "
import re, sys
lines = open('amplifier-bundle/recipes/default-workflow.yaml').readlines()
violations = []
for i, line in enumerate(lines):
    if '{{task_description}}' not in line: continue
    if line.strip().startswith('#'): continue
    in_heredoc = any(\"<<'EOFTASKDESC'\" in lines[j] for j in range(max(0,i-5), i))
    if in_heredoc: continue
    step_type = None
    for j in range(i-1, max(0,i-300), -1):
        if '    type: \"bash\"' in lines[j]: step_type='bash'; break
        if '    agent:' in lines[j]: step_type='agent'; break
        if '  - id:' in lines[j]: break
    if step_type == 'bash':
        violations.append((i+1, line.rstrip()))
if violations:
    print('FAIL:', violations); sys.exit(1)
print('PASS: all bash steps heredoc-protected')
"
```

Expected output: `PASS: all bash steps heredoc-protected`

---

## Testing the Fix

A task description containing all common injection characters should produce no bash
syntax error in any of the 6 fixed steps:

```
fix user's "login" bug (it's \$BROKEN); see issue #1 \`whoami\`
```

---

## Related Issues

- #3041 — original heredoc fix for `step-04-setup-worktree` (established the pattern)
- #3045 — first follow-up tracking remaining unprotected steps
- #3076 — second follow-up (same class of vulnerability)
