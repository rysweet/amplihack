# power_steering_checker

Power-Steering session completion checker, refactored as a five-module Python package.

Replaced the monolithic `power_steering_checker.py` (5063 LOC) with a package of focused modules that are independently testable, import-time safe, and easier to maintain.

## Package Layout

```
hooks/power_steering_checker/
├── __init__.py            # Public API re-exports (backward compatible)
├── considerations.py      # Dataclasses + ConsiderationsMixin
├── sdk_calls.py           # SdkCallsMixin + timeout helper + SDK imports
├── progress_tracking.py   # ProgressTrackingMixin + state I/O + compaction
├── result_formatting.py   # ResultFormattingMixin + output generation
└── main_checker.py        # PowerSteeringChecker + check_session + is_disabled
```

## Import Compatibility

All existing imports continue to work unchanged:

```python
# These all work exactly as before
from power_steering_checker import PowerSteeringChecker
from power_steering_checker import check_session, is_disabled
from power_steering_checker import PowerSteeringResult, CheckerResult
from power_steering_checker import ConsiderationAnalysis, PowerSteeringRedirect
from power_steering_checker import SDK_AVAILABLE, _timeout
```

## Quick Start

```python
from power_steering_checker import check_session, is_disabled

# Check if disabled before doing any work
if is_disabled():
    sys.exit(0)

# Run a full check against the current session
result = check_session(transcript_lines, session_id)

if result.decision == "block":
    print(result.continuation_prompt)
    sys.exit(2)
```

## Module Responsibilities

### `considerations.py` — Data + Detection

Owns all dataclasses and the `ConsiderationsMixin` that loads and evaluates considerations.

```python
from power_steering_checker.considerations import (
    CheckerResult,          # Result from one consideration check
    ConsiderationAnalysis,  # Aggregate of all check results
    PowerSteeringRedirect,  # Record of a blocked session
    PowerSteeringResult,    # Final approve/block decision
    ConsiderationsMixin,    # Methods: _load_considerations_yaml, _classify_session, ...
)
```

### `sdk_calls.py` — External Calls + Timeouts

Owns Claude SDK integration, parallel async analysis, and the `_timeout` context manager.

```python
from power_steering_checker.sdk_calls import (
    SDK_AVAILABLE,      # True if claude_power_steering package present
    EVIDENCE_AVAILABLE, # True if completion_evidence package present
    CHECKER_TIMEOUT,    # Per-checker timeout in seconds (env: PSC_CHECKER_TIMEOUT)
    PARALLEL_TIMEOUT,   # Parallel execution budget (env: PSC_PARALLEL_TIMEOUT)
    _timeout,           # Context manager: with _timeout(25): ...
    analyze_consideration,  # SDK analysis function (None when SDK absent)
    SdkCallsMixin,      # Methods: _analyze_considerations_parallel, _check_single_*
)
```

### `progress_tracking.py` — State + File I/O

Owns semaphore files, redirect records, compaction context, and the `_write_with_retry` helper.

```python
from power_steering_checker.progress_tracking import (
    COMPACTION_AVAILABLE,   # True if compaction_validator package present
    CompactionContext,      # Real or placeholder compaction context class
    _write_with_retry,      # Retry-aware file writer for cloud-sync resilience
    ProgressTrackingMixin,  # Methods: _already_ran, _mark_complete, _load_results, ...
)
```

### `result_formatting.py` — Output Generation

Owns all text formatting. Pure transformation — no I/O, no external calls.

```python
from power_steering_checker.result_formatting import (
    TURN_STATE_AVAILABLE,         # True if power_steering_state package present
    DEFAULT_MAX_CONSECUTIVE_BLOCKS, # Fallback when TurnState unavailable
    ResultFormattingMixin,         # Methods: _format_results_text, _generate_*
)
```

### `main_checker.py` — Orchestration + Public API

Assembles the four mixins into `PowerSteeringChecker` and exposes module-level functions.

```python
from power_steering_checker.main_checker import (
    PowerSteeringChecker,  # Main class: call checker.check(transcript, session_id)
    check_session,         # Module-level convenience wrapper
    is_disabled,           # Returns True if .disabled file present
    MAX_TRANSCRIPT_LINES,  # Safety cap (env: PSC_MAX_TRANSCRIPT_LINES)
    MAX_ASK_USER_QUESTIONS,
    MIN_TESTS_PASSED_THRESHOLD,
)
```

## Configuration

All runtime thresholds are configurable via environment variables with safe defaults.
See [configuration reference](../../../../../docs/reference/power-steering-checker-configuration.md).

| Variable | Default | Description |
|---|---|---|
| `PSC_CHECKER_TIMEOUT` | `25` | Per-consideration timeout (seconds) |
| `PSC_PARALLEL_TIMEOUT` | `60` | Total parallel execution budget (seconds) |
| `PSC_MAX_TRANSCRIPT_LINES` | `50000` | Transcript size cap |
| `PSC_MAX_ASK_USER_QUESTIONS` | `3` | Max AskUserQuestion calls before flagging |
| `PSC_MIN_TESTS_PASSED_THRESHOLD` | `10` | Minimum passing tests |
| `PSC_MAX_CONSECUTIVE_BLOCKS` | `10` | Consecutive block limit (turn-state fallback) |

## Error Handling

Every `except Exception` block logs at `WARNING` level with `exc_info=True` so stack traces are preserved. Two top-level fail-open catches log at `ERROR`. The `is_disabled()` helper logs at `WARNING` if checker construction fails. No exception is silently swallowed.

## Related Documentation

- [API Reference](../../../../../docs/reference/power-steering-checker-api.md)
- [Configuration Reference](../../../../../docs/reference/power-steering-checker-configuration.md)
- [Architecture Migration Guide](../../../../../docs/features/power-steering/architecture-refactor.md)
- [Power-Steering Overview](../../../../../docs/features/power-steering/README.md)
