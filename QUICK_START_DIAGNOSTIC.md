# Quick Start: Run Diagnostic

**Phase 1 Status**: ✓ COMPLETE - All instrumentation added
**Next Step**: Run diagnostic test to confirm root cause

---

## Prerequisites

The instrumented code is in this worktree:
```bash
/home/azureuser/src/amplihack/worktrees/feat/issue-1425-auto-mode-execution-fix
```

---

## Option 1: Copy to Main Repo and Test (RECOMMENDED)

### Step 1: Backup original file
```bash
cd /home/azureuser/src/amplihack
cp src/amplihack/launcher/auto_mode.py src/amplihack/launcher/auto_mode.py.backup
```

### Step 2: Copy instrumented file
```bash
cp worktrees/feat/issue-1425-auto-mode-execution-fix/src/amplihack/launcher/auto_mode.py \
   src/amplihack/launcher/auto_mode.py
```

### Step 3: Run diagnostic test
```bash
cd /home/azureuser/src/amplihack

# Test 1: Simple prompt (should complete quickly)
amplihack --auto --prompt "print hello world" --max-turns 5 2>&1 | tee diagnostic_test.log

# If that works, test with more turns
amplihack --auto --prompt "list files in the current directory" --max-turns 10 2>&1 | tee diagnostic_test2.log
```

### Step 4: Analyze logs
```bash
# Find the most recent auto mode log
LOG_FILE=$(ls -t logs/auto_claude_*.log | head -1)

# Extract all diagnostic markers
echo "=== DIAGNOSTIC OUTPUT ==="
grep "DIAG:" $LOG_FILE

# Check if Turn 3+ was reached
echo -e "\n=== TURN 3+ CHECK ==="
grep "Loop iteration [3-9]" $LOG_FILE || echo "❌ Turn 3+ never started!"

# Check for exceptions
echo -e "\n=== EXCEPTION CHECK ==="
grep "CRITICAL EXCEPTION\|ERROR" $LOG_FILE || echo "✓ No exceptions found"

# Show timeline
echo -e "\n=== TIMELINE (first 20 diagnostic lines) ==="
grep "DIAG:" $LOG_FILE | head -20
```

### Step 5: Restore original file (after testing)
```bash
cd /home/azureuser/src/amplihack
mv src/amplihack/launcher/auto_mode.py.backup src/amplihack/launcher/auto_mode.py
```

---

## Option 2: Create Standalone Test Script

If you don't want to modify the main repo, create a test harness:

```bash
cd /home/azureuser/src/amplihack/worktrees/feat/issue-1425-auto-mode-execution-fix

# Create test script
cat > test_diagnostic.py << 'EOF'
#!/usr/bin/env python3
"""Test harness for instrumented auto_mode.py"""

import sys
import os

# Add worktree src to path
sys.path.insert(0, '/home/azureuser/src/amplihack/worktrees/feat/issue-1425-auto-mode-execution-fix/src')

# Import and run auto mode
from amplihack.launcher.auto_mode import AutoModeLauncher

# Create minimal test
launcher = AutoModeLauncher(
    sdk="claude",
    prompt="print hello world",
    max_turns=5,
    working_dir=os.getcwd()
)

# Run and capture result
exit_code = launcher.run()
print(f"Exit code: {exit_code}")
sys.exit(exit_code)
EOF

chmod +x test_diagnostic.py
python test_diagnostic.py 2>&1 | tee test_output.log
```

---

## Expected Output Scenarios

### Scenario A: Working (Bug Fixed)
```
DIAG: Loop entry - range(3, 6) => turns 3 to 5
DIAG: Loop will execute 3 iterations
DIAG: Event loop is active and healthy before loop
DIAG: Loop iteration 3 started (max_turns=5)
DIAG: Event loop still active at turn 3
DIAG: About to execute turn 3
DIAG: execute_prompt length: 3821 chars
DIAG: Execute call returned - code=0, output_len=2145, elapsed=12.3s
DIAG: About to evaluate turn 3
DIAG: Evaluate call returned - code=0, result_len=432, elapsed=8.5s
DIAG: Checking for completion signals in eval
DIAG: Signals found - complete=True, achieved=False, criteria=False
✓ Objective achieved!
DIAG: Loop exited normally after 3 turns
```
**Interpretation**: Bug is fixed! Loop executes Turns 3+ and completes properly.

---

### Scenario B: Broken - Loop Never Starts (Suspect #2)
```
DIAG: Loop entry - range(3, 6) => turns 3 to 5
DIAG: Loop will execute 3 iterations
DIAG: Event loop is active and healthy before loop
[NOTHING AFTER THIS]
```
**Interpretation**: Loop never starts executing. Root cause is early break/return before Turn 3.
**Fix**: Implement Fix #2 from DIAGNOSTIC_AND_FIX_STRATEGY.md

---

### Scenario C: Broken - Loop Starts But Hangs (Suspect #3)
```
DIAG: Loop entry - range(3, 6) => turns 3 to 5
DIAG: Loop will execute 3 iterations
DIAG: Event loop is active and healthy before loop
DIAG: Loop iteration 3 started (max_turns=5)
DIAG: Event loop still active at turn 3
DIAG: About to execute turn 3
[HANGS HERE - never returns]
```
**Interpretation**: SDK call hangs indefinitely.
**Fix**: Implement Fix #3 (SDK timeout wrapper) from DIAGNOSTIC_AND_FIX_STRATEGY.md

---

### Scenario D: Broken - Exception Swallowed (Suspect #1)
```
DIAG: Loop entry - range(3, 6) => turns 3 to 5
DIAG: Loop will execute 3 iterations
DIAG: Event loop is active and healthy before loop
DIAG: Loop iteration 3 started (max_turns=5)
DIAG: Event loop still active at turn 3
DIAG: About to execute turn 3
DIAG: CRITICAL EXCEPTION escaped from turns: CancelledError
DIAG: Exception message: Task was cancelled
DIAG: Traceback:
  File "auto_mode.py", line 1177, in _run_async_session
    code, execution_output = await self._run_turn_with_retry(...)
  [... full traceback ...]
```
**Interpretation**: Exception is thrown and caught by our instrumentation.
**Fix**: Implement Fix #1 (exception handling) from DIAGNOSTIC_AND_FIX_STRATEGY.md

---

### Scenario E: Broken - Empty Loop Range (Suspect #4)
```
DIAG: Loop entry - range(3, 3) => turns 3 to 2
DIAG: WARNING - loop range is empty (3 > 2)
DIAG: Loop will execute 0 iterations
DIAG: Loop exited normally after 2 turns
```
**Interpretation**: max_turns is less than 3, loop never executes.
**Fix**: Implement Fix #4 (loop range validation) from DIAGNOSTIC_AND_FIX_STRATEGY.md

---

### Scenario F: Broken - Event Loop Lost (Suspect #5)
```
DIAG: Loop entry - range(3, 6) => turns 3 to 5
DIAG: Loop will execute 3 iterations
DIAG: Event loop is active and healthy before loop
DIAG: Loop iteration 3 started (max_turns=5)
DIAG: CRITICAL - event loop lost at turn 3: no running event loop
```
**Interpretation**: Async event loop became unavailable.
**Fix**: Implement Fix #5 (async coordination reset) from DIAGNOSTIC_AND_FIX_STRATEGY.md

---

## Troubleshooting

### Problem: Can't find log file
```bash
# Check if logs directory exists
ls -la logs/

# Find all auto mode logs
find . -name "auto_claude_*.log" -mtime -1

# If no logs, check if logging is enabled
grep "LOG_FILE" diagnostic_test.log
```

### Problem: No DIAG output in logs
```bash
# Check if DEBUG level is enabled
grep "level=\"DEBUG\"" src/amplihack/launcher/auto_mode.py

# Verify instrumentation is in file
grep -c "DIAG:" src/amplihack/launcher/auto_mode.py
# Should show: 23
```

### Problem: Import errors when running test
```bash
# Ensure PYTHONPATH includes src directory
export PYTHONPATH=/home/azureuser/src/amplihack/worktrees/feat/issue-1425-auto-mode-execution-fix/src:$PYTHONPATH

# Check Python version (requires 3.11+)
python --version
```

---

## Next Actions After Diagnosis

Once you've identified the root cause:

1. **Document findings**: Add results to DIAGNOSTIC_RESULTS.md
2. **Choose fix**: Select appropriate fix from DIAGNOSTIC_AND_FIX_STRATEGY.md
3. **Implement fix**: Modify auto_mode.py with chosen fix
4. **Run validation**: Re-test to verify fix works
5. **Clean up instrumentation**: Remove DIAG logging (optional, can keep for debugging)
6. **Create PR**: Submit fix to main repository

---

## Quick Command Cheat Sheet

```bash
# 1. Copy instrumented file to main repo
cp worktrees/feat/issue-1425-auto-mode-execution-fix/src/amplihack/launcher/auto_mode.py src/amplihack/launcher/auto_mode.py

# 2. Run test
amplihack --auto --prompt "print hello" --max-turns 5 2>&1 | tee test.log

# 3. Analyze
LOG=$(ls -t logs/auto_claude_*.log | head -1) && grep "DIAG:" $LOG

# 4. Check Turn 3+
LOG=$(ls -t logs/auto_claude_*.log | head -1) && grep "Loop iteration [3-9]" $LOG

# 5. Look for exceptions
LOG=$(ls -t logs/auto_claude_*.log | head -1) && grep "CRITICAL EXCEPTION" $LOG

# 6. Restore original (after testing)
mv src/amplihack/launcher/auto_mode.py.backup src/amplihack/launcher/auto_mode.py
```

---

## Time Estimates

- Copy file and run test: **2 minutes**
- Analyze logs: **5 minutes**
- Identify root cause: **5 minutes**
- **Total Phase 2**: ~15 minutes

---

**Ready to proceed**: YES - All instrumentation is complete and tested for syntax errors.
