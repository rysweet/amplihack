# Power-Steering Checker — Configuration Reference

> [Home](../index.md) > [Reference](README.md) > Power-Steering Checker Configuration

All runtime constants in the `power_steering_checker` package can be overridden with environment variables. This reference documents every variable, its default, the module that owns it, and the behavior when set to an invalid value.

---

## Quick Reference

| Variable | Default | Module | Description |
|---|---|---|---|
| `PSC_CHECKER_TIMEOUT` | `25` | `sdk_calls` | Per-consideration timeout (seconds) |
| `PSC_PARALLEL_TIMEOUT` | `60` | `sdk_calls` | Total parallel execution budget (seconds) |
| `PSC_MAX_TRANSCRIPT_LINES` | `50000` | `main_checker` | Transcript size cap (lines) |
| `PSC_MAX_ASK_USER_QUESTIONS` | `3` | `main_checker` | AskUserQuestion call limit |
| `PSC_MIN_TESTS_PASSED_THRESHOLD` | `10` | `main_checker` | Minimum passing tests |
| `PSC_MAX_CONSECUTIVE_BLOCKS` | `10` | `result_formatting` | Consecutive block limit (turn-state fallback) |

All variables are **optional**. Omitting them uses the default shown above.

---

## Timeout Variables

### `PSC_CHECKER_TIMEOUT`

**Default**: `25`
**Module**: `sdk_calls.py` as `CHECKER_TIMEOUT`
**Units**: seconds

Per-consideration timeout. Each individual checker (e.g., `_check_ci_status`, `_check_todos_complete`) is allowed at most this many seconds to complete. If it exceeds the limit, a `TimeoutError` is raised and the check is treated as not-satisfied.

**Timeout hierarchy**:

```
HOOK_TIMEOUT (120s)        ← hard limit imposed by Claude Code framework
  └── PARALLEL_TIMEOUT (60s)  ← PSC_PARALLEL_TIMEOUT — total budget for all checks
        └── CHECKER_TIMEOUT (25s) ← PSC_CHECKER_TIMEOUT — per-check budget
```

**Tuning guidelines**:

| Situation | Recommended value |
|---|---|
| Slow network (gh CLI latency > 5s) | `40` |
| CI environment with fast network | `15` |
| Debug / local development | `60` |

**Example**:

```bash
export PSC_CHECKER_TIMEOUT=40
```

---

### `PSC_PARALLEL_TIMEOUT`

**Default**: `60`
**Module**: `sdk_calls.py` as `PARALLEL_TIMEOUT`
**Units**: seconds

Total execution budget for the parallel analysis phase. All 21 checks run concurrently; this timeout bounds the entire batch.

Normal execution runs in 15–20 seconds. The 60-second default provides a buffer for slow network conditions while remaining safely under the 120-second hook timeout.

**Constraint**: Must be less than the Claude Code hook timeout (120s).

**Example**:

```bash
export PSC_PARALLEL_TIMEOUT=45
```

---

## Transcript Variables

### `PSC_MAX_TRANSCRIPT_LINES`

**Default**: `50000`
**Module**: `main_checker.py` as `MAX_TRANSCRIPT_LINES`
**Units**: lines

Maximum number of lines read from the session transcript. Lines beyond this limit are silently dropped. This prevents memory exhaustion when a very long session transcript is passed to the checker.

**Security note**: In addition to this line count limit, each individual line is checked against a 10 MB per-line size limit (`MAX_LINE_BYTES` in `progress_tracking.py`). Both guards must be satisfied.

**Example**:

```bash
# Reduce for memory-constrained environments
export PSC_MAX_TRANSCRIPT_LINES=20000

# Increase for very long sessions (ensure adequate RAM)
export PSC_MAX_TRANSCRIPT_LINES=100000
```

---

## Quality Threshold Variables

### `PSC_MAX_ASK_USER_QUESTIONS`

**Default**: `3`
**Module**: `main_checker.py` as `MAX_ASK_USER_QUESTIONS`
**Units**: count

Maximum number of `AskUserQuestion` tool invocations before the checker flags the session as over-questioning. Sessions that repeatedly ask the user instead of executing are blocked.

**Example**:

```bash
# Allow more questions in exploratory sessions
export PSC_MAX_ASK_USER_QUESTIONS=5
```

---

### `PSC_MIN_TESTS_PASSED_THRESHOLD`

**Default**: `10`
**Module**: `main_checker.py` as `MIN_TESTS_PASSED_THRESHOLD`
**Units**: count

Minimum number of test cases that must pass for the local testing check to be considered satisfied. Exists to distinguish meaningful test runs from trivial smoke tests.

**Example**:

```bash
# Lower for projects with small test suites
export PSC_MIN_TESTS_PASSED_THRESHOLD=3

# Raise for large projects to ensure thorough test coverage
export PSC_MIN_TESTS_PASSED_THRESHOLD=25
```

---

### `PSC_MAX_CONSECUTIVE_BLOCKS`

**Default**: `10`
**Module**: `result_formatting.py` as `DEFAULT_MAX_CONSECUTIVE_BLOCKS`
**Units**: count

Fallback maximum consecutive block count used when `power_steering_state` is unavailable (`TURN_STATE_AVAILABLE=False`). When turn-state tracking is available, this constant is not used — the actual turn state value takes precedence.

**Example**:

```bash
export PSC_MAX_CONSECUTIVE_BLOCKS=5
```

---

## Invalid Value Behavior

All `PSC_*` variables are parsed through the `_env_int(name, default)` helper. If a variable is set to a non-numeric string, the helper:

1. Logs a `WARNING` with the variable name and the invalid value.
2. Returns the default value.
3. Continues — the hook is not disabled.

**Example**:

```bash
export PSC_CHECKER_TIMEOUT=fast  # Non-numeric

# Results in:
# WARNING: PSC_CHECKER_TIMEOUT='fast' is not a valid integer; using default 25
```

This design ensures that a misconfigured environment variable never silently disables power-steering.

---

## Setting Variables

### Per-Project (`.env` file)

Not directly supported; use a shell wrapper or configure in your hook invocation.

### In `settings.json` hook command

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "PSC_CHECKER_TIMEOUT=40 PSC_PARALLEL_TIMEOUT=90 python .claude/tools/amplihack/hooks/stop_power_steering.py"
      }]
    }]
  }
}
```

### In shell profile

```bash
# ~/.bashrc or ~/.zshrc
export PSC_CHECKER_TIMEOUT=30
export PSC_MAX_TRANSCRIPT_LINES=30000
```

### Per-Run (inline)

```bash
PSC_CHECKER_TIMEOUT=40 amplihack claude
```

---

## Defaults Rationale

| Variable | Default | Rationale |
|---|---|---|
| `PSC_CHECKER_TIMEOUT=25` | Per-check budget that exceeds `gh` CLI network latency (100–500ms) by a wide margin while leaving room for the parallel budget. |
| `PSC_PARALLEL_TIMEOUT=60` | Roughly 3× median execution time (15–20s), providing a buffer for slow checks without approaching the 120s hook limit. |
| `PSC_MAX_TRANSCRIPT_LINES=50000` | Covers sessions up to ~50 hours of activity. At ~1 line/second average, 50k lines ≈ 14 hours. |
| `PSC_MAX_ASK_USER_QUESTIONS=3` | Based on amplihack usage data: sessions asking more than 3 questions before executing tend to be stalling. |
| `PSC_MIN_TESTS_PASSED_THRESHOLD=10` | Empirically derived: test suites with fewer than 10 passing tests rarely provide meaningful coverage evidence. |
| `PSC_MAX_CONSECUTIVE_BLOCKS=10` | Fallback only — the real threshold comes from `TurnStateManager` when available. |

---

## Related Documentation

- [API Reference](power-steering-checker-api.md) — Full package API
- [Architecture Refactor Guide](../features/power-steering/architecture-refactor.md) — Module split and constant placement
- [Troubleshooting](../features/power-steering/troubleshooting.md) — Common configuration issues
