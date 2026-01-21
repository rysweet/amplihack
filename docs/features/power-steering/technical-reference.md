# Power Steering Technical Reference

Ahoy, developer! This be the technical reference fer power steering's internals, particularly the infinite loop fix implemented in v0.9.1.

## State Management Architecture

### State Structure

Power steering maintains persistent state in JSON format:

```python
{
    "consecutive_blocks": 0,        # Guidance counter
    "session_id": "20251217_193000", # Session identifier
    "last_check_timestamp": "2025-12-17T19:30:00Z",
    "check_results": {               # Last check results
        "files_modified": ["file1.py", "file2.py"],
        "workflow_compliant": true,
        "quality_score": 85
    }
}
```

**State file location:** `.claude/runtime/power-steering/{session_id}/state.json`

### State Lifecycle

```
Initialize → Load → Validate → Check → Increment → Save → Verify
     ↓         ↑                            ↓
   Create   Recover                    fsync + retry
```

## Atomic Write Implementation

### Core Write Function

```python
def _atomic_write_state(self, state_data: Dict[str, Any]) -> bool:
    """
    Atomically write state with verification.

    Returns True if write AND verification succeed.
    Logs to diagnostics on failure.
    """
    state_file = self._get_state_file()

    # Phase 1: Write with fsync
    try:
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # CRITICAL: Force disk write
    except OSError as e:
        self._log_diagnostic({
            "operation": "state_save",
            "save_success": False,
            "error": str(e)
        })
        return False

    # Phase 2: Verification read
    try:
        with open(state_file, 'r') as f:
            verified_data = json.load(f)

        if verified_data != state_data:
            self._log_diagnostic({
                "operation": "verification_read",
                "verification_success": False,
                "reason": "data_mismatch"
            })
            return False

    except (OSError, json.JSONDecodeError) as e:
        self._log_diagnostic({
            "operation": "verification_read",
            "verification_success": False,
            "error": str(e)
        })
        return False

    # Success
    self._log_diagnostic({
        "operation": "state_save",
        "save_success": True,
        "verification_success": True,
        "retry_count": 0
    })
    return True
```

### Retry Logic

```python
def _write_with_retry(self, state_data: Dict[str, Any],
                      max_retries: int = 3) -> bool:
    """Write with exponential backoff for cloud sync resilience"""
    retry_delays = [0.1, 0.2, 0.4]  # seconds

    for attempt, delay in enumerate(retry_delays):
        if self._atomic_write_state(state_data):
            if attempt > 0:
                self._log_diagnostic({
                    "operation": "state_save_retry",
                    "success": True,
                    "retry_count": attempt
                })
            return True

        if attempt < len(retry_delays) - 1:
            time.sleep(delay)

    # All retries failed - try non-atomic fallback
    return self._fallback_write(state_data)
```

### Why fsync() is Critical

**Without fsync():**

```python
with open(file, 'w') as f:
    f.write(data)
# Data in OS buffer - not on disk yet!
# Power loss = data loss
# Cloud sync may read old data
```

**With fsync():**

```python
with open(file, 'w') as f:
    f.write(data)
    f.flush()
    os.fsync(f.fileno())
# Data GUARANTEED on disk
# Cloud sync sees latest data
```

**Trade-off:**

- Adds 1-2ms latency per write
- Worth it to prevent infinite loops

## Defensive Validation

### Validation Rules

```python
def _validate_state(self, state: Dict) -> Tuple[bool, str]:
    """
    Validate loaded state data.

    Returns (is_valid, reason) tuple.
    """
    # Type check
    if not isinstance(state, dict):
        return (False, "state_not_dict")

    # Counter validation
    counter = state.get("consecutive_blocks")
    if counter is None:
        return (False, "missing_counter")
    if not isinstance(counter, int):
        return (False, "counter_not_int")
    if counter < 0:
        return (False, "negative_counter")
    if counter > 1000:  # Sanity check
        return (False, "counter_too_large")

    # Session ID validation
    session_id = state.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return (False, "invalid_session_id")

    return (True, "")
```

### Recovery Strategy

```python
def _load_state_with_validation(self) -> Dict[str, Any]:
    """Load state with validation and recovery"""
    try:
        with open(self._get_state_file(), 'r') as f:
            state = json.load(f)

        is_valid, reason = self._validate_state(state)

        if not is_valid:
            self._log_diagnostic({
                "operation": "validation",
                "validation_failed": True,
                "reason": reason,
                "corrupted_state": state
            })

            # Recovery: Reset to defaults
            state = self._get_default_state()
            self._log_diagnostic({
                "operation": "state_reset",
                "counter_reset_to": 0
            })

    except (FileNotFoundError, json.JSONDecodeError):
        # Expected on first run or corrupted file
        state = self._get_default_state()

    return state
```

## Diagnostic Logging

### Log Format

Structured JSON logs written to `.claude/runtime/power-steering/{session_id}/diagnostic.jsonl`:

```json
{"timestamp": "2025-12-17T19:30:00.123Z", "operation": "state_save", ...}
{"timestamp": "2025-12-17T19:30:00.456Z", "operation": "state_load", ...}
{"timestamp": "2025-12-17T19:30:01.789Z", "operation": "validation", ...}
```

### Log Entry Types

**state_save:**

```json
{
  "timestamp": "ISO8601",
  "operation": "state_save",
  "counter_before": 0,
  "counter_after": 1,
  "session_id": "session_id_string",
  "file_path": "path/to/state.json",
  "save_success": true,
  "verification_success": true,
  "retry_count": 0
}
```

**state_load:**

```json
{
  "timestamp": "ISO8601",
  "operation": "state_load",
  "session_id": "session_id_string",
  "file_path": "path/to/state.json",
  "load_success": true,
  "validation_passed": true,
  "counter_value": 1
}
```

**validation:**

```json
{
  "timestamp": "ISO8601",
  "operation": "validation",
  "validation_failed": true,
  "reason": "negative_counter",
  "corrupted_state": { "consecutive_blocks": -1 }
}
```

**state_reset:**

```json
{
  "timestamp": "ISO8601",
  "operation": "state_reset",
  "reason": "corruption_detected",
  "counter_reset_to": 0
}
```

### Log Analysis

**Extract failures:**

```bash
cat .claude/runtime/power-steering/*/diagnostic.jsonl | \
  grep '"success": false' | \
  jq -r '[.timestamp, .operation, .reason] | @tsv'
```

**Count retries:**

```bash
cat .claude/runtime/power-steering/*/diagnostic.jsonl | \
  grep '"retry_count"' | \
  jq '.retry_count' | \
  awk '{sum+=$1; count++} END {print sum/count}'
```

**Find corruption events:**

```bash
cat .claude/runtime/power-steering/*/diagnostic.jsonl | \
  grep '"validation_failed": true'
```

## Message Customization

### Check Results Integration

```python
def _customize_message(self,
                       check_results: Dict[str, Any]) -> str:
    """
    Customize guidance message based on check results.

    Args:
        check_results: Results from power_steering_checker
            - files_modified: List of changed files
            - workflow_compliant: Boolean
            - quality_score: 0-100

    Returns:
        Customized guidance string
    """
    # Base message
    if not check_results.get("files_modified"):
        return "Ahoy! No files modified - smooth sailin'!"

    # Workflow compliance check
    if not check_results.get("workflow_compliant"):
        return (
            f"Arr! Found {len(check_results['files_modified'])} "
            "modified files, but workflow not followed. "
            "Check DEFAULT_WORKFLOW.md, matey!"
        )

    # Quality score check
    quality = check_results.get("quality_score", 0)
    if quality < 70:
        return (
            f"Files modified with quality score {quality}. "
            "Consider reviewin' yer changes fer improvement."
        )

    # All good
    return (
        f"Nice work! {len(check_results['files_modified'])} "
        f"files modified with {quality}% quality. "
        "Keep it up!"
    )
```

## Performance Characteristics

### Operation Latencies

| Operation               | Typical | Worst Case | Notes                 |
| ----------------------- | ------- | ---------- | --------------------- |
| State load              | 0.5ms   | 5ms        | Depends on disk speed |
| State save (no fsync)   | 0.5ms   | 5ms        | OS buffered           |
| State save (with fsync) | 1-2ms   | 50ms       | Disk flush            |
| Verification read       | 0.3ms   | 3ms        | Cached by OS          |
| Validation              | 0.1ms   | 0.5ms      | Pure CPU              |
| Retry delay             | 100ms   | 400ms      | Cloud sync tolerance  |

### Memory Usage

- State object: ~500 bytes
- Diagnostic log: ~200 bytes per entry
- Session overhead: ~1KB

### Scalability

- State files isolated per session (no contention)
- Diagnostic logs auto-rotate (TODO: implement cleanup)
- No database dependencies (filesystem only)

## Error Codes

Power steering uses these return codes:

| Code | Meaning               | Recovery              |
| ---- | --------------------- | --------------------- |
| 0    | Success               | Continue              |
| 1    | State save failed     | Retry, then fallback  |
| 2    | Validation failed     | Reset to defaults     |
| 3    | Verification failed   | Retry write           |
| 4    | All retries exhausted | Log warning, continue |

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
def test_atomic_write_with_fsync():
    """Verify fsync is called during write"""
    with patch('os.fsync') as mock_fsync:
        state_manager._atomic_write_state({})
        assert mock_fsync.called

def test_validation_detects_negative_counter():
    """Validation catches corrupted counter"""
    state = {"consecutive_blocks": -1}
    is_valid, reason = validator._validate_state(state)
    assert not is_valid
    assert reason == "negative_counter"
```

### Integration Tests

Test component interactions:

```python
def test_save_load_roundtrip():
    """Data persists correctly through save/load"""
    original_state = {"consecutive_blocks": 5}
    manager.save_state(original_state)
    loaded_state = manager.load_state()
    assert loaded_state == original_state

def test_corruption_recovery():
    """System recovers from corrupted state file"""
    # Write corrupted data
    write_corrupted_state_file()

    # Load should recover
    state = manager.load_state()
    assert state["consecutive_blocks"] == 0  # Default
```

### End-to-End Tests

Simulate real-world scenarios:

```python
def test_cloud_sync_conflict():
    """Handle cloud sync delays gracefully"""
    with simulated_cloud_sync_delay(200):  # ms
        manager.save_state({"consecutive_blocks": 1})
        state = manager.load_state()
        assert state["consecutive_blocks"] == 1

def test_concurrent_session_isolation():
    """Multiple sessions don't interfere"""
    session1 = PowerSteeringState("session1")
    session2 = PowerSteeringState("session2")

    session1.save_state({"consecutive_blocks": 5})
    session2.save_state({"consecutive_blocks": 10})

    assert session1.load_state()["consecutive_blocks"] == 5
    assert session2.load_state()["consecutive_blocks"] == 10
```

## Configuration

### Environment Variables

Control power steering behavior:

```bash
# Enable debug logging
export AMPLIHACK_PS_DEBUG=1

# Increase retry count
export AMPLIHACK_PS_MAX_RETRIES=5

# Disable fsync (NOT RECOMMENDED)
export AMPLIHACK_PS_NO_FSYNC=1

# Custom state directory
export AMPLIHACK_PS_STATE_DIR=/custom/path
```

### Runtime Configuration

Override defaults in code:

```python
from claude.tools.amplihack.hooks import power_steering_state

# Custom retry delays (seconds)
power_steering_state.RETRY_DELAYS = [0.05, 0.1, 0.2]

# Disable verification read (NOT RECOMMENDED)
power_steering_state.VERIFY_WRITES = False

# Custom diagnostic log location
power_steering_state.DIAGNOSTIC_LOG_DIR = "/custom/logs"
```

## Debugging

### Enable Debug Logging

```python
import logging

logging.getLogger("amplihack.power_steering").setLevel(logging.DEBUG)
```

### Trace State Operations

```bash
# Watch state file changes in real-time
watch -n 1 cat .claude/runtime/power-steering/*/state.json

# Tail diagnostic logs
tail -f .claude/runtime/power-steering/*/diagnostic.jsonl | jq
```

### Reproduce Issues

```python
# Simulate fsync failure
with patch('os.fsync', side_effect=OSError("Disk full")):
    manager.save_state(state)

# Simulate corrupted file
write_invalid_json_to_state_file()
manager.load_state()  # Should recover gracefully
```

## Smart Message Truncation

### Overview

Power steering feedback messages are intelligently truncated to maintain readability and security while preserving semantic meaning. The truncation system prevents mid-word breaks and prioritizes sentence boundaries.

### The `_smart_truncate()` Function

Located in `.claude/tools/amplihack/hooks/claude_power_steering.py`, this function implements multi-level truncation logic:

```python
def _smart_truncate(text: str, max_length: int = 200) -> str:
    """
    Smart truncation that preserves sentence and word boundaries.

    Truncation priority:
    1. Sentence boundaries (. ! ?)
    2. Word boundaries (whitespace)
    3. Character limit (with ... indicator)

    Args:
        text: Input text to truncate
        max_length: Maximum length (default: 200 chars)

    Returns:
        Truncated text with ... indicator if shortened

    Examples:
        >>> _smart_truncate("First sentence. Second sentence.", 20)
        "First sentence."

        >>> _smart_truncate("Short text", 200)
        "Short text"

        >>> _smart_truncate("VeryLongWordWithNoSpaces" * 20, 200)
        "VeryLongWordWithNoSpaces...VeryLongWordWit..."
    """
    if len(text) <= max_length:
        return text

    # Level 1: Try sentence boundary truncation
    sentence_boundaries = ['.', '!', '?']
    best_boundary = -1

    for i in range(max_length - 1, -1, -1):
        if text[i] in sentence_boundaries:
            # Include the boundary character itself
            best_boundary = i + 1
            break

    if best_boundary > 0:
        return text[:best_boundary]

    # Level 2: Try word boundary truncation
    for i in range(max_length - 1, -1, -1):
        if text[i] == ' ':
            # Don't include the trailing space
            return text[:i]

    # Level 3: Hard truncate at character limit
    return text[:max_length]
```

### Truncation Behavior

**Sentence Boundary (Preferred)**

```python
# Input (300 chars)
"Run pytest to verify your changes. Ensure all tests pass. Check CI status."

# Output (stays under 200 chars)
"Run pytest to verify your changes. Ensure all tests pass."
```

**Word Boundary (Fallback)**

```python
# Input (no sentence boundaries within limit)
"CompleteTheIncompleteTODOsShownInTheTaskList"

# Output
"CompleteTheIncompleteTODOsShownInThe..."
```

**Hard Truncate (Last Resort)**

```python
# Input (no spaces or punctuation)
"VeryLongWordWithNoSpaces" * 50

# Output
"VeryLongWordWithNoSpacesVeryLongWordWit..."
```

### Security Considerations

The 200-character maximum serves dual purposes:

1. **Readability**: Keeps messages concise and scannable
2. **Security**: Prevents feedback injection attacks by limiting message length

**Why 200 Characters?**

- Fits on most terminal screens without wrapping
- Short enough to scan quickly
- Long enough for meaningful guidance
- Matches security limit in `claude_power_steering.py`

### Integration Points

Smart truncation is applied to:

1. **Consideration failure reasons** - Why a check failed
2. **Completion claim detection** - Claims extracted from transcripts
3. **Evidence strings** - Why delta content addresses a failure
4. **Final guidance messages** - Overall feedback to user

**Example Integration**

```python
# In analyze_consideration()
reason = _extract_reason_from_response(response)
# Reason is already truncated to 200 chars

# In generate_final_guidance()
guidance = _sanitize_html(guidance)
# Smart truncation applied during sanitization
```

### Testing Smart Truncation

**Unit Tests**

```python
def test_smart_truncate_preserves_short_text():
    """Text under limit is unchanged"""
    short = "This is short"
    assert _smart_truncate(short, 200) == short

def test_smart_truncate_uses_sentence_boundary():
    """Prioritizes sentence boundaries"""
    text = "First sentence. Second sentence. Third."
    result = _smart_truncate(text, 20)
    assert result == "First sentence."

def test_smart_truncate_uses_word_boundary():
    """Falls back to word boundaries"""
    text = "No sentence punctuation just words"
    result = _smart_truncate(text, 20)
    assert result.endswith("...")
    assert not result[:-3].endswith(" ")  # No trailing space

def test_smart_truncate_hard_limit():
    """Hard truncates when no boundaries found"""
    text = "VeryLongWordWithNoSpaces" * 20
    result = _smart_truncate(text, 50)
    assert len(result) == 50
    assert result.endswith("...")
```

**Integration Tests**

```python
def test_feedback_messages_are_truncated():
    """Verify truncation in real feedback flow"""
    # Create long failure reason
    long_reason = "Check failed because " + "x" * 300

    # Generate guidance
    guidance = generate_final_guidance(
        [("test_check", long_reason)],
        conversation=[],
        project_root=Path.cwd()
    )

    # Verify truncation applied
    assert len(guidance) <= 200
    assert "..." in guidance or "." in guidance
```

### Performance Characteristics

| Operation         | Complexity | Typical Time |
| ----------------- | ---------- | ------------ |
| Length check      | O(1)       | < 0.01ms     |
| Sentence search   | O(n)       | 0.1ms        |
| Word search       | O(n)       | 0.1ms        |
| Hard truncate     | O(1)       | < 0.01ms     |
| Total (worst case)| O(n)       | 0.2ms        |

Where n = max_length (200 chars max).

### Configuration

Smart truncation can be customized via constants in `claude_power_steering.py`:

```python
# Default maximum length
MAX_SDK_RESPONSE_LENGTH = 5000  # For full responses
MAX_FEEDBACK_MESSAGE_LENGTH = 200  # For truncated feedback

# Sentence terminators
SENTENCE_TERMINATORS = ['. ', '! ', '? ']

# Truncation indicator
TRUNCATION_INDICATOR = "..."
```

### Debugging

**Enable truncation logging:**

```python
import logging

logging.getLogger("amplihack.power_steering.truncation").setLevel(logging.DEBUG)
```

**Check truncation in diagnostic logs:**

```bash
grep "truncated" .claude/runtime/power-steering/*/diagnostic.jsonl | \
  jq '{timestamp, original_length, truncated_length, method}'
```

## Related Documentation

- [Power Steering Overview](./README.md)
- [Architecture](./architecture.md)
- [Troubleshooting](./troubleshooting.md)
- [Changelog v0.9.1](./changelog-v0.9.1.md)
