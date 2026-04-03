# Lock Tool Session ID Sanitization

> [Home](../index.md) > [Security](./README.md) > Lock Session ID Sanitization

Security hardening for the lock tool and stop hook: session identifiers are
sanitized before they are used as filesystem path components or written into
lock-file metadata, preventing path-traversal and metadata-injection attacks.

## Contents

- [Problem Solved](#problem-solved)
- [Sanitization Rules](#sanitization-rules)
- [API Reference](#api-reference)
  - [\_sanitize_session_id](#_sanitize_session_id)
- [Where Sanitization Is Applied](#where-sanitization-is-applied)
- [Security Invariants](#security-invariants)
- [Error Handling and Fallback](#error-handling-and-fallback)
- [Testing](#testing)
- [Related](#related)

---

## Problem Solved

The lock tool stores the current `AMPLIHACK_SESSION_ID` in lock-file metadata
so that a stop hook can distinguish its own lock from a stale lock left by a
crashed session. Two attack surfaces existed:

| Attack                 | Mechanism                                                                | Example payload                   |
| ---------------------- | ------------------------------------------------------------------------ | --------------------------------- |
| **Path traversal**     | `session_id` used as a directory name when constructing the counter path | `../../etc/cron.d/evil`           |
| **Metadata injection** | `session_id` written verbatim as a value in the key-value lock file      | `myid\nsession_id=attacker_value` |

Both attack surfaces are now closed by a single sanitization helper applied on
every write path and validated on every read path.

---

## Sanitization Rules

```
allowed characters: A–Z  a–z  0–9  _  -
replacement:        any other byte → _
empty guard:        if session_id is falsy → "unknown"
hard rejects (read path only):  values containing / or ..
```

The transformation is idempotent — sanitizing an already-clean ID returns it
unchanged.

```python
import re

def _sanitize_session_id(session_id: str | None) -> str:
    """Return a filesystem-safe, injection-free version of session_id."""
    if not session_id:
        return "unknown"
    return re.sub(r"[^A-Za-z0-9_\-]", "_", session_id)
```

---

## API Reference

### `_sanitize_session_id`

```python
from amplihack.tools.lock_tool import _sanitize_session_id

safe_id = _sanitize_session_id(raw_session_id)
```

| Parameter    | Type          | Description                                                 |
| ------------ | ------------- | ----------------------------------------------------------- |
| `session_id` | `str \| None` | Raw value from `AMPLIHACK_SESSION_ID` or lock-file metadata |

**Returns**: `str` — sanitized identifier, guaranteed to contain only
`[A-Za-z0-9_-]` and never be empty.

**Raises**: nothing — all edge cases return `"unknown"`.

**Examples**:

```python
_sanitize_session_id("my-session_01")      # → "my-session_01"  (unchanged)
_sanitize_session_id("../../etc/passwd")   # → "______etc_passwd"
_sanitize_session_id("abc\nid=evil")       # → "abc_id_evil"
_sanitize_session_id("   ")               # → "___"
_sanitize_session_id("")                   # → "unknown"
_sanitize_session_id(None)                 # → "unknown"
```

---

## Where Sanitization Is Applied

Sanitization is applied consistently on both write and read paths so that
counter directories named with sanitized IDs are found correctly even after
the sanitization was introduced mid-flight.

### `lock_tool.py` (canonical — two copies kept in sync)

| Function               | Action                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------- |
| `create_lock()`        | Sanitizes `session_id` before writing `session_id=<value>` into lock metadata         |
| `read_lock_metadata()` | Rejects any value containing `/` or `..`; returns `None` to trigger TTL-only recovery |

### `stop.py` (stop hook)

| Function                      | Action                                                                                        |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| `_increment_lock_counter()`   | Sanitizes `session_id` before constructing the counter directory path                         |
| `_get_lock_recovery_reason()` | Sanitizes both the stored and live session IDs before comparing; rejects malformed stored IDs |

### `_copilot_stop_handler_impl.py` (Python package mirror)

Mirrors the same sanitization as `stop.py` so that Python package consumers
and standalone hook consumers behave identically. Any change to either file
must be reflected in the other.

---

## Security Invariants

The following invariants must never be broken:

1. **No path separator** — the sanitized session ID never contains `/` or `\`.
2. **No newline** — the sanitized value never contains `\n`, `\r`, or other
   control characters, preventing metadata file corruption.
3. **Non-empty** — the sanitized value is never an empty string; unknown
   sessions fall back to `"unknown"`.
4. **Lock file permissions unchanged** — `os.O_CREAT | os.O_EXCL | os.O_WRONLY`
   with mode `0o600` remain in force; sanitization does not relax permissions.
5. **No `shell=True`** — no subprocess call in the lock/stop stack uses
   `shell=True`; this is validated by static analysis and must remain absent.
6. **TTL recovery preserved** — when `AMPLIHACK_SESSION_ID` is unset the lock
   tool falls back to TTL-only recovery without error.

---

## Error Handling and Fallback

```
┌─────────────────────────────────────────────────────┐
│ create_lock()                                        │
│   session_id = os.environ.get("AMPLIHACK_SESSION_ID")│
│   if session_id:                                     │
│       safe_id = _sanitize_session_id(session_id)     │
│       write "session_id=<safe_id>" to lock file      │
│   else:                                              │
│       omit session_id line → TTL-only recovery       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ read_lock_metadata() (read path guard)               │
│   raw = parse_value("session_id", lock_file)         │
│   if "/" in raw or ".." in raw:                      │
│       log warning, return None  (TTL fallback)       │
│   return raw                                         │
└─────────────────────────────────────────────────────┘
```

If the stored `session_id` is rejected on read, the lock tool falls back to
TTL-based stale-lock detection. The lock is not silently ignored — it is still
subject to the configured `AMPLIHACK_LOCK_TTL_SECONDS`.

---

## Testing

Tests covering the sanitization are spread across four files:

| File                                                             | What it tests                                                                                                                                    |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tests/test_lock_unlock.py`                                      | Path-traversal and newline-injection inputs to `create_lock()`; read-path rejection of `/` and `..` values                                       |
| `.claude/tools/amplihack/hooks/tests/test_stop_state_machine.py` | `_increment_lock_counter()` path construction with adversarial session IDs; `_get_lock_recovery_reason()` metadata comparison after sanitization |
| `tests/hooks/test_copilot_stop_handler.py`                       | Mirror parity: identical sanitization behaviour in `_copilot_stop_handler_impl.py`                                                               |
| `tests/outside_in/test_stop_hook_safety_valve_e2e.py`            | End-to-end: adversarial `AMPLIHACK_SESSION_ID` does not escape the session counter directory                                                     |

Run all sanitization-related tests:

```bash
pytest tests/test_lock_unlock.py \
       .claude/tools/amplihack/hooks/tests/test_stop_state_machine.py \
       tests/hooks/test_copilot_stop_handler.py \
       tests/outside_in/test_stop_hook_safety_valve_e2e.py \
       -v -k "sanitiz or traversal or injection or session_id"
```

---

## Related

- [Power Steering File Locking](./power-steering-file-locking.md) — lock
  acquisition, timeout, and fail-open behaviour
- [Security Recommendations](../SECURITY_RECOMMENDATIONS.md) — input validation
  patterns used across the codebase
- [Token Sanitization Guide](./TOKEN_SANITIZATION_GUIDE.md) — analogous
  sanitization for API tokens in log output
- Issues [#3960](https://github.com/rysweet/amplihack/issues/3960) and
  [#3983](https://github.com/rysweet/amplihack/issues/3983) — originating bug
  reports
- PR [#4143](https://github.com/rysweet/amplihack/pull/4143) — implementation

---

**Metadata**

| Field         | Value                                                           |
| ------------- | --------------------------------------------------------------- |
| Status        | Planned / PR #4143                                              |
| Issues        | #3960, #3983                                                    |
| PR            | #4143                                                           |
| Files changed | `lock_tool.py` (×2), `stop.py`, `_copilot_stop_handler_impl.py` |
| Python        | 3.8+                                                            |
| Dependencies  | `re` (stdlib only)                                              |
