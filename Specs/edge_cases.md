# Edge Cases & Error Handling

## Purpose

Document all edge cases and error handling strategies for power-steering.

## Core Principle: Fail-Open

**CRITICAL**: Power-steering should NEVER prevent a user from stopping a session due to bugs or errors.

**Default Behavior on Error**: Approve stop and log error

---

## Edge Case Categories

### 1. Transcript-Related Edge Cases

#### 1.1 Missing Transcript File

**Scenario**: `transcript_path` doesn't exist

**Handling**:

```python
if not transcript_path.exists():
    self.logger.warning(f"Transcript file not found: {transcript_path}")
    return PowerSteeringResult("approve", ["transcript_missing"], None, None)
```

**Rationale**: Can't analyze what doesn't exist, allow stop

#### 1.2 Empty Transcript

**Scenario**: Transcript file exists but is empty (0 bytes or no messages)

**Handling**:

```python
messages = self._load_transcript(transcript_path)
if not messages:
    self.logger.info("Empty transcript, allowing stop")
    return PowerSteeringResult("approve", ["empty_transcript"], None, None)
```

**Rationale**: Nothing to analyze, allow stop

#### 1.3 Malformed JSONL

**Scenario**: Transcript contains invalid JSON lines

**Handling**:

```python
def _load_transcript(self, transcript_path: Path) -> List[Dict]:
    messages = []
    line_num = 0
    errors = 0

    with open(transcript_path) as f:
        for line in f:
            line_num += 1
            if not line.strip():
                continue

            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors += 1
                self.logger.warning(f"Invalid JSON at line {line_num}: {e}")
                if errors > 10:
                    # Too many errors, fail-open
                    self.logger.error("Too many JSON errors in transcript, skipping power-steering")
                    raise MalformedTranscriptError("Excessive JSON errors")

    return messages
```

**Rationale**: Try to parse what we can, but if too broken, give up

#### 1.4 Very Large Transcript (>10MB)

**Scenario**: Long session with huge transcript file

**Handling**:

```python
def check(self, transcript_path: Path, session_id: str) -> PowerSteeringResult:
    # Check file size before loading
    file_size = transcript_path.stat().st_size
    max_size = 10 * 1024 * 1024  # 10MB

    if file_size > max_size:
        self.logger.warning(f"Transcript too large ({file_size} bytes), skipping power-steering")
        return PowerSteeringResult("approve", ["transcript_too_large"], None, None)
```

**Rationale**: Prevent memory issues and timeouts

#### 1.5 Corrupted Transcript (Valid JSON but Wrong Structure)

**Scenario**: Messages don't have expected fields (role, content, etc.)

**Handling**:

```python
def _validate_message(self, msg: Dict) -> bool:
    """Check if message has expected structure."""
    return "role" in msg and msg["role"] in ["user", "assistant", "system"]

def _load_transcript(self, transcript_path: Path) -> List[Dict]:
    messages = []
    for msg in raw_messages:
        if self._validate_message(msg):
            messages.append(msg)
        else:
            self.logger.debug(f"Skipping invalid message: {msg}")
    return messages
```

**Rationale**: Skip invalid messages but continue with valid ones

---

### 2. Session-Related Edge Cases

#### 2.1 Missing Session ID

**Scenario**: `session_id` is None or empty string

**Handling**:

```python
if not session_id:
    session_id = self._generate_fallback_session_id()
    self.logger.warning(f"Missing session_id, using fallback: {session_id}")
```

**Rationale**: Generate fallback ID to continue, but log warning

#### 2.2 Duplicate Session IDs

**Scenario**: Same session_id used multiple times (race condition)

**Handling**:

```python
def _mark_complete(self, session_id: str):
    semaphore = self.runtime_dir / f".{session_id}_completed"

    # Atomic write with existence check
    try:
        semaphore.touch(exist_ok=False)
    except FileExistsError:
        self.logger.info(f"Session {session_id} already marked complete")
```

**Rationale**: First write wins, others skip gracefully

#### 2.3 Concurrent Sessions with Same ID

**Scenario**: Multiple sessions running simultaneously with same ID

**Handling**:

```python
def _already_ran(self, session_id: str) -> bool:
    semaphore = self.runtime_dir / f".{session_id}_completed"

    # Check age - if semaphore is old, ignore it
    if semaphore.exists():
        age_seconds = time.time() - semaphore.stat().st_mtime
        if age_seconds > 3600:  # 1 hour
            self.logger.warning(f"Stale semaphore for {session_id}, ignoring")
            return False
        return True

    return False
```

**Rationale**: Stale semaphores shouldn't block forever

---

### 3. Checker-Related Edge Cases

#### 3.1 Checker Method Missing

**Scenario**: Consideration references `_check_foo` but method doesn't exist

**Handling**:

```python
def _check_consideration(self, consideration: Dict, transcript: List[Dict], session_id: str) -> bool:
    checker_func = getattr(self, consideration['checker'], None)

    if not checker_func:
        self.logger.warning(f"Checker not found: {consideration['checker']}, skipping")
        return True  # Treat as satisfied (don't block on missing checker)

    return checker_func(transcript, session_id)
```

**Rationale**: Don't block on implementation gaps

#### 3.2 Checker Crashes

**Scenario**: Individual checker raises exception

**Handling**:

```python
def _check_consideration(self, consideration: Dict, transcript: List[Dict], session_id: str) -> bool:
    checker_func = getattr(self, consideration['checker'], None)

    if not checker_func:
        return True

    try:
        return checker_func(transcript, session_id)
    except Exception as e:
        self.logger.error(
            f"Checker {consideration['checker']} crashed: {e}",
            exc_info=True
        )
        return True  # Treat as satisfied (don't block on bugs)
```

**Rationale**: One bad checker shouldn't break entire system

#### 3.3 Checker Times Out

**Scenario**: Checker takes too long (infinite loop, network call, etc.)

**Handling**:

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds: int):
    def timeout_handler(signum, frame):
        raise TimeoutError("Operation timed out")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def _check_consideration(self, consideration: Dict, transcript: List[Dict], session_id: str) -> bool:
    checker_func = getattr(self, consideration['checker'], None)

    if not checker_func:
        return True

    try:
        with timeout(5):  # 5 second timeout per checker
            return checker_func(transcript, session_id)
    except TimeoutError:
        self.logger.error(f"Checker {consideration['checker']} timed out")
        return True  # Treat as satisfied
    except Exception as e:
        self.logger.error(f"Checker {consideration['checker']} crashed: {e}")
        return True
```

**Rationale**: Don't let slow checkers hang stop hook

#### 3.4 All Checkers Timeout

**Scenario**: Overall analysis takes too long

**Handling**:

```python
def check(self, transcript_path: Path, session_id: str) -> PowerSteeringResult:
    try:
        with timeout(30):  # 30 second timeout for entire analysis
            # ... normal flow ...
    except TimeoutError:
        self.logger.error("Power-steering analysis timed out")
        return PowerSteeringResult("approve", ["timeout"], None, None)
```

**Rationale**: Never hang the stop hook indefinitely

---

### 4. Configuration Edge Cases

#### 4.1 Config File Missing

**Scenario**: `.power_steering_config` doesn't exist

**Handling**:

```python
def _load_config(self) -> Dict:
    config_path = self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"

    if not config_path.exists():
        self.logger.debug("Config file not found, using defaults")
        return DEFAULT_CONFIG
```

**Rationale**: Use defaults, don't require config file

#### 4.2 Invalid JSON in Config

**Scenario**: Config file contains malformed JSON

**Handling**:

```python
def _load_config(self) -> Dict:
    config_path = self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"

    if not config_path.exists():
        return DEFAULT_CONFIG

    try:
        with open(config_path) as f:
            config = json.load(f)
            return {**DEFAULT_CONFIG, **config}
    except json.JSONDecodeError as e:
        self.logger.warning(f"Invalid JSON in config: {e}, using defaults")
        return DEFAULT_CONFIG
```

**Rationale**: Bad config shouldn't crash power-steering

#### 4.3 Config with Unknown Keys

**Scenario**: Config contains fields not in schema

**Handling**:

```python
def _load_config(self) -> Dict:
    raw_config = self._load_raw_config()

    # Only use known keys
    known_keys = DEFAULT_CONFIG.keys()
    config = {k: v for k, v in raw_config.items() if k in known_keys}

    # Log unknown keys
    unknown = set(raw_config.keys()) - set(known_keys)
    if unknown:
        self.logger.warning(f"Unknown config keys: {unknown}")

    return {**DEFAULT_CONFIG, **config}
```

**Rationale**: Ignore unknown keys, use what we know

#### 4.4 Invalid Config Values

**Scenario**: Config has wrong type or out-of-range values

**Handling**:

```python
def _validate_config(self, config: Dict) -> Dict:
    """Validate and sanitize config values."""

    # Validate enabled (bool)
    if not isinstance(config.get("enabled"), bool):
        self.logger.warning(f"Invalid 'enabled' value, using default")
        config["enabled"] = DEFAULT_CONFIG["enabled"]

    # Validate timeout_seconds (positive int)
    timeout = config.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout < 1 or timeout > 300:
        self.logger.warning(f"Invalid 'timeout_seconds' value, using default")
        config["timeout_seconds"] = DEFAULT_CONFIG["timeout_seconds"]

    return config
```

**Rationale**: Sanitize bad values rather than crashing

---

### 5. File System Edge Cases

#### 5.1 Permission Errors (Can't Write Semaphore)

**Scenario**: No write permission for `~/.amplihack/.claude/runtime/power-steering/`

**Handling**:

```python
def _mark_complete(self, session_id: str):
    semaphore = self.runtime_dir / f".{session_id}_completed"

    try:
        semaphore.parent.mkdir(parents=True, exist_ok=True)
        semaphore.touch()
    except PermissionError as e:
        self.logger.error(f"Cannot write semaphore: {e}")
        # Continue anyway - not a blocker
    except Exception as e:
        self.logger.error(f"Failed to create semaphore: {e}")
```

**Rationale**: Semaphore is optimization, not critical

#### 5.2 Disk Full

**Scenario**: Can't write summary or semaphore due to disk full

**Handling**:

```python
def _write_summary(self, session_id: str, summary: str):
    summary_path = self.runtime_dir / session_id / "summary.md"

    try:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary)
    except OSError as e:
        self.logger.error(f"Cannot write summary: {e}")
        # Continue - summary is nice-to-have
```

**Rationale**: Summary is enhancement, not critical

#### 5.3 Symlink Attacks

**Scenario**: Malicious user creates symlinks in runtime directory

**Handling**:

```python
def _safe_path(self, path: Path) -> Path:
    """Resolve path and ensure it's within project."""
    resolved = path.resolve()

    # Ensure path is within project_root
    if not str(resolved).startswith(str(self.project_root)):
        raise SecurityError(f"Path outside project: {resolved}")

    return resolved
```

**Rationale**: Prevent directory traversal attacks

---

### 6. Consideration-Specific Edge Cases

#### 6.1 No Tool Calls in Transcript

**Scenario**: Session with only text chat, no file operations

**Handling**:

```python
def _check_objective_complete(self, transcript: List[Dict], session_id: str) -> bool:
    tool_calls = self._extract_tool_calls(transcript)

    if not tool_calls:
        # Likely Q&A session, check if last message looks conclusive
        last_msg = self._get_last_assistant_message(transcript)
        if self._looks_conclusive(last_msg):
            return True
        return False  # Ambiguous, prefer to ask
```

**Rationale**: Handle informational sessions differently

#### 6.2 No First User Message (Can't Extract Objective)

**Scenario**: Transcript doesn't start with user message

**Handling**:

```python
def _extract_objective(self, transcript: List[Dict]) -> str:
    user_messages = [m for m in transcript if m.get("role") == "user"]

    if not user_messages:
        return "Unknown objective (no user messages)"

    return self._extract_text(user_messages[0])
```

**Rationale**: Handle edge case gracefully

#### 6.3 CI Status Check Fails (Network Error)

**Scenario**: Can't reach GitHub API to check CI status

**Handling**:

```python
def _check_ci_status(self, transcript: List[Dict], session_id: str) -> bool:
    try:
        ci_status = self._get_ci_status_from_transcript(transcript)
        return ci_status.all_passed()
    except NetworkError:
        # Can't verify CI, don't block
        self.logger.warning("Cannot check CI status (network error)")
        return True
```

**Rationale**: Don't block on external service failures

---

### 7. Recursive Power-Steering Edge Cases

#### 7.1 Power-Steering Blocks, User Responds, Power-Steering Runs Again

**Scenario**: Normal case, should work

**Handling**:

```python
def check(self, transcript_path: Path, session_id: str) -> PowerSteeringResult:
    # Check semaphore first
    if self._already_ran(session_id):
        return PowerSteeringResult("approve", ["already_ran"], None, None)

    # ... normal flow ...

    # Only mark complete on approval
    if result.decision == "approve":
        self._mark_complete(session_id)
```

**Rationale**: Only mark complete when approving, allow re-checking after blocks

#### 7.2 Power-Steering Blocks Itself (Infinite Loop)

**Scenario**: Power-steering's continuation prompt is seen as incomplete work

**Handling**:

```python
def _is_power_steering_prompt(self, message: Dict) -> bool:
    """Detect if message is power-steering continuation prompt."""
    content = self._extract_text(message)
    return "The session appears incomplete" in content

def check(self, transcript_path: Path, session_id: str) -> PowerSteeringResult:
    # Check if last message was power-steering prompt
    last_msg = self._get_last_assistant_message(transcript)
    if self._is_power_steering_prompt(last_msg):
        # Don't re-check same prompt
        return PowerSteeringResult("approve", ["power_steering_prompt"], None, None)
```

**Rationale**: Detect and break infinite loops

#### 7.3 Semaphore Stale (Old Session with Same ID)

**Scenario**: Semaphore from old session prevents new analysis

**Handling**: See section 2.3 above (check semaphore age)

---

### 8. Prompt Generation Edge Cases

#### 8.1 No Failed Considerations (Shouldn't Block but Logic Error)

**Scenario**: Bug causes block with empty failed_considerations list

**Handling**:

```python
def _generate_continuation_prompt(self, analysis: ConsiderationAnalysis) -> str:
    if not analysis.failed_considerations:
        # Logic error - shouldn't be here
        self.logger.error("generate_continuation_prompt called with no failures")
        return "Session appears complete. If you see this, please report a bug."

    # ... normal flow ...
```

**Rationale**: Handle logic errors gracefully

#### 8.2 All Considerations Warning-Only

**Scenario**: Only warnings failed, no blockers

**Handling**:

```python
@property
def has_blockers(self) -> bool:
    """True if any blocker consideration failed."""
    return any(
        c.get("severity") == "blocker"
        for c in self.failed_considerations
    )

def check(...) -> PowerSteeringResult:
    if analysis.has_blockers:
        return block_result
    elif analysis.failed_considerations:
        # Only warnings - inform but allow
        return PowerSteeringResult(
            decision="approve",
            reasons=["only_warnings"],
            continuation_prompt=None,
            summary=self._generate_summary_with_warnings(analysis)
        )
```

**Rationale**: Don't block on warnings

---

### 9. Summary Generation Edge Cases

#### 9.1 Can't Extract Objective

**Scenario**: No clear objective in transcript

**Handling**: Use placeholder "Unknown objective", continue with summary

#### 9.2 No Files Changed

**Scenario**: Session with no file operations

**Handling**:

```python
def _extract_files_changed(self, transcript: List[Dict]) -> str:
    files = self._find_file_operations(transcript)

    if not files:
        return "No files were modified (informational session)"

    return "\n".join(f"- {f}" for f in files)
```

**Rationale**: Acknowledge informational sessions

#### 9.3 Summary Too Large (>10MB)

**Scenario**: Pathological case with huge summary

**Handling**:

```python
def _generate_summary(...) -> str:
    summary = "..."  # generate

    # Truncate if too large
    max_size = 100_000  # 100KB
    if len(summary) > max_size:
        summary = summary[:max_size] + "\n\n... (truncated)"

    return summary
```

**Rationale**: Prevent memory/disk issues

---

## Error Handling Patterns

### Pattern 1: Try-Except-Log-Continue

```python
try:
    result = risky_operation()
except Exception as e:
    self.logger.error(f"Operation failed: {e}", exc_info=True)
    result = safe_default
```

### Pattern 2: Validate-Before-Use

```python
if not self._is_valid(input):
    self.logger.warning(f"Invalid input: {input}")
    return fallback_value
```

### Pattern 3: Fail-Open on Critical Path

```python
try:
    power_steering_result = check_completeness()
except Exception as e:
    log_error(e)
    return approve_stop()  # Don't block user
```

### Pattern 4: Timeout on Long Operations

```python
with timeout(30):
    result = potentially_slow_operation()
```

---

## Testing Strategy for Edge Cases

### Unit Tests

- Mock each edge case scenario
- Verify correct handling
- Check logging output
- Verify fail-open behavior

### Integration Tests

- Real transcript files with edge cases
- File system permissions tests
- Timeout simulation
- Concurrent execution tests

### Chaos Testing

- Random transcript corruption
- Random file system errors
- Random network failures
- Measure fail-open rate (should be 100%)

---

## Monitoring & Alerting

### Metrics to Track

- `power_steering_errors`: Total errors
- `power_steering_timeouts`: Timeout count
- `power_steering_transcript_errors`: Malformed transcripts
- `power_steering_checker_crashes`: Individual checker failures

### Alerts

- Alert if error rate >5% over 1 hour
- Alert if timeout rate >10% over 1 hour
- Alert if specific checker crashes repeatedly

### Investigation

- All errors logged with full context
- Transcript path saved for debugging
- Stack traces captured
- Session ID for reproduction

---

## Recovery Procedures

### User Experiencing Issues

**Step 1: Immediate Disable**

```bash
export AMPLIHACK_SKIP_POWER_STEERING=1
```

**Step 2: Report Issue**

- Include session ID
- Include error message
- Include transcript path (if accessible)

**Step 3: Re-enable After Fix**

```bash
unset AMPLIHACK_SKIP_POWER_STEERING
```

### Developer Debugging

**Step 1: Reproduce**

- Use exact transcript file
- Same session ID
- Same environment

**Step 2: Isolate**

- Test each checker independently
- Identify failing component

**Step 3: Fix & Test**

- Add test case for edge case
- Verify fix
- Deploy patch

**Step 4: Monitor**

- Watch metrics for recurrence
- Verify fix effectiveness
