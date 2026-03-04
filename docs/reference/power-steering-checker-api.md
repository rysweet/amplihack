# Power-Steering Checker — API Reference

> [Home](../index.md) > [Reference](README.md) > Power-Steering Checker API

Complete API reference for the `power_steering_checker` package.

---

## Package Overview

`power_steering_checker` is a Python package at:

```
.claude/tools/amplihack/hooks/power_steering_checker/
```

It is structured as five focused modules assembled by a re-exporting `__init__.py` that preserves full backward compatibility with the previous single-file layout.

---

## Public API (`__init__.py`)

```python
from power_steering_checker import (
    # Main entry points
    PowerSteeringChecker,
    check_session,
    is_disabled,

    # Data classes
    PowerSteeringResult,
    CheckerResult,
    ConsiderationAnalysis,
    PowerSteeringRedirect,

    # Feature flags (used by tests and integrations)
    SDK_AVAILABLE,
    _timeout,
)
```

### `check_session(transcript_lines, session_id, project_root=None)`

Module-level convenience wrapper. Creates a `PowerSteeringChecker` and calls `.check()`.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `transcript_lines` | `list[str]` | JSONL lines from the session transcript |
| `session_id` | `str` | Session identifier (alphanumeric, `_`, `-`, max 128 chars) |
| `project_root` | `Path \| None` | Project root; auto-detected from `.claude` marker if `None` |

**Returns** `PowerSteeringResult`

**Behavior**

- Returns `decision="approve"` if all blocker considerations pass.
- Returns `decision="block"` with `continuation_prompt` if any blocker fails.
- Always returns a result; never raises (fail-open design).

**Example**

```python
import sys
from pathlib import Path
from power_steering_checker import check_session

lines = Path(".claude/runtime/transcript.jsonl").read_text().splitlines()
result = check_session(lines, session_id="abc123")

if result.decision == "block":
    sys.stderr.write(result.continuation_prompt + "\n")
    sys.exit(2)
```

---

### `is_disabled(project_root=None)`

Returns `True` if power-steering is currently disabled for the project.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `project_root` | `Path \| None` | Project root; auto-detected if `None` |

**Returns** `bool`

**Behavior**

- Checks for a `.disabled` semaphore file in the runtime directory.
- Returns `False` on any error (fail-open).
- Logs a `WARNING` with stack trace if checker construction fails.

**Example**

```python
from power_steering_checker import is_disabled

if is_disabled():
    sys.exit(0)  # Skip check; power-steering is disabled
```

---

## `PowerSteeringChecker`

Main orchestrator class. Inherits from four mixins:

```
ConsiderationsMixin   → loads YAML, classifies sessions, runs individual checks
SdkCallsMixin         → parallel SDK analysis, timeout wrapper
ProgressTrackingMixin → semaphore files, redirect records, compaction context
ResultFormattingMixin → text output, continuation prompt generation
```

### Constructor

```python
checker = PowerSteeringChecker(project_root: Path | None = None)
```

Auto-detects `project_root` by walking up from `__file__` until a `.claude` directory is found (max 10 levels). Raises `ValueError` if not found.

### `checker.check(transcript_lines, session_id)`

Run all applicable considerations and return a decision.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `transcript_lines` | `list[str]` | Session transcript as JSONL lines |
| `session_id` | `str` | Session identifier |

**Returns** `PowerSteeringResult`

**Behavior**

1. Validates `session_id` format (see Security section).
2. Checks if already ran this session (idempotent via semaphore).
3. Classifies session type (SIMPLE / STANDARD / COMPLEX).
4. Runs all enabled considerations in parallel (up to `PARALLEL_TIMEOUT` seconds).
5. Formats and returns result.

---

## Data Classes

All data classes are defined in `considerations.py` and re-exported from `__init__.py`.

### `PowerSteeringResult`

Final decision from the checker.

```python
@dataclass
class PowerSteeringResult:
    decision: Literal["approve", "block"]
    reasons: list[str]
    continuation_prompt: str | None = None
    summary: str | None = None
    analysis: ConsiderationAnalysis | None = None
    is_first_stop: bool = False
    evidence_results: list = field(default_factory=list)
    compaction_context: Any = None
    considerations: list = field(default_factory=list)
```

| Field | Description |
|---|---|
| `decision` | `"approve"` or `"block"` |
| `reasons` | Human-readable reasons for the decision |
| `continuation_prompt` | Injected into the hook output when `decision="block"` |
| `summary` | One-line summary for logging |
| `analysis` | Full `ConsiderationAnalysis` for detailed inspection |
| `is_first_stop` | `True` if this is the first block in the session |
| `evidence_results` | Concrete evidence from Phase 1 checks |
| `compaction_context` | Compaction diagnostics (`CompactionContext` if available) |
| `considerations` | List of `CheckerResult` objects for visibility |

---

### `CheckerResult`

Result from a single consideration check.

```python
@dataclass
class CheckerResult:
    consideration_id: str
    satisfied: bool
    reason: str
    severity: Literal["blocker", "warning"]
    recovery_steps: list[str] = field(default_factory=list)
    executed: bool = True
```

| Field | Description |
|---|---|
| `consideration_id` | ID matching the entry in `considerations.yaml` |
| `satisfied` | `True` if the consideration was met |
| `reason` | Human-readable explanation |
| `severity` | `"blocker"` blocks the session; `"warning"` is advisory |
| `recovery_steps` | Ordered steps to resolve a failed check |
| `executed` | `False` if the check was skipped (not applicable for this session) |

**Properties**

```python
result.id  # Alias for consideration_id (backward compatibility)
```

---

### `ConsiderationAnalysis`

Aggregate of all check results for a session.

```python
@dataclass
class ConsiderationAnalysis:
    results: dict[str, CheckerResult] = field(default_factory=dict)
    failed_blockers: list[CheckerResult] = field(default_factory=list)
    failed_warnings: list[CheckerResult] = field(default_factory=list)
```

**Properties**

```python
analysis.has_blockers  # True if any blocker failed
```

**Methods**

```python
analysis.add_result(result: CheckerResult) -> None
# Adds result; automatically appends to failed_blockers or failed_warnings

analysis.group_by_category() -> dict[str, list[CheckerResult]]
# Groups failed considerations by display category
```

---

### `PowerSteeringRedirect`

Persistent record of a blocked session written to disk.

```python
@dataclass
class PowerSteeringRedirect:
    redirect_number: int
    timestamp: str               # ISO 8601
    failed_considerations: list[str]  # Consideration IDs
    continuation_prompt: str
    work_summary: str | None = None
```

---

## Feature Flags

These module-level booleans reflect whether optional dependencies are available. They are set at import time and do not change during execution.

| Flag | Module | Package Required | Purpose |
|---|---|---|---|
| `SDK_AVAILABLE` | `sdk_calls` | `claude_power_steering` | Enables SDK-based analysis |
| `EVIDENCE_AVAILABLE` | `sdk_calls` | `completion_evidence` | Enables Phase 1 evidence collection |
| `COMPACTION_AVAILABLE` | `progress_tracking` | `compaction_validator` | Enables compaction event detection |
| `TURN_STATE_AVAILABLE` | `result_formatting` | `power_steering_state` | Enables turn-aware state tracking |

```python
from power_steering_checker import SDK_AVAILABLE

if not SDK_AVAILABLE:
    # Running in fallback heuristic mode
    pass
```

---

## `_timeout` Context Manager

A SIGALRM-based timeout for wrapping external subprocess or SDK calls.

```python
from power_steering_checker import _timeout

with _timeout(25):
    result = subprocess.run(["gh", "pr", "view"], ...)
```

**Parameters**

| Name | Type | Description |
|---|---|---|
| `seconds` | `int` | Maximum duration before `TimeoutError` is raised |

**Raises** `TimeoutError` if the block exceeds `seconds`.

**Note**: Uses `signal.SIGALRM` — only works on Unix-like systems. Windows is not supported.

---

## `_write_with_retry(filepath, data, mode, max_retries)`

Retry-aware file writer that handles transient I/O errors from cloud-synced directories (iCloud, OneDrive, Dropbox).

```python
from power_steering_checker.progress_tracking import _write_with_retry

_write_with_retry(Path("/some/file.json"), data='{"key": "val"}')
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `filepath` | `Path` | — | Destination path |
| `data` | `str` | — | Content to write |
| `mode` | `str` | `"w"` | `"w"` (overwrite) or `"a"` (append) |
| `max_retries` | `int` | `3` | Retry attempts with exponential backoff |

**Raises** `OSError` after all retries exhausted.

**Backoff**: Starts at 0.1s, doubles on each retry (0.1s → 0.2s → 0.4s).

---

## Security

### Session ID Validation

`session_id` is validated against `r'^[a-zA-Z0-9_\-]{1,128}$'` before being interpolated into filesystem paths. Inputs containing path separators (`.`, `/`, `\`) or control characters are rejected with a `WARNING` log and the check is skipped (fail-open).

### Transcript Line Size Limit

Each JSONL line read from the transcript is checked against `MAX_LINE_BYTES` (10 MB). Lines exceeding this limit are skipped with a `WARNING` log. This prevents memory exhaustion from pathological inputs.

### Compaction Event Path Validation

The `saved_transcript_path` field read from compaction events is validated with `isinstance(str)` and a non-empty check before use. Malformed entries are skipped with a `WARNING` log.

### Semaphore File Creation

Semaphore files (`.{session_id}_completed`) are created atomically using `os.open(O_CREAT | O_EXCL | O_WRONLY, 0o600)`. This eliminates the TOCTOU race window that existed with the previous two-step create-then-chmod approach.

### Environment Variable Parsing

All `PSC_*` environment variables are parsed through a `_env_int(name, default)` helper. Non-numeric values log a `WARNING` and fall back to the default, preventing silent hook failure at import time.

---

## Error Handling Policy

| Scenario | Log Level | Behavior |
|---|---|---|
| Unexpected error in `check()` | `ERROR` + `exc_info=True` | Fail-open: returns `decision="approve"` |
| Parallel analysis failure | `ERROR` + `exc_info=True` | Fail-open: returns `decision="approve"` |
| Individual consideration error | `WARNING` + `exc_info=True` | Skip check; continue with others |
| `is_disabled()` construction error | `WARNING` + `exc_info=True` | Returns `False` (assume not disabled) |
| OSError on semaphore file | `WARNING` + `exc_info=True` | Continue without semaphore |
| Invalid session ID | `WARNING` | Skip check; treat as not-already-ran |
| Oversized transcript line | `WARNING` | Skip line; continue parsing |

---

## Related Documentation

- [Configuration Reference](power-steering-checker-configuration.md) — All `PSC_*` environment variables
- [Architecture Refactor Guide](../features/power-steering/architecture-refactor.md) — Module split rationale
- [Power-Steering Overview](../features/power-steering/README.md) — Feature overview
- [Customization Guide](../features/power-steering/customization-guide.md) — considerations.yaml reference
