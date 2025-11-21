# Auto Mode Fix Designs

**Purpose**: Detailed implementation specifications for fixing the auto mode execution bug

---

## Fix Design 1: Exception Capture and Logging (Suspect 1 - Swallowed Exception)

### Root Cause
Exception occurs inside the main execution loop but is caught silently by `_run_turn_with_retry()` or by implicit Python exception handling, causing the loop to exit cleanly without processing turns 3+.

### Problem Manifestation
- Process exits with code 0 (success)
- Logs show only Turns 1-2 completed
- No error messages in logs
- `_run_turn_with_retry()` returns error code but loop doesn't check it

### Fix Implementation

**File**: `/src/amplihack/launcher/auto_mode.py`

**Location**: Lines 1090-1200 (the main execution loop)

**Code Changes**:

```python
# ORIGINAL CODE (lines 1090-1200)
            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn

                # ... existing fork check and setup code ...

                code, execution_output = await self._run_turn_with_retry(
                    execute_prompt, max_retries=3
                )
                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # ... existing evaluation code ...

                code, eval_result = await self._run_turn_with_retry(eval_prompt, max_retries=3)

                # ... existing completion check ...


# FIXED CODE
            # Turns 3+: Execute and evaluate
            loop_iterations_executed = 0
            try:
                for turn in range(3, self.max_turns + 1):
                    try:
                        self.turn = turn
                        loop_iterations_executed += 1

                        self.log(f"DIAG: Turn {turn} starting (loop iteration {loop_iterations_executed})", level="DEBUG")

                        # ... existing fork check and setup code ...

                        # Execute with error checking
                        self.log(f"DIAG: Calling _run_turn_with_retry for execute", level="DEBUG")
                        code, execution_output = await self._run_turn_with_retry(
                            execute_prompt, max_retries=3
                        )

                        if code != 0:
                            self.log(f"ERROR: Execution failed with code {code}")
                            self.log(f"DIAG: Execution error output: {execution_output[:500]}", level="DEBUG")
                            # Log but continue to evaluation to check if we should stop
                            continue  # Skip to next turn instead of evaluating this failed turn

                        self.log(f"DIAG: Execute succeeded, output length={len(execution_output)}", level="DEBUG")

                        # Evaluate
                        self.log(f"DIAG: Calling _run_turn_with_retry for evaluate", level="DEBUG")
                        code, eval_result = await self._run_turn_with_retry(eval_prompt, max_retries=3)

                        if code != 0:
                            self.log(f"ERROR: Evaluation failed with code {code}")
                            self.log(f"DIAG: Evaluation error output: {eval_result[:500]}", level="DEBUG")
                            # Continue loop on eval failure too
                            continue

                        # ... existing completion check ...
                        eval_lower = eval_result.lower()
                        if (
                            "auto-mode evaluation: complete" in eval_lower
                            or "objective achieved" in eval_lower
                            or "all criteria met" in eval_lower
                        ):
                            self.log("✓ Objective achieved!")
                            if self.ui_enabled and hasattr(self, "state"):
                                self.state.update_status("completed")
                            break

                        if turn >= self.max_turns:
                            self.log("Max turns reached")
                            if self.ui_enabled and hasattr(self, "state"):
                                self.state.update_status("completed")
                            break

                        self.log(f"DIAG: Turn {turn} completed successfully", level="DEBUG")

                    except Exception as turn_exception:
                        self.log(
                            f"ERROR: Turn {turn} failed with {type(turn_exception).__name__}: {turn_exception}",
                            level="ERROR"
                        )
                        import traceback
                        self.log(f"Traceback: {traceback.format_exc()}", level="ERROR")
                        # Re-raise to allow outer handler to decide what to do
                        raise

            except Exception as loop_exception:
                # Outer handler for critical exceptions
                self.log(
                    f"CRITICAL: Loop was interrupted by {type(loop_exception).__name__}: {loop_exception}",
                    level="ERROR"
                )

                # Check if this is an expected async cleanup exception
                if "cancel scope" in str(loop_exception).lower() or isinstance(loop_exception, GeneratorExit):
                    self.log("DIAG: Expected async cleanup during graceful shutdown", level="DEBUG")
                    # Don't propagate - continue to summary
                else:
                    # Unexpected exception - log and continue but signal error
                    self.log(f"DIAG: Executed {loop_iterations_executed} turns before failure", level="WARNING")
                    # Don't return 1 yet - try to generate summary and gracefully exit

            self.log(f"DIAG: Loop execution completed - {loop_iterations_executed} iterations executed", level="DEBUG")
```

### Verification
Add to test file:
```python
def test_exception_in_turn_breaks_with_error():
    """Verify that exceptions in turns are logged and handled."""
    # Create auto mode instance
    # Mock _run_turn_with_retry to raise exception on turn 3
    # Run auto mode
    # Assert: Logs contain error for turn 3
    # Assert: Process exits with graceful handling
```

---

## Fix Design 2: Explicit Loop Guard (Suspect 4 - Empty Loop Range)

### Root Cause
Loop range `range(3, self.max_turns + 1)` is empty because `self.max_turns < 3`

### Problem Manifestation
- Process exits cleanly with code 0
- Only 2 turns (1 and 2) are shown in logs
- No execution or evaluation phases appear
- User expected 10 turns but got 2

### Fix Implementation

**File**: `/src/amplihack/launcher/auto_mode.py`

**Location**: Lines 76-105 (__init__ method)

**Code Changes**:

```python
# ORIGINAL CODE (lines 80-95)
    def __init__(
        self,
        sdk: str,
        prompt: str,
        max_turns: int = 10,
        working_dir: Optional[Path] = None,
        ui_mode: bool = False,
    ):
        """Initialize auto mode.

        Args:
            sdk: "claude", "copilot", or "codex"
            prompt: User's initial prompt
            max_turns: Max iterations (default 10)
            working_dir: Working directory (defaults to current dir)
            ui_mode: Enable interactive UI mode (requires Rich library)
        """
        self.sdk = sdk
        self.prompt = prompt
        self.max_turns = max_turns
        self.turn = 0


# FIXED CODE
    def __init__(
        self,
        sdk: str,
        prompt: str,
        max_turns: int = 10,
        working_dir: Optional[Path] = None,
        ui_mode: bool = False,
    ):
        """Initialize auto mode.

        Args:
            sdk: "claude", "copilot", or "codex"
            prompt: User's initial prompt
            max_turns: Max iterations (default 10, minimum 3 for meaningful execution)
            working_dir: Working directory (defaults to current dir)
            ui_mode: Enable interactive UI mode (requires Rich library)

        Raises:
            ValueError: If max_turns < 3 (insufficient for Turn 1 + Turn 2 + Turn 3+)
        """
        # GUARD: Validate max_turns before using it
        if max_turns < 3:
            raise ValueError(
                f"max_turns must be at least 3 (required: Turn 1 Clarify + Turn 2 Plan + Turn 3+ Execute). "
                f"Got max_turns={max_turns}"
            )

        self.sdk = sdk
        self.prompt = prompt
        self.max_turns = max_turns
        self.turn = 0
```

### Why This Matters
- **Turn 1**: Clarify objective
- **Turn 2**: Create plan
- **Turn 3+**: Execute and evaluate (minimum 1 iteration needed)

So minimum viable `max_turns = 3`.

### Additional Guard at Loop Time

**Location**: Before the main execution loop (line ~1090)

**Code**:
```python
            # Guard: Ensure loop will actually execute
            if 3 > self.max_turns:
                self.log(f"ERROR: Loop range invalid - loop starts at 3 but max_turns is {self.max_turns}", level="ERROR")
                return 1  # This should never happen due to __init__ guard, but be defensive

            loop_range_size = self.max_turns - 3 + 1
            self.log(f"DIAG: Loop will execute {loop_range_size} iterations (turns 3 to {self.max_turns})", level="DEBUG")

            for turn in range(3, self.max_turns + 1):
                # ... loop body ...
```

### Verification
```python
def test_auto_mode_rejects_max_turns_less_than_3():
    """Verify that AutoMode rejects max_turns < 3."""
    with pytest.raises(ValueError):
        AutoMode(sdk="claude", prompt="test", max_turns=2)

    with pytest.raises(ValueError):
        AutoMode(sdk="claude", prompt="test", max_turns=1)

    # These should NOT raise
    AutoMode(sdk="claude", prompt="test", max_turns=3)
    AutoMode(sdk="claude", prompt="test", max_turns=10)
```

---

## Fix Design 3: Timeout Protection (Suspect 3 - SDK Hang)

### Root Cause
Turn 3 SDK call hangs indefinitely, blocking execution loop

### Problem Manifestation
- Process appears to hang after Turn 2
- CPU usage stays low (not spinning)
- Process doesn't exit, must be killed with Ctrl+C
- No timeout errors in logs (because there is no timeout)

### Fix Implementation

**File**: `/src/amplihack/launcher/auto_mode.py`

**Location**: Add new method around line 680, modify calls at lines 1147 and 1180

**New Method**:
```python
    async def _run_turn_with_timeout(
        self,
        prompt: str,
        timeout_seconds: float = 600.0,
        max_retries: int = 3,
    ) -> Tuple[int, str]:
        """Execute turn with timeout protection.

        Wraps _run_turn_with_retry with asyncio.wait_for timeout.
        If turn takes longer than timeout_seconds, raises TimeoutError.

        Args:
            prompt: The prompt for this turn
            timeout_seconds: Timeout in seconds (default 10 minutes)
            max_retries: Max retry attempts for transient errors

        Returns:
            (exit_code, output_text)
        """
        try:
            self.log(f"DIAG: Running turn with {timeout_seconds}s timeout", level="DEBUG")
            return await asyncio.wait_for(
                self._run_turn_with_retry(prompt, max_retries=max_retries),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            self.log(f"ERROR: Turn exceeded timeout ({timeout_seconds}s)", level="ERROR")
            self.log("This could indicate an SDK hang or extremely slow response", level="ERROR")
            return (1, f"Turn timeout: exceeded {timeout_seconds} seconds")
        except Exception as e:
            # Re-raise any other exceptions
            self.log(f"ERROR: Turn with timeout failed: {type(e).__name__}: {e}", level="ERROR")
            raise
```

**Replace calls to _run_turn_with_retry in execution loop**:

```python
# OLD (line 1147-1149)
                code, execution_output = await self._run_turn_with_retry(
                    execute_prompt, max_retries=3
                )

# NEW
                code, execution_output = await self._run_turn_with_timeout(
                    execute_prompt,
                    timeout_seconds=600.0,  # 10 minutes per turn
                    max_retries=3
                )


# OLD (line 1180)
                code, eval_result = await self._run_turn_with_retry(eval_prompt, max_retries=3)

# NEW
                code, eval_result = await self._run_turn_with_timeout(
                    eval_prompt,
                    timeout_seconds=300.0,  # 5 minutes for evaluation (usually faster)
                    max_retries=2  # Fewer retries for eval
                )
```

### Configuration

Add timeout configuration to __init__:
```python
        # Timeout configuration (seconds)
        self.turn_execute_timeout = 600  # 10 minutes for execution turns
        self.turn_evaluate_timeout = 300  # 5 minutes for evaluation turns
```

Then use:
```python
                code, execution_output = await self._run_turn_with_timeout(
                    execute_prompt,
                    timeout_seconds=self.turn_execute_timeout,
                    max_retries=3
                )
```

### Verification
```python
def test_turn_timeout_triggers():
    """Verify timeout protection works."""
    # Create a mock that takes > 10 seconds
    # Run auto mode
    # Assert: ERROR logged about timeout
    # Assert: Returns error code 1, not hangs
```

---

## Fix Design 4: Event Loop Health Check (Suspect 5 - Async Coordination)

### Root Cause
Single event loop becomes corrupted or resource-limited after Turn 2

### Problem Manifestation
- Turns 1 and 2 work fine
- Turn 3 immediately fails with cryptic async errors
- Error might be "RuntimeError: no running event loop" or similar
- Problem appears after some number of turns (not always Turn 3)

### Fix Implementation

**File**: `/src/amplihack/launcher/auto_mode.py`

**Location**: Add method around line 680, call before each turn

**New Method**:
```python
    async def _check_event_loop_health(self, turn: int) -> bool:
        """Check if event loop is healthy and log status.

        Returns True if healthy, False if degraded.
        Logs warnings for troubleshooting.
        """
        try:
            loop = asyncio.get_running_loop()

            # Check for obvious problems
            if loop._stopping:
                self.log(f"WARNING: Event loop is stopping (turn {turn})", level="WARNING")
                return False

            # Log basic loop info
            self.log(f"DIAG: Event loop health check - turn {turn}: HEALTHY", level="DEBUG")

            # Optional: Force garbage collection between turns to clean up resources
            import gc
            collected = gc.collect()
            if collected > 0:
                self.log(f"DIAG: Garbage collection freed {collected} objects before turn {turn}", level="DEBUG")

            return True

        except RuntimeError as e:
            self.log(f"ERROR: Event loop health check failed at turn {turn}: {e}", level="ERROR")
            return False
        except Exception as e:
            self.log(f"ERROR: Unexpected error during event loop health check: {e}", level="ERROR")
            return False
```

**Call before each turn**:

```python
            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn

                # Health check before processing turn
                if not await self._check_event_loop_health(turn):
                    self.log(f"ERROR: Event loop degraded before turn {turn}, stopping", level="ERROR")
                    break

                # ... rest of loop body ...
```

### Additional Resource Cleanup

Between turns, add:
```python
                # After evaluation, before next iteration
                if turn < self.max_turns:  # Don't bother on last turn
                    # Clear any accumulated message state
                    gc.collect()
                    await asyncio.sleep(0.1)  # Brief yield to event loop
                    self.log(f"DIAG: Event loop yield before turn {turn + 1}", level="DEBUG")
```

### Verification
```python
def test_event_loop_remains_healthy():
    """Verify event loop doesn't degrade over multiple turns."""
    # Run auto mode with max_turns=10
    # Assert: All 10 turns have "HEALTHY" or "loop health check" logs
    # Assert: No "EventLoop degraded" errors
```

---

## Fix Design 5: Improved Error Reporting (All Suspects)

### New Logging Infrastructure

**File**: `/src/amplihack/launcher/auto_mode.py`

**Location**: Add new method around line 185

**New Method**:
```python
    def _log_diagnostic_summary(self) -> None:
        """Generate diagnostic summary of session state.

        Called before exiting to help debug issues.
        """
        self.log("\n" + "="*60, level="INFO")
        self.log("DIAGNOSTIC SUMMARY", level="INFO")
        self.log("="*60, level="INFO")
        self.log(f"SDK: {self.sdk}", level="INFO")
        self.log(f"Turns executed: {self.turn}/{self.max_turns}", level="INFO")
        self.log(f"Elapsed time: {self._format_elapsed(time.time() - self.start_time)}", level="INFO")
        self.log(f"Session: {self.log_dir.name}", level="INFO")
        self.log(f"Log file: {self.log_dir}/auto.log", level="INFO")

        if self.turn < 3:
            self.log("WARNING: Loop did not reach execution phase (Turn 3+)", level="WARNING")
            self.log("This may indicate an issue with Turn 1 or Turn 2", level="WARNING")

        self.log("="*60, level="INFO")
```

**Call before return**:

```python
    async def _run_async_session(self) -> int:
        # ... existing code ...

        finally:
            # BEFORE exporting transcript
            self._log_diagnostic_summary()

            # Export session transcript before stop hook
            self._export_session_transcript()
```

---

## Summary of Fixes

| Suspect | Fix | Complexity | Confidence |
|---------|-----|-----------|-----------|
| Swallowed Exception | Exception capture + logging | Low | 85% |
| Loop Range Empty | Input validation guard | Minimal | 15% |
| SDK Hang | Timeout wrapper | Medium | 50% |
| Async Coordination | Loop health check | Medium | 45% |
| Early Break | Explicit error checking | Low | 60% |

### Recommended Implementation Order

1. **First**: Fix 1 (Exception capture) - Most likely, helps debug all others
2. **Second**: Fix 2 (Loop range guard) - Minimal code, catches edge case
3. **Third**: Fix 5 (Diagnostic summary) - Helps debug if not fully fixed yet
4. **If needed**: Fix 3 (Timeout) + Fix 4 (Health check) for edge cases

---

## Testing Each Fix

See TEST_PLAN.md for detailed testing procedures for each fix.
