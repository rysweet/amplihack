---
title: Recipe Variable Expansion Reference
last_updated: 2026-03-14
---

# Recipe Variable Expansion Reference

This document explains how `{{var}}` template variables are expanded in amplihack
recipe YAML files.

## Contents

- [How Variable Expansion Works](#how-variable-expansion-works)
- [Automatic Quoting Normalisation](#automatic-quoting-normalisation)
- [Canonical Patterns](#canonical-patterns)
- [Agent Side-Effect Prevention](#agent-side-effect-prevention)
- [Related Documentation](#related-documentation)

---

## How Variable Expansion Works

The Rust recipe runner translates `{{var}}` placeholders into shell environment
variable references before executing each `command` block:

```
{{var}}  →  "$RECIPE_VAR_var"   (outside heredocs, with double quotes)
{{var}}  →  $RECIPE_VAR_var     (inside unquoted heredocs, no extra quotes)
```

The environment variable `RECIPE_VAR_var` is set by the runner before the
shell subprocess starts. The shell then expands it normally.

---

## Automatic Quoting Normalisation

The Python runner wrapper (`rust_runner.py`) automatically normalises common
quoting mistakes in recipe `command:` fields before invoking the Rust binary.
Recipe authors can write natural commands; the following patterns are fixed
transparently:

| Original (in YAML)         | Normalised to | Why |
|----------------------------|---------------|-----|
| `"{{var}}"`                | `{{var}}`     | Runner already adds double quotes; explicit quotes double them |
| `'{{var}}'`                | `{{var}}`     | Single quotes block runner's `$RECIPE_VAR_*` expansion |
| `<<'DELIM'` with `{{var}}` in body | `<<DELIM` | Single-quoted heredocs block shell expansion |

### Example: before and after normalisation

```yaml
# Written by author (any of these forms)
command: cd "{{repo_path}}"
command: printf '%s' '{{force_single_workstream}}'
command: |
  cat <<'EOF'
  Task: {{task_description}}
  EOF

# After automatic normalisation (what the Rust binary sees)
command: cd {{repo_path}}          # runner renders: cd "$RECIPE_VAR_repo_path"
command: printf '%s' {{force_single_workstream}}
command: |
  cat <<EOF
  Task: {{task_description}}       # runner expands to $RECIPE_VAR_task_description
  EOF
```

---

## Canonical Patterns

While normalisation handles the common mistakes, the canonical forms are
preferred in new recipes:

```yaml
# Paths and simple values — bare var, runner adds quotes
command: cd {{repo_path}}

# Heredocs — unquoted delimiter
command: |
  cat <<EOF
  Task: {{task_description}}
  EOF

# printf / subshell — bare var
command: |
  FLAG=$(printf '%s' {{force_single_workstream}})
```

Unquoted heredocs are safe because shell variable expansion is single-pass:
when `$RECIPE_VAR_task_description` expands, the resulting text is **not**
re-processed for shell metacharacters.

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
