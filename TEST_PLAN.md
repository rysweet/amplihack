# Auto Mode Execution Bug - Test Plan

**Purpose**: Systematic validation that fixes work and prevent regressions

---

## Pre-Fix Baseline Tests

Run these BEFORE implementing fixes to confirm the bug:

### Baseline Test 1: Three Turns Execution (MUST FAIL)

**Command**:
```bash
cd /home/azureuser/src/amplihack/worktrees/feat/issue-1425-auto-mode-execution-fix
amplihack --auto --max-turns 5 --prompt "print 'hello world'"
```

**Expected (Currently Broken)**:
- Output shows only Turn 1 (Clarifying) and Turn 2 (Planning)
- No "Executing" or "Evaluating" phases appear
- Exit code: 0 (success)
- Process completes in < 30 seconds

**Verification**:
```bash
# Count how many turns executed
grep -c "--- \[Turn.*Planning\|Executing\|Evaluating" auto.log

# Should show: 1 (only Turn 2)
# Goal: Should show: 5+ (Turns 3, 4, 5 with execute + evaluate)
```

### Baseline Test 2: Log Entry Check

**Command**:
```bash
grep "Starting auto mode with Claude SDK (max 5 turns)" auto.log
grep "Turns 3+: Execute and evaluate" auto.log
```

**Expected (Currently Broken)**:
- First grep matches (session starts correctly)
- Second grep doesn't match or loop never enters
- No "Loop iteration 3" messages

---

## Post-Fix Validation Tests

Run these AFTER implementing fixes to confirm they work:

### Validation Test 1: Basic Five-Turn Execution

**Purpose**: Verify loop executes Turn 3+

**Command**:
```bash
rm -f logs/auto_claude_*/*.log
amplihack --auto --max-turns 5 --prompt "List files in current directory"
```

**Success Criteria**:
- [ ] Turn 3 (Executing) appears in output
- [ ] Turn 3 (Evaluating) appears in output
- [ ] At least one iteration of execute+evaluate completes
- [ ] Exit code: 0
- [ ] Completes in < 60 seconds

**Failure Patterns** (if any occur, fix didn't work):
- Only Turns 1-2 shown → Exception still swallowed
- Process hangs → Timeout issue
- Exit code 1 → Unhandled exception

**Log Check**:
```bash
LOG=$(ls -t logs/auto_claude_*/auto.log | head -1)
grep -E "Turn [3-9].*Executing|Turn [3-9].*Evaluating" $LOG
# Should match at least 2 lines
```

---

### Validation Test 2: Completion Signal Early Exit

**Purpose**: Verify loop exits early on completion signal

**Command**:
```bash
rm -f logs/auto_claude_*/*.log
amplihack --auto --max-turns 20 --prompt "Create a simple hello world function"
```

**Success Criteria**:
- [ ] Process completes in < 120 seconds (not 20 full turns)
- [ ] Output includes "Objective achieved" or similar
- [ ] Final turn number < 20 (e.g., completed at turn 5 or 6)
- [ ] No "Max turns reached" message
- [ ] Exit code: 0

**Failure Patterns**:
- Runs all 20 turns → Completion signal not recognized
- Hangs waiting for timeout → Timeout too long

**Log Check**:
```bash
LOG=$(ls -t logs/auto_claude_*/auto.log | head -1)
FINAL_TURN=$(grep "Turn [0-9]*/20" $LOG | tail -1 | grep -o "Turn [0-9]*" | tail -1)
echo $FINAL_TURN
# Should be < 20, e.g., "Turn 8"
```

---

### Validation Test 3: Max Turns Respected

**Purpose**: Verify loop doesn't go past max_turns

**Command**:
```bash
rm -f logs/auto_claude_*/*.log
amplihack --auto --max-turns 3 --prompt "test"
```

**Success Criteria**:
- [ ] Exactly 3 turns in output (Turn 1, Turn 2, Turn 3)
- [ ] No Turn 4 in logs
- [ ] Output contains "Max turns reached"
- [ ] Exit code: 0

**Log Check**:
```bash
LOG=$(ls -t logs/auto_claude_*/auto.log | head -1)
grep -c "Turn [0-9]" $LOG
# Should be 3
```

---

### Validation Test 4: Min Turns Guard

**Purpose**: Verify max_turns < 3 is rejected

**Command** (should fail immediately):
```bash
amplihack --auto --max-turns 2 --prompt "test" 2>&1 | head -20
```

**Success Criteria**:
- [ ] Error message about max_turns minimum
- [ ] Process exits immediately with code 1
- [ ] No session directory created
- [ ] Error mentions "max_turns must be at least 3"

**Log Check**:
```bash
# Should exit with code 1
echo $?  # Should be 1
```

---

### Validation Test 5: Exception Logging

**Purpose**: Verify exceptions are logged and not swallowed

**Command**:
```bash
rm -f logs/auto_claude_*/*.log

# Create test script that injects exception
cat > /tmp/test_exception.py << 'EOF'
# Patch auto_mode to inject exception in Turn 3
import sys
sys.path.insert(0, 'src')
from amplihack.launcher.auto_mode import AutoMode

original_run_turn = AutoMode._run_turn_with_retry
async def patched_run_turn(self, prompt, max_retries=3):
    if "Execute" in prompt and self.turn == 3:
        raise RuntimeError("Injected test exception for diagnostic")
    return await original_run_turn(self, prompt, max_retries)

AutoMode._run_turn_with_retry = patched_run_turn

# Now run normal auto mode
amplihack --auto --max-turns 5 --prompt "test"
EOF

python /tmp/test_exception.py 2>&1
```

**Success Criteria**:
- [ ] Exception is logged in auto.log
- [ ] Error includes "ERROR: Turn 3 failed with RuntimeError"
- [ ] Process exits gracefully (code 0 or 1, not hang)
- [ ] No stack trace pollution in stdout

---

### Validation Test 6: Timeout Protection

**Purpose**: Verify turns have timeout protection

**Command**:
```bash
# Test with timeout wrapper active
rm -f logs/auto_claude_*/*.log

# Set short timeout for testing (normally 600s)
# This would require modifying auto_mode.py temporarily
# Or run full test and check logs for timeout handling

amplihack --auto --max-turns 5 --prompt "test"
```

**Success Criteria** (if timeout fix implemented):
- [ ] Logs contain "running turn with 600s timeout"
- [ ] No "turn timeout" errors for normal operations
- [ ] Process completes normally

---

### Validation Test 7: Event Loop Health

**Purpose**: Verify event loop remains healthy

**Command**:
```bash
rm -f logs/auto_claude_*/*.log
amplihack --auto --max-turns 10 --prompt "complex task"
```

**Success Criteria** (if health check implemented):
- [ ] Logs show "Event loop health check: HEALTHY" for all turns
- [ ] No "Event loop lost" errors
- [ ] All 10 turns execute without degradation
- [ ] Turn 10 completes as fast as Turn 3 (no slowdown)

---

## Simple Scenario Tests

Simple reproducible test cases:

### Simple Test A: "List Files" (5 turns)

**Objective**: Very simple task, should complete quickly

**Command**:
```bash
amplihack --auto --max-turns 5 --prompt "List the files in the current directory"
```

**Expected**: Completes in 10-20 seconds, shows Turn 3 executing

---

### Simple Test B: "Print Hello" (3 turns)

**Objective**: Minimal viable task

**Command**:
```bash
amplihack --auto --max-turns 3 --prompt "Print hello world to the console"
```

**Expected**: Completes in 5-15 seconds, shows exactly Turn 3

---

### Simple Test C: "Early Completion" (20 turns max)

**Objective**: Should stop before max

**Command**:
```bash
amplihack --auto --max-turns 20 --prompt "Say 'done' and stop"
```

**Expected**: Completes at Turn 3-5, shows "Objective achieved"

---

## Complex Scenario Tests

More realistic test cases:

### Complex Test A: "Feature Implementation"

**Objective**: Multi-step feature

**Command**:
```bash
amplihack --auto --max-turns 10 --prompt "Create a Python function that validates email addresses using regex"
```

**Expected**:
- Turns 1-2: Clarify and plan
- Turns 3-5: Implement, test, evaluate
- Completes by Turn 6-7 with completion signal

---

### Complex Test B: "Debugging Task"

**Objective**: Iterative problem-solving

**Command**:
```bash
amplihack --auto --max-turns 15 --prompt "Debug why our API endpoint returns 500 errors"
```

**Expected**:
- Multiple execute+evaluate cycles
- May require most turns before completion
- Shows iteration progress in logs

---

## Regression Tests (CI Integration)

Automated tests for CI pipeline:

### CI Test Suite: `tests/unit/test_auto_mode_fix.py`

```python
import pytest
import asyncio
from pathlib import Path
from amplihack.launcher.auto_mode import AutoMode

class TestAutoModeExecutionFix:
    """Regression tests for auto mode execution bug."""

    def test_loop_enters_turn_3(self):
        """Verify loop execution reaches Turn 3."""
        # Create AutoMode instance
        auto_mode = AutoMode(
            sdk="claude",
            prompt="test prompt",
            max_turns=5,
            working_dir=Path.cwd()
        )

        # Run in test mode (mock SDK calls)
        # Assert that loop iteration counter >= 1
        # Assert logs contain "Loop iteration 3"

    def test_max_turns_less_than_3_raises(self):
        """Verify max_turns < 3 raises ValueError."""
        with pytest.raises(ValueError, match="max_turns must be at least 3"):
            AutoMode(sdk="claude", prompt="test", max_turns=2)

    def test_exception_is_logged_not_swallowed(self):
        """Verify exceptions in turns are logged."""
        # Mock _run_turn_with_retry to raise in Turn 3
        # Run auto mode
        # Assert logs contain error for Turn 3
        # Assert process exits cleanly

    def test_five_turns_executes_at_least_3(self):
        """Verify 5-turn session includes Turn 3+."""
        # Run actual auto mode with max_turns=5
        # Assert final turn >= 3
        # Assert "Executing" phase appears in logs
```

---

## Performance Tests

### Performance Test 1: Turn Execution Time

**Purpose**: Ensure no performance regression

**Measurement**:
```bash
amplihack --auto --max-turns 5 --prompt "test" 2>&1 | grep "DIAG:"
# Look for execution times

# Expected: Each turn takes 5-30 seconds (depends on SDK)
# Bad: Turn 3 takes > 2 minutes or hangs
```

### Performance Test 2: Total Session Time

**Command**:
```bash
time amplihack --auto --max-turns 5 --prompt "test"
```

**Expected**:
- < 90 seconds for 5 turns (roughly 18s per turn average)
- Real time close to user time (no background delays)
- No significant pause between turns

---

## Manual Verification Checklist

After implementing fixes, run through this checklist:

- [ ] **Turns 3+ Execute**: At least Turn 3 shows in logs with Executing phase
- [ ] **Clean Shutdown**: Process exits cleanly with code 0, no hangs
- [ ] **Error Visibility**: Any errors are logged to auto.log, not swallowed
- [ ] **Completion Works**: Loop exits on completion signal before max_turns
- [ ] **Max Respected**: Loop respects max_turns limit
- [ ] **Minimal Mode Works**: Subprocess-based (Copilot) mode still works
- [ ] **UI Mode Works**: If UI enabled, no crashes or freezes
- [ ] **Logs Clear**: auto.log file clearly shows turn progression
- [ ] **Timestamps**: All log entries have clear timestamps
- [ ] **Reproducible**: Running same test twice produces similar results

---

## Debugging Guide

If tests fail, use this guide:

### If Loop Never Reaches Turn 3:

1. Check auto.log for:
   ```bash
   grep "Loop entry\|Loop iteration 3\|About to execute turn 3" auto.log
   ```

2. If nothing appears, loop isn't executing at all → Fix 2 (empty range)

3. If "Loop entry" appears but "Loop iteration 3" doesn't → Exception between loop entry and first iteration

### If Process Hangs:

1. Check if stdin is being requested:
   ```bash
   strace -e read amplihack --auto ... 2>&1 | grep stdin
   ```

2. Add timeout to next run:
   ```bash
   timeout 30s amplihack --auto ...
   ```

3. Check logs for last turn attempted:
   ```bash
   tail -20 auto.log
   ```

### If Exception Logged:

1. Find exception in logs:
   ```bash
   grep "ERROR\|CRITICAL\|Traceback" auto.log
   ```

2. Match to line number in auto_mode.py

3. Add more detailed logging at that location

---

## Test Report Template

For each test, fill in:

```
Test Name: _______________
Date: _______________
Command: _______________

Expected Result:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

Actual Result:
[paste relevant log section]

Status: PASS / FAIL

Notes:
[any observations]
```
