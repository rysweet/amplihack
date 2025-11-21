# Auto Mode Execution Bug - Diagnostic and Fix Strategy

**Issue**: Auto mode stops after Turn 2 (Planning) instead of continuing to Turns 3+ (Execution/Evaluation)
**Current behavior**: Exit code 0 (success) but only 2/20 turns executed
**Location**: `/src/amplihack/launcher/auto_mode.py` lines 994-1220 (`_run_async_session`)
**Root cause status**: Not yet confirmed - multiple candidates identified

---

## PHASE 1: ROOT CAUSE DIAGNOSIS

### Ranked Suspects (High → Low Probability)

#### 1. **SWALLOWED EXCEPTION (HIGH PRIORITY)**
- **Location**: Lines 1090-1198 (the `for turn in range(3, self.max_turns + 1)` loop)
- **Theory**: Exception occurs inside the loop but is caught somewhere, breaking loop execution
- **Why HIGH**:
  - No explicit exception handling visible in loop
  - SDK calls wrapped in `await _run_turn_with_retry()` which catches exceptions
  - Could silently fail and return immediately
- **Symptoms**: Silent exit with code 0, no error logging
- **Confidence**: 85%

#### 2. **EARLY BREAK BEFORE LOOP (MEDIUM PRIORITY)**
- **Location**: Lines 1083-1091 (before Turn 3 starts)
- **Theory**: Turn 2 completes, but code breaks/returns before reaching Turn 3
- **Why MEDIUM**:
  - Loop is inside try-finally block
  - Could be premature return in error handling
  - Or break statement could be triggered by error state
- **Symptoms**: Cleanly exits with 0, no loop entry
- **Confidence**: 60%

#### 3. **SDK HANG (MEDIUM PRIORITY)**
- **Location**: Lines 1147-1149 (`await self._run_turn_with_retry()` calls)
- **Theory**: Turn 2 call hangs indefinitely, blocking execution
- **Why MEDIUM**:
  - Async SDK calls could deadlock
  - RetryLogic adds delays that could exceed timeouts
  - Single event loop shared across session
- **Symptoms**: Process hangs without exiting
- **Confidence**: 50%

#### 4. **EMPTY LOOP RANGE (LOW PRIORITY)**
- **Location**: Line 1091 (`for turn in range(3, self.max_turns + 1)`)
- **Theory**: Loop range is empty (3 > max_turns)
- **Why LOW**:
  - max_turns defaults to 10 (line 80)
  - Would need caller to pass max_turns < 3
- **Symptoms**: Silent skip of loop (would execute 0 times)
- **Confidence**: 15%

#### 5. **ASYNC COORDINATION FAILURE (MEDIUM PRIORITY)**
- **Location**: Lines 1000-1020 (async event loop setup)
- **Theory**: Single event loop has resource limits or context issues
- **Why MEDIUM**:
  - First two turns work (loop created successfully)
  - Third turn might encounter context poisoning
  - Forking logic (lines 1094-1113) could interfere
- **Symptoms**: Stops exactly at Turn 3, not random
- **Confidence**: 45%

---

## PHASE 2: INSTRUMENTATION PLAN

### Logging Points to Add

#### A. Loop Entry/Exit Detection
```python
# At line 1091 (BEFORE for loop)
self.log(f"DEBUG: Entering execution loop with range(3, {self.max_turns + 1})", level="DEBUG")
loop_entry_logged = True

# At line 1091.5 (INSIDE for loop, first thing)
self.log(f"DEBUG: Loop iteration started - turn={turn}", level="DEBUG")

# At line 1198.5 (AFTER loop completes)
self.log(f"DEBUG: Loop exited normally, final turn={self.turn}", level="DEBUG")
```

#### B. Exception Capture in Loop
```python
# Wrap entire loop in try-except
try:
    for turn in range(3, self.max_turns + 1):
        self.log(f"DEBUG: Turn {turn} starting", level="DEBUG")
        try:
            # ... existing code ...
        except Exception as e:
            self.log(f"ERROR: Exception in turn {turn}: {type(e).__name__}: {e}", level="ERROR")
            import traceback
            self.log(f"Traceback:\n{traceback.format_exc()}", level="ERROR")
            raise  # Re-raise to debug
except Exception as e:
    self.log(f"CRITICAL: Exception escaped loop: {type(e).__name__}: {e}", level="ERROR")
    raise
```

#### C. Turn Execution Checkpoint Logging
```python
# At line 1120 (BEFORE execute_prompt)
self.log(f"DEBUG: About to execute turn {turn}", level="DEBUG")

# At line 1147 (BEFORE await)
self.log(f"DEBUG: Calling _run_turn_with_retry for execute", level="DEBUG")

# At line 1149 (AFTER await)
self.log(f"DEBUG: _run_turn_with_retry returned code={code}, output_len={len(execution_output)}", level="DEBUG")

# At line 1157 (BEFORE evaluate)
self.log(f"DEBUG: About to evaluate turn {turn}", level="DEBUG")

# At line 1180 (AFTER evaluate)
self.log(f"DEBUG: Evaluation completed, result contains: {eval_result[:100]}...", level="DEBUG")

# At line 1193 (BEFORE break check)
self.log(f"DEBUG: Checking for completion signals in eval_result", level="DEBUG")
```

#### D. Completion Check Logging
```python
# At line 1183-1188 (INSIDE if statement)
eval_lower = eval_result.lower()
self.log(f"DEBUG: Completion check - searching for signals in eval", level="DEBUG")
if "auto-mode evaluation: complete" in eval_lower:
    self.log(f"DEBUG: Found 'auto-mode evaluation: complete' - breaking", level="DEBUG")
    # ... break ...
elif "objective achieved" in eval_lower:
    self.log(f"DEBUG: Found 'objective achieved' - breaking", level="DEBUG")
    # ... break ...
else:
    self.log(f"DEBUG: No completion signals found - continuing loop", level="DEBUG")
```

#### E. Async Context Logging
```python
# At line 1091 (BEFORE loop)
self.log(f"DEBUG: Event loop active: {asyncio._get_running_loop() is not None}", level="DEBUG")
self.log(f"DEBUG: max_turns={self.max_turns}, turn will go from 3 to {self.max_turns}", level="DEBUG")

# At line 1091.5 (IN loop, first thing)
try:
    self.log(f"DEBUG: Event loop still active in turn {turn}", level="DEBUG")
except:
    self.log(f"ERROR: Event loop lost in turn {turn}!", level="ERROR")
```

---

## PHASE 3: FIX APPROACHES

### FIX 1: Swallowed Exception (If diagnosis confirms)
**Problem**: Exception in loop is caught silently

**Solution**:
```python
# Add explicit exception handling around loop (line ~1090)
try:
    for turn in range(3, self.max_turns + 1):
        try:
            self.turn = turn
            # ... all existing loop code ...
        except Exception as e:
            self.log(f"ERROR: Turn {turn} failed with {type(e).__name__}: {e}", level="ERROR")
            import traceback
            self.log(f"Full traceback:\n{traceback.format_exc()}", level="ERROR")
            # Re-raise to preserve control flow
            raise
except Exception as outer_e:
    self.log(f"CRITICAL: Loop interrupted by {type(outer_e).__name__}: {outer_e}", level="ERROR")
    # Try to gracefully finish vs hard fail
    if "cancel scope" in str(outer_e).lower():
        self.log("Async coordination issue detected - attempting to finalize", level="WARNING")
    else:
        raise  # Non-async errors should bubble up
```

**Testing**: Add synthetic exception to confirm it bubbles up

---

### FIX 2: Early Return/Break (If diagnosis confirms)
**Problem**: Code exits loop before Turn 3

**Solution 1 - Check loop execution**:
```python
# At line 1091, explicitly log and guard
loop_start_turn = 3
self.log(f"DEBUG: Loop starting - will process turns {loop_start_turn} to {self.max_turns}", level="DEBUG")

if loop_start_turn > self.max_turns:
    self.log(f"ERROR: Loop range invalid - start={loop_start_turn} > max={self.max_turns}", level="ERROR")
    # This shouldn't happen, but guard against it
    pass
else:
    turns_executed = 0
    for turn in range(loop_start_turn, self.max_turns + 1):
        turns_executed += 1
        self.log(f"DEBUG: Executing turn {turns_executed} of {self.max_turns - loop_start_turn + 1}", level="DEBUG")
        # ... existing code ...

    self.log(f"DEBUG: Loop completed, executed {turns_executed} turns", level="DEBUG")
```

**Solution 2 - Remove premature returns**:
- Search for any `return` statements between line 1090 and 1200
- Ensure only the final `return 0` at line 1220 exits

---

### FIX 3: SDK Hang (If diagnosis confirms)
**Problem**: Turn 2 or Turn 3 call hangs indefinitely

**Solution**: Add timeout wrapper
```python
async def _run_turn_with_timeout(self, prompt: str, timeout_seconds: float = 600) -> Tuple[int, str]:
    """Run turn with timeout protection (10 minutes default)."""
    try:
        return await asyncio.wait_for(
            self._run_turn_with_retry(prompt, max_retries=3),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        self.log(f"Turn timed out after {timeout_seconds}s", level="ERROR")
        return (1, f"Turn timeout ({timeout_seconds}s)")

# Replace all _run_turn_with_retry calls with _run_turn_with_timeout
```

---

### FIX 4: Empty Loop Range (If diagnosis confirms)
**Problem**: Loop skipped because max_turns < 3

**Solution**: Validate at __init__
```python
def __init__(self, sdk: str, prompt: str, max_turns: int = 10, ...):
    # Add after line 95
    if max_turns < 3:
        raise ValueError(f"max_turns must be >= 3 (got {max_turns})")
    self.max_turns = max_turns
```

---

### FIX 5: Async Coordination (If diagnosis confirms)
**Problem**: Single event loop gets poisoned after Turn 2

**Solution**: Reset loop state between turns
```python
# At line 1120 (beginning of loop body)
# Force garbage collection to clean up any lingering resources
import gc
gc.collect()
self.log(f"DEBUG: GC cleanup before turn {turn}", level="DEBUG")

# Also check event loop health
try:
    current_loop = asyncio.get_running_loop()
    self.log(f"DEBUG: Event loop is healthy, turn {turn} can proceed", level="DEBUG")
except RuntimeError as e:
    self.log(f"ERROR: Event loop is dead before turn {turn}: {e}", level="ERROR")
    raise
```

---

## PHASE 4: TEST PLAN

### Test 1: Basic Loop Execution (Simple)
```bash
# Command: Test that 3+ turns execute
amplihack --auto --prompt "List the files in the current directory" --max-turns 5
# Expected: See output for Turns 1, 2, 3, 4, 5
# Check: auto.log should show "Executing" phase at least once
```

### Test 2: Completion Signal (Simple)
```bash
# Command: Test that loop exits on completion
amplihack --auto --prompt "Print hello world" --max-turns 20
# Expected: Should complete by Turn 3-4, not go to 20
# Check: "auto-mode EVALUATION: COMPLETE" appears in output
```

### Test 3: Loop Exhaustion (Simple)
```bash
# Command: Test that loop completes at max_turns
amplihack --auto --prompt "Complex task requiring iteration" --max-turns 3
# Expected: Should do Turns 1, 2, 3 then exit with "Max turns reached"
# Check: auto.log shows Turn 3 execution
```

### Test 4: Exception Handling (Diagnostic)
```python
# Inject exception in Turn 3 by modifying test auto_mode.py:
# Add to _run_turn_with_retry at line 691 for turn 3 specifically:
if turn == 3:
    raise RuntimeError("Injected test exception for Turn 3")

# Run: amplihack --auto --prompt "test" --max-turns 5
# Expected: Should catch exception, log it, and either retry or fail cleanly
# Check: Exception appears in auto.log with traceback
```

### Test 5: Hang Detection (Diagnostic)
```bash
# Monitor with timeout
timeout 30s amplihack --auto --prompt "test" --max-turns 5
# Expected: Should NOT hang, should complete or fail within 30s
# Check: Exit code is 0 or 1, not 124 (timeout)
```

### Test 6: Event Loop Stress (Complex)
```bash
# Generate many turns to stress event loop
amplihack --auto --prompt "Generate a todo list with 100 items" --max-turns 20
# Expected: All 20 turns should execute without loop degradation
# Check: Turn 20 log entry appears, timing doesn't degrade
```

---

## PHASE 5: REGRESSION PREVENTION

### Monitor Points
1. **Loop Entry Detection**
   - Add CI check: "Verify at least 3 turns execute in auto mode"
   - Script: Count "Executing" log entries in auto.log

2. **Event Loop Health**
   - Add debug flag: `--debug-async` to log event loop state
   - CI check: No "Event loop is dead" messages

3. **Turn Completion Times**
   - Track average turn duration
   - Alert if Turn 3+ average > 2x Turn 1-2 average

4. **Exception Tracking**
   - Parse auto.log for unexpected exceptions
   - Fail CI if "Exception escaped loop" appears

5. **Timeout Monitoring**
   - Add `--turn-timeout` parameter (default 600s)
   - Fail CI if any turn exceeds timeout

### Test Coverage
```python
# Add to tests/unit/test_auto_mode_execution.py:

def test_loop_executes_at_least_three_turns():
    """Verify Turn 3+ executes, not just Turn 1-2."""
    # Run auto mode with max_turns=5
    # Assert that logs show Turn 3 start

def test_exception_in_turn_is_logged():
    """Verify exceptions in turns are not swallowed."""
    # Inject exception in Turn 3
    # Assert exception appears in logs and is propagated

def test_completion_signal_breaks_loop():
    """Verify loop exits on completion."""
    # Mock eval_result with completion signal
    # Assert loop breaks before max_turns

def test_loop_range_validated():
    """Verify max_turns >= 3."""
    # Try max_turns=2
    # Assert raises ValueError or similar
```

---

## EXECUTION ORDER

### Day 1: Diagnosis
1. Add all logging points to auto_mode.py
2. Run simple test (Test 1) and capture logs
3. Search logs for loop entry/exit messages
4. Identify which suspect is actual root cause

### Day 2: Fix Implementation
1. Implement fix for confirmed root cause
2. Run all 6 tests to verify fix
3. Check no regressions in other modes (sync mode, subprocess)

### Day 3: Regression Prevention
1. Add regression tests to CI
2. Update monitoring/alerting
3. Document findings in DISCOVERIES.md

---

## SUCCESS CRITERIA

1. **Turn 3+ executes**: Auto mode with `--max-turns 10` should have 10 turns in logs
2. **No hangups**: Process completes in < 60 seconds for simple prompts
3. **Clean failure**: Any errors are logged and visible, not swallowed
4. **Completion signal works**: Loop exits early on completion, not just at max_turns
5. **Regression tests pass**: CI catches if bug re-appears

---

## Key Files to Monitor

- `/src/amplihack/launcher/auto_mode.py` (main code, lines 994-1220)
- `/src/amplihack/launcher/auto_mode.py` (logging additions, throughout)
- `logs/auto_mode_execution_debug.log` (generated during testing)
- Tests: `tests/unit/test_auto_mode_execution.py` (create if needed)

---

## Likely Root Cause Prediction

**Based on code review**: The bug is most likely **SWALLOWED EXCEPTION** (Suspect 1):

- The loop code structure doesn't have explicit exception handling
- `_run_turn_with_retry()` catches exceptions and returns them as error codes
- If `_run_turn_with_retry()` encounters an exception it can't retry, it likely catches it
- But there's no explicit error check after each turn's result
- **Most telling**: The process exits cleanly with code 0, suggesting normal flow, not crash

**Hypothesis**: An exception occurs in Turn 3's SDK call, gets caught by `_run_turn_with_retry()`, returns error code, but the loop doesn't check that code and may hit an exception handler that breaks the loop.

**To confirm**: Add logging at lines 1147-1149 and 1180 to see if Turn 3 `_run_turn_with_retry` calls are even reached.
