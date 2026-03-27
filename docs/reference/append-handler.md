# AppendHandler Reference

`AppendHandler` writes agent output to timestamped files on disk. It is the persistence layer used by post-session hooks and batch recipe runs to capture results for later inspection.

## Contents

- [Overview](#overview)
- [AppendResult](#appendresult)
- [Filename Format](#filename-format)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)
- [API](#api)

---

## Overview

```python
from amplihack.append_handler import AppendHandler, AppendResult
```

`AppendHandler` writes one file per append call. Files are created atomically using `os.open()` with `O_CREAT | O_WRONLY | O_EXCL` to prevent overwriting existing output. The caller receives an `AppendResult` describing the outcome.

---

## AppendResult

`AppendResult` is a dataclass describing a single append operation:

```python
@dataclass
class AppendResult:
    success: bool
    file_path: str | None        # Absolute path of the file written, or None on failure
    bytes_written: int           # 0 on failure
    error: str | None            # Error message string, or None on success
```

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | `True` if the file was written without error. |
| `file_path` | `str \| None` | Absolute path of the written file. `None` if `success` is `False`. |
| `bytes_written` | `int` | Number of bytes written. `0` on failure. |
| `error` | `str \| None` | Human-readable error description. `None` on success. |

**Checking the result:**

```python
from amplihack.append_handler import AppendHandler

handler = AppendHandler(output_dir="~/.amplihack/.claude/runtime/output")
result = handler.append("Agent completed task successfully.\n\nSummary: 3 files modified.")

if result.success:
    print(f"Saved {result.bytes_written} bytes to {result.file_path}")
else:
    print(f"Failed to save: {result.error}")
```

---

## Filename Format

Each file is named with a timestamp derived from the moment `append()` is called:

```
YYYYMMDD_HHMMSS_ffffff.txt
```

Where `ffffff` is microseconds (6 digits), providing sub-second uniqueness even under rapid sequential calls.

**Examples:**

```
20260312_143022_483921.txt
20260312_143022_501847.txt   # same second, different microsecond
```

This format sorts lexicographically in chronological order, which simplifies log browsing with standard shell tools:

```bash
ls ~/.amplihack/.claude/runtime/output/ | tail -5
# 20260312_140011_002341.txt
# 20260312_143022_483921.txt
# 20260312_143022_501847.txt
# 20260312_151300_119204.txt
# 20260312_162500_883412.txt
```

> **Note:** Prior to v0.9.2, timestamps used `%Y%m%d_%H%M%S` (no microseconds). Files from old runs keep their original names; the new format is used only for files written by v0.9.2 and later.

---

## Usage Examples

### Write a session summary

```python
from amplihack.append_handler import AppendHandler

handler = AppendHandler(output_dir="~/.amplihack/.claude/runtime/output")

summary = """
Session complete.

Tasks completed: 3
Files modified: auth.py, tests/test_auth.py, README.md
""".strip()

result = handler.append(summary)
print(f"Written to: {result.file_path}")
# Written to: /home/user/.amplihack/.claude/runtime/output/20260312_143022_483921.txt
```

### Persist all recipe step outputs

```python
from amplihack.append_handler import AppendHandler
from amplihack.recipes.runner import RecipeRunner

runner = RecipeRunner()
handler = AppendHandler(output_dir="./run-logs")
recipe_result = runner.run("default-workflow", {"task_description": "add caching layer"})

for step in recipe_result.step_results:
    if step.output:
        result = handler.append(f"# {step.step_name}\n\n{step.output}")
        print(f"Step {step.step_id} saved: {result.file_path}")
```

### Handle permission errors

```python
handler = AppendHandler(output_dir="/root/protected")
result = handler.append("some content")

if not result.success:
    # result.error contains the OS error string, e.g. "Permission denied: '/root/protected/...'"
    import logging
    logging.error("Could not write output: %s", result.error)
```

---

## Error Handling

`append()` never raises. All errors are captured in the returned `AppendResult`:

| Condition | `result.success` | `result.error` |
|-----------|-----------------|---------------|
| Write succeeded | `True` | `None` |
| Output directory does not exist | `False` | `"[Errno 2] No such file or directory: '…'"` |
| Permission denied | `False` | `"[Errno 13] Permission denied: '…'"` |
| Disk full | `False` | `"[Errno 28] No space left on device"` |

---

## API

### `AppendHandler(output_dir: str)`

Constructs a handler that writes files to `output_dir`. The directory is expanded (supports `~`) but **not created** — callers must ensure it exists before the first `append()` call.

### `handler.append(content: str) -> AppendResult`

Writes `content` to a new timestamped file in `output_dir`. Uses `os.open()` with `O_CREAT | O_WRONLY | O_EXCL` to guarantee each call creates a unique file.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `content` | `str` | Text to write. Encoded as UTF-8. |

**Returns** `AppendResult` — always. Never raises.

---

## See Also

- [RecipeResult Reference](./recipe-result.md) — step outputs that AppendHandler typically persists
- [Trace Logging API](./trace-logging-api.md) — structured logging alongside file-based output
- [Runtime Directory Layout](../DEVELOPING_AMPLIHACK.md) — where output files live
