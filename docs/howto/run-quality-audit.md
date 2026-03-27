# How to Run a Quality Audit

Run the `quality-audit-cycle` recipe to scan a codebase for quality issues with
escalating-depth SEEK/VALIDATE/FIX/RECURSE cycles.

## Prerequisites

- amplihack installed (`AMPLIHACK_HOME` set)
- Python 3.10+ with `amplihack` package importable
- Target repository checked out locally

## Basic Invocation

```python
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "quality-audit-cycle",
    user_context={
        "task_description": "Run quality audit on the payments module",
        "repo_path": ".",
        "target_path": "src/payments",
    },
    progress=True,
)
print(f"Recipe result: {result}")
```

> **Note:** Use `run_recipe_by_name()` — not `amplihack recipe execute`. The
> Python API is the canonical invocation path, matching how `dev-orchestrator`
> and all other recipes are launched.

## [PLANNED — Implementation Pending] Setting `repo_path`

> The `repo_path` context variable and `working_dir` integration described
> below are planned fixes for [#3638](https://github.com/rysweet/amplihack/issues/3638).
> Until implemented, agent steps may not resolve relative `target_path` values
> correctly.

The `repo_path` variable tells agent steps where the repository root is. Set it
so that `target_path` resolves relative to the repo:

```python
result = run_recipe_by_name(
    "quality-audit-cycle",
    user_context={
        "task_description": "Audit the crates directory",
        "repo_path": "/home/user/src/my-project",
        "target_path": "crates/",
    },
    progress=True,
)
```

When `repo_path` is set, each agent step's `working_dir` is set to that path,
giving agents file-system access to the target directory.

**Rules:**

| `repo_path`             | `target_path`   | Agent sees                           |
| ----------------------- | --------------- | ------------------------------------ |
| `.` (default)           | `src/payments`  | `./src/payments` from CWD            |
| `/home/user/src/myproj` | `crates/`       | `crates/` relative to `/home/…/myproj` |
| (omitted)               | absolute path   | Works, but agents may lack CWD context |

## Targeting a Subdirectory

Set `target_path` to audit a specific part of the codebase:

```python
result = run_recipe_by_name(
    "quality-audit-cycle",
    user_context={
        "target_path": "src/amplihack/fleet",
        "repo_path": ".",
        "min_cycles": "2",
        "max_cycles": "4",
    },
    progress=True,
)
```

## Filtering by Category

Limit the audit to specific issue categories:

```python
result = run_recipe_by_name(
    "quality-audit-cycle",
    user_context={
        "target_path": "src/amplihack",
        "repo_path": ".",
        "categories": "security,reliability,error_swallowing",
    },
    progress=True,
)
```

Available categories: `security`, `reliability`, `dead_code`, `silent_fallbacks`,
`error_swallowing`, `result_dropping`, `shell_anti_patterns`, `silent_truncation`,
`async_anti_patterns`, `config_divergence`, `validation_gaps`, `health_observability`,
`retry_anti_patterns`, `structural`, `hardcoded_limits`, `test_gaps`, `doc_gaps`,
`documentation`.

## Adjusting Cycle Limits

```python
result = run_recipe_by_name(
    "quality-audit-cycle",
    user_context={
        "target_path": "src/amplihack",
        "repo_path": ".",
        "min_cycles": "3",
        "max_cycles": "6",
        "severity_threshold": "high",
    },
    progress=True,
)
```

## Troubleshooting

### "target path does not exist"

The agent cannot find `target_path`. Likely causes:

1. **Missing `repo_path`** — [PLANNED] set `repo_path` to the repo root so
   agents resolve relative paths correctly.
2. **Relative path with wrong CWD** — ensure your shell's CWD is the repo root
   before calling `run_recipe_by_name()`, or use an absolute `target_path`.

### Bash step errors like `json: command not found`

Template variables (`{{validated_findings}}`) are being interpreted as bash
commands instead of being interpolated. This is a heredoc safety issue —
see the [recipe reference](../reference/quality-audit-cycle-recipe.md#bash-step-safety)
for details on the fix.

### Recipe completes but agents produce empty results

This is a **hollow success**. Check:

1. `repo_path` points to the actual repo root
2. `target_path` contains files the agents can read
3. The agent binary has access to file-reading tools

## See Also

- [Quality Audit Recipe Reference](../reference/quality-audit-cycle-recipe.md) — full
  context variable table and step-by-step reference
- [SKILL.md](../../amplifier-bundle/skills/quality-audit/SKILL.md) — skill activation
  triggers and detection categories
