---
title: Recipe Variable Expansion Reference
last_updated: 2026-03-14
---

# Recipe Variable Expansion Reference

This document explains how `{{var}}` template variables are expanded in amplihack
recipe YAML files and the shell quoting rules that recipe authors must follow.

## Contents

- [How Variable Expansion Works](#how-variable-expansion-works)
- [Shell Quoting Rules](#shell-quoting-rules)
  - [Heredocs](#heredocs)
  - [Double-Quoting Variables](#double-quoting-variables)
  - [printf and echo](#printf-and-echo)
- [Common Mistakes](#common-mistakes)
- [Agent Side-Effect Prevention](#agent-side-effect-prevention)
- [Related Documentation](#related-documentation)

---

## How Variable Expansion Works

The Rust recipe runner translates `{{var}}` placeholders into shell environment
variable references before executing each `command` block:

```
{{var}}  →  $RECIPE_VAR_var
```

The environment variable `RECIPE_VAR_var` is set by the runner before the
shell subprocess starts. The shell then expands it normally.

**Python runner**: uses direct string interpolation (replaces `{{var}}` with
the value before execution). Shell quoting rules below do not apply to the
Python runner.

---

## Shell Quoting Rules

### Heredocs

**Rule**: Use unquoted heredocs (`<<EOF`) when the body contains `{{var}}`.
Single-quoted heredocs (`<<'EOF'`) block all shell expansion.

```yaml
# CORRECT — runner sets RECIPE_VAR_task_description; shell expands it
command: |
  cat <<EOF
  Task: $RECIPE_VAR_task_description
  EOF

# WRONG — single quotes block expansion; literal $RECIPE_VAR_task_description emitted
command: |
  cat <<'EOF'
  Task: {{task_description}}
  EOF
```

Unquoted heredocs are safe because shell variable expansion is single-pass.
When `$RECIPE_VAR_task_description` expands to user-supplied text, that text is
**not** re-processed for shell metacharacters.

### Double-Quoting Variables

**Rule**: Do **not** add your own double quotes around `{{var}}` in commands.
The Rust runner already wraps the expanded reference with double quotes.

```yaml
# CORRECT — runner renders: cd "$RECIPE_VAR_repo_path"
command: cd {{repo_path}}

# WRONG — runner renders: cd ""$RECIPE_VAR_repo_path""  (broken)
command: cd "{{repo_path}}"
```

The runner's automatic quoting is sufficient and handles paths with spaces.
Adding explicit double quotes produces doubled quote marks and breaks the
command.

### printf and echo

**Rule**: When using `printf` or a subshell assignment, use **double** quotes
around `{{var}}`, not single quotes.

```yaml
# CORRECT — shell expands $RECIPE_VAR_force_single_workstream inside double quotes
command: |
  FLAG=$(printf '%s' "{{force_single_workstream}}")

# WRONG — single quotes block expansion; literal text emitted
command: |
  FLAG=$(printf '%s' '{{force_single_workstream}}')
```

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `<<'EOF'` heredoc with `{{var}}` | Literal `$RECIPE_VAR_*` appears in output (issue bodies, PR descriptions, etc.) | Change to `<<EOF` |
| `"{{var}}"` in commands | Doubled quotes in rendered shell (`cd ""path""`) | Remove the surrounding double quotes |
| `'{{var}}'` in printf/assignments | Variable not expanded; condition checks fail | Use `"{{var}}"` |

---

## Agent Side-Effect Prevention

When writing agent prompts for classification or planning steps (e.g.,
`classify-and-decompose`), always add an explicit prohibition against
implementation:

```yaml
# In the agent prompt for classification/planning steps:
prompt: |
  Analyze the task and produce a structured orchestration plan.

  DO NOT implement, build, code, or make any changes to files.
  Your output must be a plan only.
```

Without this guard, a general-purpose agent may interpret "analyze and plan" as
permission to also implement, causing unintended repository mutations during the
classification phase.

---

## Related Documentation

- [Recipe Resilience](./RECIPE_RESILIENCE.md) — branch sanitization and
  sub-recipe recovery
- [Discoveries](./claude/context/DISCOVERIES.md) — recipe runner quoting
  patterns discovered during development
