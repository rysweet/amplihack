# Auto Mode Instrumentation Reference

**Purpose**: Specific code locations and exact logging statements to add for diagnosing the execution bug

---

## File: `/src/amplihack/launcher/auto_mode.py`

### Region 1: Pre-Loop Setup (Lines 1088-1091)

**Current code (lines 1083-1091)**:
```python
            code, plan = await self._run_turn_with_retry(turn2_prompt, max_retries=3)
            if code != 0:
                self.log(f"Error creating plan (exit {code})")
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
```

**Add AFTER line 1089 (before the for loop)**:
```python
            # INSTRUMENTATION: Log loop entry with range details
            self.log(f"DIAG: Loop entry - range(3, {self.max_turns + 1}) => turns {3} to {self.max_turns}", level="DEBUG")
            self.log(f"DIAG: Loop will execute {max(0, self.max_turns - 2)} iterations", level="DEBUG")

            # Safety check: verify loop range is valid
            if 3 > self.max_turns:
                self.log(f"DIAG: WARNING - loop range is empty (3 > {self.max_turns})", level="WARNING")

            # INSTRUMENTATION: Check event loop status
            try:
                loop = asyncio.get_running_loop()
                self.log(f"DIAG: Event loop is active and healthy before loop", level="DEBUG")
            except RuntimeError as e:
                self.log(f"DIAG: ERROR - no running event loop: {e}", level="ERROR")
                return 1
```

**Expected output when working**:
```
[AUTO CLAUDE] DIAG: Loop entry - range(3, 11) => turns 3 to 10
[AUTO CLAUDE] DIAG: Loop will execute 8 iterations
[AUTO CLAUDE] DIAG: Event loop is active and healthy before loop
```

---

### Region 2: Loop Body Entry (Line ~1091, inside loop)

**Current code (lines 1091-1120)**:
```python
            for turn in range(3, self.max_turns + 1):
                self.turn = turn

                # Check if fork needed before turn execution
                if self.fork_manager.should_fork():
                    # ... fork handling ...

                self.message_capture.set_phase(
                    "executing", self.turn
                )  # Set phase for message capture
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_turn(self.turn)
                self.log(f"\n--- {self._progress_str('Executing')} Execute ---")
```

**Add AFTER line 1092 (after `self.turn = turn`)**:
```python
                # INSTRUMENTATION: Confirm loop iteration started
                self.log(f"DIAG: Loop iteration {turn} started (max_turns={self.max_turns})", level="DEBUG")
                try:
                    loop = asyncio.get_running_loop()
                    self.log(f"DIAG: Event loop still active at turn {turn}", level="DEBUG")
                except RuntimeError as e:
                    self.log(f"DIAG: CRITICAL - event loop lost at turn {turn}: {e}", level="ERROR")
                    raise
```

**Expected output**:
```
[AUTO CLAUDE] DIAG: Loop iteration 3 started (max_turns=10)
[AUTO CLAUDE] DIAG: Event loop still active at turn 3
```

---

### Region 3: Pre-Execute Call (Before line 1147)

**Current code (lines 1126-1149)**:
```python
                # Execute
                execute_prompt = f"""{self._build_philosophy_context()}
...
Current Turn: {turn}/{self.max_turns}"""

                code, execution_output = await self._run_turn_with_retry(
                    execute_prompt, max_retries=3
                )
```

**Add BEFORE line 1147 (before the await)**:
```python
                # INSTRUMENTATION: Log execution attempt
                self.log(f"DIAG: About to execute turn {turn}", level="DEBUG")
                self.log(f"DIAG: execute_prompt length: {len(execute_prompt)} chars", level="DEBUG")

                execution_start = time.time()
```

**Add AFTER line 1149 (after the await)**:
```python
                execution_elapsed = time.time() - execution_start
                self.log(f"DIAG: Execute call returned - code={code}, output_len={len(execution_output)}, elapsed={execution_elapsed:.1f}s", level="DEBUG")
                if code != 0:
                    self.log(f"DIAG: Execute failed with code {code}", level="WARNING")
                    self.log(f"DIAG: Error output: {execution_output[:200]}", level="DEBUG")
```

**Expected output**:
```
[AUTO CLAUDE] DIAG: About to execute turn 3
[AUTO CLAUDE] DIAG: execute_prompt length: 3821 chars
[AUTO CLAUDE] DIAG: Execute call returned - code=0, output_len=2145, elapsed=12.3s
```

---

### Region 4: Pre-Evaluate Call (Before line 1180)

**Current code (lines 1153-1180)**:
```python
                # Evaluate
                self.message_capture.set_phase(
                    "evaluating", self.turn
                )  # Set phase for message capture
                self.log(f"--- {self._progress_str('Evaluating')} Evaluate ---")
                eval_prompt = f"""{self._build_philosophy_context()}
...
Current Turn: {turn}/{self.max_turns}"""

                code, eval_result = await self._run_turn_with_retry(eval_prompt, max_retries=3)
```

**Add BEFORE line 1180 (before the await)**:
```python
                # INSTRUMENTATION: Log evaluation attempt
                self.log(f"DIAG: About to evaluate turn {turn}", level="DEBUG")
                self.log(f"DIAG: eval_prompt length: {len(eval_prompt)} chars", level="DEBUG")

                eval_start = time.time()
```

**Add AFTER line 1180 (after the await)**:
```python
                eval_elapsed = time.time() - eval_start
                self.log(f"DIAG: Evaluate call returned - code={code}, result_len={len(eval_result)}, elapsed={eval_elapsed:.1f}s", level="DEBUG")
                self.log(f"DIAG: Eval result preview: {eval_result[:150]}...", level="DEBUG")
```

**Expected output**:
```
[AUTO CLAUDE] DIAG: About to evaluate turn 3
[AUTO CLAUDE] DIAG: eval_prompt length: 2234 chars
[AUTO CLAUDE] DIAG: Evaluate call returned - code=0, result_len=432, elapsed=8.5s
[AUTO CLAUDE] DIAG: Eval result preview: auto-mode EVALUATION: IN PROGRESS...
```

---

### Region 5: Completion Check (Lines 1182-1192)

**Current code**:
```python
                # Check completion - look for strong completion signals
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
```

**Add BEFORE line 1182 (before the if)**:
```python
                # INSTRUMENTATION: Log completion check
                eval_lower = eval_result.lower()
                self.log(f"DIAG: Checking for completion signals in eval", level="DEBUG")

                has_complete = "auto-mode evaluation: complete" in eval_lower
                has_achieved = "objective achieved" in eval_lower
                has_criteria = "all criteria met" in eval_lower

                self.log(f"DIAG: Signals found - complete={has_complete}, achieved={has_achieved}, criteria={has_criteria}", level="DEBUG")
```

**Expected output**:
```
[AUTO CLAUDE] DIAG: Checking for completion signals in eval
[AUTO CLAUDE] DIAG: Signals found - complete=False, achieved=False, criteria=False
```

Or if completing:
```
[AUTO CLAUDE] DIAG: Signals found - complete=True, achieved=False, criteria=False
```

---

### Region 6: Loop Exit (After line 1198)

**Current code (lines 1194-1198)**:
```python
                if turn >= self.max_turns:
                    self.log("Max turns reached")
                    if self.ui_enabled and hasattr(self, "state"):
                        self.state.update_status("completed")
                    break
```

**Add AFTER line 1198 (after the loop ends)**:
```
            # INSTRUMENTATION: Confirm loop completion
            self.log(f"DIAG: Loop exited normally after {self.turn} turns", level="DEBUG")
```

**Expected output**:
```
[AUTO CLAUDE] DIAG: Loop exited normally after 5 turns
```

---

### Region 7: Exception Wrapper (Wrap entire try block)

**Current code (lines 1027-1219)**:
```python
        try:
            # Turn 1: Clarify objective
            ...
        finally:
            # Export session transcript before stop hook
            self._export_session_transcript()
            self.run_hook("stop")

        return 0
```

**Add exception handler INSIDE the existing try block, at line 1027-1028**:
```python
        try:
            # INSTRUMENTATION: Capture any exceptions that escape the turns
            try:
                # Turn 1: Clarify objective
                # ... (rest of existing code) ...
            except Exception as loop_exception:
                self.log(f"DIAG: CRITICAL EXCEPTION escaped from turns: {type(loop_exception).__name__}", level="ERROR")
                self.log(f"DIAG: Exception message: {loop_exception}", level="ERROR")
                import traceback
                self.log(f"DIAG: Traceback:\n{traceback.format_exc()}", level="ERROR")
                # Don't re-raise - we're in the finally block alternative
                # Just ensure we return error code
                return 1
```

**Expected output** (if exception occurs):
```
[AUTO CLAUDE] DIAG: CRITICAL EXCEPTION escaped from turns: TimeoutError
[AUTO CLAUDE] DIAG: Exception message: Turn timed out after 600 seconds
[AUTO CLAUDE] DIAG: Traceback:
Traceback (most recent call last):
  ...
```

---

## Log Parsing Guide

### Search for Debug Output
```bash
# Extract all diagnostic output
grep "DIAG:" logs/auto_claude_*.log

# Check if loop was entered
grep "Loop entry" logs/auto_claude_*.log

# Check if Turn 3+ was attempted
grep "Loop iteration [3-9]" logs/auto_claude_*.log

# Check if any exceptions occurred
grep "CRITICAL EXCEPTION\|ERROR" logs/auto_claude_*.log

# Timeline view
grep "DIAG:" logs/auto_claude_*.log | head -30
```

### Expected vs Broken Output

**Working (should show)**:
```
Loop entry - range(3, 11)
Loop iteration 3 started
About to execute turn 3
Execute call returned - code=0
About to evaluate turn 3
Evaluate call returned - code=0
Loop iteration 4 started
... (and so on until max_turns or completion)
```

**Broken (will show something like)**:
```
Loop entry - range(3, 11)
(nothing after this - loop never executed)
```

Or:

```
Loop entry - range(3, 11)
Loop iteration 3 started
About to execute turn 3
(hangs here forever)
```

Or:

```
Loop entry - range(3, 11)
Loop iteration 3 started
About to execute turn 3
Execute call returned - code=1
ERROR - Execute failed with code 1
(loop exits without trying turn 4)
```

---

## Installation Instructions

### Step 1: Modify auto_mode.py
1. Open `/src/amplihack/launcher/auto_mode.py`
2. Add each logging block from Regions 1-7 above
3. Keep line numbers roughly aligned (don't worry about exact offset)

### Step 2: Run Test
```bash
cd /home/azureuser/src/amplihack/worktrees/feat/issue-1425-auto-mode-execution-fix

# Run auto mode with simple prompt
amplihack --auto --prompt "print hello world" --max-turns 5
```

### Step 3: Review Logs
```bash
# Find the most recent log
LOG_FILE=$(ls -t logs/auto_claude_*.log | head -1)

# View all diagnostics
grep "DIAG:" $LOG_FILE

# Full log
cat $LOG_FILE
```

---

## Diagnostic Checklist

- [ ] Loop entry logged with correct range
- [ ] At least one loop iteration entry logged
- [ ] Execute call logged for Turn 3
- [ ] Evaluate call logged for Turn 3
- [ ] Loop exit logged or completion signal logged
- [ ] No exceptions in DIAG logs
- [ ] No "event loop lost" errors

If any of these fail, the diagnostic logs will point to the root cause.
