# GhAwCompiler Reference

`GhAwCompiler` is a Python compiler frontend for validating
`.github/workflows/*.md` frontmatter files used by the GitHub Actions Workflow
(`gh-aw`) system. It replaces direct `yaml.safe_load()` parsing with a
structure-aware compiler that produces accurate, actionable diagnostics.

## Import

```python
from amplihack.workflows import GhAwCompiler, Diagnostic, compile_workflow
```

## Quick Start

```python
from amplihack.workflows import compile_workflow

with open(".github/workflows/issue-classifier.md") as f:
    content = f.read()

diagnostics = compile_workflow(content, filename="issue-classifier.md")

for d in diagnostics:
    print(f"[{d.severity.upper()}] {d.filename}:{d.line}:{d.col}: {d.message}")
```

## `compile_workflow()`

```python
def compile_workflow(content: str, filename: str = "<input>") -> list[Diagnostic]
```

Compiles a workflow file and returns a list of `Diagnostic` objects.

**Parameters**:

| Parameter  | Type  | Description                                             |
| ---------- | ----- | ------------------------------------------------------- |
| `content`  | `str` | Full text of the `.md` workflow file                    |
| `filename` | `str` | Filename for diagnostic messages (default: `"<input>"`) |

**Returns**: `list[Diagnostic]` — may be empty (no errors).

## `Diagnostic`

```python
@dataclass
class Diagnostic:
    severity: str      # "error" or "warning"
    message: str
    filename: str
    line: int          # 1-based line number
    col: int           # 1-based column number
```

## `GhAwCompiler`

```python
compiler = GhAwCompiler()
diagnostics = compiler.compile(content, filename="my-workflow.md")
```

Equivalent to `compile_workflow()` but useful when you want a persistent
compiler instance (e.g. to compile many files in a loop without re-importing).

## Diagnostic Rules

### P0 — YAML `on` key preservation

PyYAML's `safe_load` coerces the `on:` key to Python `True` (YAML 1.1 "Norway
problem"), producing false-positive "Missing required field 'on'" and
"Unrecognised field 'True'" errors.

`GhAwCompiler` uses `yaml.compose()` to access raw `key_node.value`, preserving
`"on"` as a string. `safe_load()` is never called on frontmatter keys.

### P1 — Line and column numbers

Every diagnostic includes the source position from the YAML compose node tree:

```
[ERROR] my-workflow.md:5:1: Unrecognised frontmatter field 'stirct' ...
```

### P1 — Typo escalation to error

When an unrecognised field name has a Levenshtein distance ≤ 2 from a known
field, severity is escalated from `"warning"` to `"error"`. This prevents
security-relevant fields (like `strict`) from being silently ignored when
misspelled.

Example: `stirct` (distance 2 from `strict`) → `[ERROR]` not `[WARN]`.

### P2 — Top-3 fuzzy suggestions

`difflib.get_close_matches(n=3, cutoff=0.5)` produces at most three ranked
candidates instead of dumping all 17 valid field names:

```
Did you mean: 'strict'?
```

### P2 — Valid-values guidance in required-field errors

When a required field is missing, the error message includes format examples:

```
[ERROR] Missing required field 'engine'. Valid values: claude, bash, node, python.
        Example: engine: claude
```

## Valid Frontmatter Fields

| Field             | Required | Type        | Description                                          |
| ----------------- | -------- | ----------- | ---------------------------------------------------- |
| `name`            | Yes      | string      | Workflow display name                                |
| `on`              | Yes      | trigger map | GitHub Actions trigger configuration                 |
| `engine`          | Yes      | string      | Execution engine: `claude`, `bash`, `node`, `python` |
| `description`     | No       | string      | Human-readable description                           |
| `timeout-minutes` | No       | integer     | Maximum runtime in minutes                           |
| `strict`          | No       | boolean     | Enable strict validation mode                        |
| `jobs`            | No       | map         | Job definitions                                      |
| `permissions`     | No       | map         | GitHub token permissions                             |
| `if`              | No       | expression  | Conditional execution                                |
| `imports`         | No       | list        | File imports                                         |
| `outputs`         | No       | map         | Workflow outputs                                     |
| `safe-outputs`    | No       | boolean     | Enable safe outputs mode                             |
| `skip-if-match`   | No       | expression  | Skip condition                                       |
| `bash`            | No       | string      | Inline bash command                                  |
| `tools`           | No       | list        | Tool configurations                                  |
| `tracker-id`      | No       | string      | External issue tracker reference                     |

## See Also

- [Workflow-to-Skills Migration Guide](../WORKFLOW_TO_SKILLS_MIGRATION.md)
- [Recent Fixes March 2026](../recipes/RECENT_FIXES_MARCH_2026.md#ghawcompiler-workflow-frontend-pr-3144)
