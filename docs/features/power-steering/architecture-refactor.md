# Power-Steering Checker — Architecture Refactor

> [Home](../../index.md) > [Features](../README.md) > [Power-Steering](README.md) > Architecture Refactor

This document describes the split of `power_steering_checker.py` (5063 LOC) into the `power_steering_checker/` package, why each module boundary was drawn where it is, and how to work with the new structure.

---

## Why the Refactor

The original `power_steering_checker.py` had grown to 5063 lines across a single file. This made it:

- Difficult to navigate — unrelated concerns interleaved
- Slow to test — any test had to import the entire module
- Hard to reason about — import-time side effects not obviously scoped
- Risky to modify — changes anywhere could affect anything

The refactor splits the file along natural separation boundaries without changing any public behavior.

---

## Package Structure

```
hooks/power_steering_checker/
├── __init__.py             # Re-exports; backward-compatible public API
├── considerations.py       # Dataclasses + ConsiderationsMixin
├── sdk_calls.py            # SdkCallsMixin + _timeout + optional SDK imports
├── progress_tracking.py    # ProgressTrackingMixin + _write_with_retry + compaction
├── result_formatting.py    # ResultFormattingMixin + turn-state imports
└── main_checker.py         # PowerSteeringChecker + check_session + is_disabled
```

---

## Module Boundaries

### Why five modules, not six?

An earlier design considered a shared `utils.py` for `_timeout` and `_write_with_retry`. This was rejected:

- `_timeout` belongs in `sdk_calls.py` — it exists exclusively to wrap external subprocess/SDK calls
- `_write_with_retry` belongs in `progress_tracking.py` — both call sites are in `ProgressTrackingMixin` methods

Adding a utilities module would have required a circular-import-free design that complicated the dependency graph without providing any net benefit.

### Dataclass placement

All four dataclasses (`CheckerResult`, `ConsiderationAnalysis`, `PowerSteeringRedirect`, `PowerSteeringResult`) live in `considerations.py`. This is the stdlib-only module — no optional imports, no I/O, no side effects. Every other module can safely import from it without pulling in anything that might fail.

### Availability flags

Each flag lives in the module that owns its import:

| Flag                   | Module              | Controls                            |
| ---------------------- | ------------------- | ----------------------------------- |
| `SDK_AVAILABLE`        | `sdk_calls`         | `claude_power_steering` integration |
| `EVIDENCE_AVAILABLE`   | `sdk_calls`         | `completion_evidence` integration   |
| `COMPACTION_AVAILABLE` | `progress_tracking` | `compaction_validator` integration  |
| `TURN_STATE_AVAILABLE` | `result_formatting` | `power_steering_state` integration  |

### Configurable constants placement

Constants are placed in the module where their value is consumed:

| Constant                         | Module              | Consumed by                               |
| -------------------------------- | ------------------- | ----------------------------------------- |
| `CHECKER_TIMEOUT`                | `sdk_calls`         | `_timeout()` calls inside `SdkCallsMixin` |
| `PARALLEL_TIMEOUT`               | `sdk_calls`         | `asyncio.wait_for()` in parallel analysis |
| `MAX_TRANSCRIPT_LINES`           | `main_checker`      | Transcript truncation in `check()`        |
| `MAX_ASK_USER_QUESTIONS`         | `main_checker`      | AskUserQuestion count check               |
| `MIN_TESTS_PASSED_THRESHOLD`     | `main_checker`      | Local testing check                       |
| `DEFAULT_MAX_CONSECUTIVE_BLOCKS` | `result_formatting` | Fallback when TurnState unavailable       |

---

## Import Dependency Graph

The dependency graph is strictly acyclic:

```
considerations.py       → stdlib only (dataclasses, typing, pathlib, ...)
         ↑
sdk_calls.py            → from .considerations import CheckerResult, ConsiderationAnalysis
         ↑
progress_tracking.py    → from .considerations import PowerSteeringResult, CheckerResult, ...
         ↑
result_formatting.py    → from .considerations import ConsiderationAnalysis, PowerSteeringResult
         ↑
main_checker.py         → from .considerations import (all)
                        → from .sdk_calls import SDK_AVAILABLE, _timeout, SdkCallsMixin, ...
                        → from .progress_tracking import ProgressTrackingMixin, _write_with_retry, ...
                        → from .result_formatting import ResultFormattingMixin, ...
         ↑
__init__.py             → re-exports from all five modules
```

No module imports from a module that is at the same level or below in this chain.

---

## Backward Compatibility

All imports that worked against the original `power_steering_checker.py` continue to work against the package `__init__.py`:

```python
# Before (single file)
from power_steering_checker import PowerSteeringChecker
from power_steering_checker import check_session, is_disabled
from power_steering_checker import PowerSteeringResult, CheckerResult
from power_steering_checker import SDK_AVAILABLE, _timeout

# After (package) — identical, no changes needed
from power_steering_checker import PowerSteeringChecker
from power_steering_checker import check_session, is_disabled
from power_steering_checker import PowerSteeringResult, CheckerResult
from power_steering_checker import SDK_AVAILABLE, _timeout
```

Test files using `sys.path` insertion to import `power_steering_checker` continue to work because the package `__init__.py` re-exports all previously public symbols.

---

## Non-Functional Improvements

The refactor also fixed the following issues that were unrelated to the module split:

### Broad `except Exception` blocks

All 19 `except Exception` blocks now:

1. Capture the exception as `e`.
2. Log at `WARNING` (or `ERROR` for two top-level fail-open catches) with `exc_info=True`.
3. Never silently swallow exceptions.

Before:

```python
except Exception:
    pass  # Line 5020 — is_disabled() silent failure
```

After:

```python
except Exception as e:
    logger.warning(
        "PowerSteeringChecker creation failed, assuming not disabled: %s",
        e,
        exc_info=True,
    )
    return False
```

### Hardcoded literals replaced with named constants

Six inline magic numbers replaced with configurable named constants:

| Before                                                | After                            | Env Variable                     |
| ----------------------------------------------------- | -------------------------------- | -------------------------------- |
| `int(os.getenv("PSC_CHECKER_TIMEOUT", "25"))` inline  | `CHECKER_TIMEOUT`                | `PSC_CHECKER_TIMEOUT`            |
| `int(os.getenv("PSC_PARALLEL_TIMEOUT", "60"))` inline | `PARALLEL_TIMEOUT`               | `PSC_PARALLEL_TIMEOUT`           |
| Literal `50000`                                       | `MAX_TRANSCRIPT_LINES`           | `PSC_MAX_TRANSCRIPT_LINES`       |
| Literal `3` (ask_user count)                          | `MAX_ASK_USER_QUESTIONS`         | `PSC_MAX_ASK_USER_QUESTIONS`     |
| Literal `10` (tests threshold)                        | `MIN_TESTS_PASSED_THRESHOLD`     | `PSC_MIN_TESTS_PASSED_THRESHOLD` |
| Literal `10` (consecutive blocks)                     | `DEFAULT_MAX_CONSECUTIVE_BLOCKS` | `PSC_MAX_CONSECUTIVE_BLOCKS`     |

### Safe environment variable parsing

All `PSC_*` variables are now parsed via `_env_int(name, default)` which logs a warning and returns the default if the value is non-numeric. This prevents a misconfigured environment from silently disabling the entire hook at import time.

---

## Security Improvements

The refactor also addressed six security issues identified during analysis. See the [API Reference security section](../../reference/power-steering-checker-api.md#security) for complete details.

| Issue                                  | Fix                                                                     |
| -------------------------------------- | ----------------------------------------------------------------------- |
| Session ID path traversal              | Regex validation `r'^[a-zA-Z0-9_\-]{1,128}$'` before path interpolation |
| Non-numeric env vars crashing import   | `_env_int()` helper with fallback                                       |
| Oversized JSON lines exhausting memory | 10 MB per-line size guard                                               |
| Malformed compaction event paths       | `isinstance(str)` + non-empty check                                     |
| Silent OSError swallowing              | Logged `WARNING` with `exc_info=True`                                   |
| TOCTOU on semaphore creation           | Atomic `os.open(O_CREAT \| O_EXCL, 0o600)`                              |

---

## Working with the New Structure

### Adding a method to an existing mixin

1. Identify which module owns the concern (see Module Boundaries above).
2. Add the method to the corresponding `*Mixin` class.
3. If the method uses constants or imports from other modules, add them at the top of that module.
4. No changes to `__init__.py` are needed for private methods.

### Adding a new public symbol

1. Implement in the appropriate module.
2. Add the import to `__init__.py`.
3. Add to `__all__` in `__init__.py`.

### Adding a new configurable constant

1. Place in the module where it is consumed (see Constants Placement above).
2. Use the pattern:

   ```python
   MY_CONSTANT = int(os.getenv("PSC_MY_CONSTANT", "default_value"))
   ```

   Or, if the module already has `_env_int`:

   ```python
   MY_CONSTANT = _env_int("PSC_MY_CONSTANT", default_value)
   ```

3. Document in [Configuration Reference](../../reference/power-steering-checker-configuration.md).

### Writing tests

Each module can be tested in isolation by importing only that module. Tests that previously required the full `PowerSteeringChecker` class can now test individual mixins directly:

```python
# Test considerations logic without instantiating PowerSteeringChecker
from power_steering_checker.considerations import ConsiderationsMixin

class TestChecker(ConsiderationsMixin):
    """Minimal test fixture."""
    def __init__(self):
        self.considerations = [...]

checker = TestChecker()
result = checker._classify_session(transcript_lines)
assert result == "STANDARD"
```

---

## Migration from Single-File to Package

This section is for maintainers who need to understand how the split was performed, or who need to backport a change from an older single-file checkout.

### File mapping

| Original line range          | Destination module     |
| ---------------------------- | ---------------------- |
| Dataclasses (top)            | `considerations.py`    |
| `ConsiderationsMixin`        | `considerations.py`    |
| `_timeout()` context manager | `sdk_calls.py`         |
| `SdkCallsMixin`              | `sdk_calls.py`         |
| `_write_with_retry()`        | `progress_tracking.py` |
| Compaction import block      | `progress_tracking.py` |
| `ProgressTrackingMixin`      | `progress_tracking.py` |
| `ResultFormattingMixin`      | `result_formatting.py` |
| `PowerSteeringChecker` class | `main_checker.py`      |
| `check_session()`            | `main_checker.py`      |
| `is_disabled()`              | `main_checker.py`      |
| `if __name__ == "__main__":` | `main_checker.py`      |

### What was not moved

Nothing was removed, renamed, or reordered beyond what is documented above. The logic is identical to the original file at the same version.

---

## Related Documentation

- [API Reference](../../reference/power-steering-checker-api.md) — Public API
- [Configuration Reference](../../reference/power-steering-checker-configuration.md) — Environment variables
- [Power-Steering Overview](README.md) — Feature overview
- [Troubleshooting](troubleshooting.md) — Common issues
