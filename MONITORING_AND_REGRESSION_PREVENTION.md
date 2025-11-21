# Auto Mode Monitoring and Regression Prevention

**Purpose**: Long-term monitoring and regression prevention for the auto mode execution bug

---

## Issue Summary

**Bug**: Auto mode stops after Turn 2 (Planning) instead of continuing to Turns 3+ (Execution)
- Current: 2/20 turns executed, exit code 0
- Expected: 3-20 turns executed based on workload and completion signal
- Impact: Auto mode features completely non-functional

**Root Cause**: To be determined by diagnostic phase, but top suspects are:
1. Swallowed exception in main loop
2. SDK hang on Turn 3
3. Early break before loop
4. Empty loop range (max_turns < 3)
5. Async coordination failure

---

## Monitoring Strategy

### Level 1: Automated CI Checks (Required for all commits)

#### Check 1.1: Loop Execution Verification

**What**: Verify that Turn 3+ is attempted in auto mode

**CI Job**: `test-auto-mode-basic`

**Command**:
```bash
#!/bin/bash
amplihack --auto --max-turns 5 --prompt "Print hello world" > /dev/null 2>&1

# Extract turn count from logs
LAST_TURN=$(grep -o "Turn [0-9]*" logs/auto_claude_*/auto.log | tail -1 | grep -o "[0-9]*")

if [ "$LAST_TURN" -lt 3 ]; then
    echo "FAIL: Auto mode stopped at Turn $LAST_TURN (expected >= 3)"
    exit 1
fi

echo "PASS: Auto mode reached Turn $LAST_TURN"
exit 0
```

**Failure Response**: Block merge until fixed

**Run Frequency**: On every commit to `launcher/auto_mode.py`

---

#### Check 1.2: Exception Detection

**What**: Verify no exceptions escaped the main loop

**CI Job**: `test-auto-mode-exceptions`

**Command**:
```bash
#!/bin/bash
amplihack --auto --max-turns 3 --prompt "test" > /dev/null 2>&1

# Check for escaped exceptions
if grep -q "CRITICAL EXCEPTION escaped\|Exception escaped loop" logs/auto_claude_*/auto.log; then
    echo "FAIL: Exception escaped main loop"
    exit 1
fi

# Check for unexpected errors
if grep -q "ERROR: Turn [0-9]* failed\|EventError\|RuntimeError" logs/auto_claude_*/auto.log; then
    echo "WARNING: Unexpected error occurred"
    # This is a warning, not hard fail
fi

echo "PASS: No escaped exceptions"
exit 0
```

**Failure Response**: Block merge

**Run Frequency**: On every commit to launcher files

---

#### Check 1.3: Performance Regression

**What**: Verify turn execution times haven't degraded

**CI Job**: `test-auto-mode-performance`

**Command**:
```bash
#!/bin/bash
amplihack --auto --max-turns 5 --prompt "test" > /dev/null 2>&1

# Extract timing for each turn
grep "DIAG: Turn [0-9]* completed" logs/auto_claude_*/auto.log | grep -o "elapsed=[0-9]*\.[0-9]*s" | grep -o "[0-9]*\.[0-9]*" > /tmp/turn_times.txt

# Check if any turn > 120 seconds (2 minutes)
while read time; do
    if (( $(echo "$time > 120" | bc -l) )); then
        echo "FAIL: Turn took ${time}s (expected < 120s)"
        exit 1
    fi
done < /tmp/turn_times.txt

echo "PASS: All turns completed within performance budget"
exit 0
```

**Failure Response**: Warning only (may need investigation)

**Run Frequency**: Weekly or after major changes

---

#### Check 1.4: Mode Coverage

**What**: Verify both sync and async modes work

**CI Job**: `test-auto-mode-all-sdks`

**Commands**:
```bash
#!/bin/bash

# Test Claude SDK (async)
amplihack --auto --sdk claude --max-turns 3 --prompt "test" || exit 1

# Test Copilot (subprocess)
which copilot >/dev/null 2>&1 && amplihack --auto --sdk copilot --max-turns 3 --prompt "test" || echo "Copilot not available (OK)"

echo "PASS: All available SDK modes work"
exit 0
```

**Failure Response**: Block merge if Claude SDK fails

**Run Frequency**: On every commit to launcher files

---

### Level 2: Manual Testing (Before Release)

#### Pre-Release Checklist

```
Release: _______________
Date: _______________

Manual Tests:
- [ ] Run with max_turns=5, verify Turn 3+ appears
- [ ] Run with max_turns=20, verify completes early on signal
- [ ] Run with complex prompt, verify iteration happens
- [ ] Run with edge case (max_turns=3), verify exactly 3 turns
- [ ] Check logs for no ERROR messages
- [ ] Check timing, verify no turns hang
- [ ] Test both Claude and Copilot modes (if available)
- [ ] Run UI mode, verify no crashes

Issues Found:
[list any issues]

Sign-Off:
Tester: _______________
Date: _______________
```

---

### Level 3: User-Facing Monitoring (Post-Deployment)

#### Metric 1: Auto Mode Success Rate

**Source**: Production logs from `.claude/runtime/logs/auto_*/auto.log`

**Calculation**:
```
Success Rate = (Sessions reaching Turn 3+) / (Total sessions) * 100%
```

**Alert Threshold**: If < 95% for more than 1 hour, notify maintainers

**Dashboard**: Monitor in ops/status page

---

#### Metric 2: Auto Mode Session Duration

**Source**: Session completion times from logs

**Calculation**:
```
Avg Duration = sum(session times) / count(sessions)
P95 Duration = 95th percentile of session times
```

**Alert Threshold**: If avg > 5 minutes or P95 > 15 minutes, investigate

**Expected**: 30-90 seconds for typical tasks

---

#### Metric 3: Exception Rate

**Source**: ERROR and CRITICAL log entries

**Calculation**:
```
Exception Rate = (Sessions with errors) / (Total sessions) * 100%
```

**Alert Threshold**: If > 5% in any 1-hour window, page on-call

**Action**: Correlate with recent changes

---

## Regression Prevention Strategies

### Strategy 1: Code Review Checklist

**For any PR touching `launcher/auto_mode.py`**:

```
Code Review Checklist:
- [ ] Does the change affect the main loop (lines 1090-1200)?
- [ ] Are all async calls awaited correctly?
- [ ] Are there any new `return` statements that might exit early?
- [ ] Are exceptions handled properly (not swallowed)?
- [ ] Are new variables initialized before use?
- [ ] Is error checking after SDK calls?
- [ ] Are there any break statements that might exit loop?

If any "yes" → Require additional testing
```

---

### Strategy 2: Test Coverage Requirements

**Minimum test coverage for launcher code**:

```python
# tests/unit/test_auto_mode_execution_coverage.py

def test_turn_3_execution_required():
    """This test MUST pass - core functionality."""
    # Run auto mode, assert Turn >= 3

def test_exception_handling_required():
    """This test MUST pass - error handling."""
    # Inject exception, assert logged and handled

def test_loop_completion_required():
    """This test MUST pass - loop termination."""
    # Run to completion, assert no hang

# These tests cannot be skipped or marked xfail
```

---

### Strategy 3: Documentation

**Document in code**:

```python
# Critical section - changes here can break auto mode
# See DIAGNOSTIC_AND_FIX_STRATEGY.md for detailed analysis
# Line 1090-1200: Main execution loop
# DO NOT change without understanding async event loop coordination
# DO NOT add early returns without checking loop completion path
# DO NOT catch exceptions without re-raising or logging

for turn in range(3, self.max_turns + 1):
    # ... loop body ...
```

---

### Strategy 4: Staged Rollout

**For any fix that changes core loop**:

1. Deploy to canary environment
2. Run 100 test sessions, monitor metrics
3. If success rate >= 99% and no exceptions, proceed
4. Deploy to staging
5. Full test suite
6. Deploy to production with monitoring

---

## Long-Term Monitoring Dashboard

### Dashboard Widgets

#### Widget 1: Turn Execution Distribution

```
Turn Execution Chart:
Turn 1: ████████████████████ 100%
Turn 2: ████████████████████ 100%
Turn 3: ██████████████████░░  95%  <- Should be ~95-100%
Turn 4: █████████████░░░░░░░  65%  <- Varies by workload
Turn 5: ███████░░░░░░░░░░░░░  35%
Turn 6: ████░░░░░░░░░░░░░░░░  20%
...
```

**What it tells you**: If Turn 3 drops below 90%, the bug may have regressed

---

#### Widget 2: Session Duration Trend

```
Duration Over Time:
Week 1: 45s ✓
Week 2: 47s ✓
Week 3: 52s ✓
Week 4: 1m 15s ⚠️ <- Investigate
Week 5: 5m 30s 🚨 <- Critical regression
```

**What it tells you**: Hang or performance degradation issues

---

#### Widget 3: Error Rate Trend

```
Error Rate:
Hour 1:  0% ✓
Hour 2:  0% ✓
Hour 3:  2% ✓
Hour 4:  8% ⚠️ <- Investigate
Hour 5: 22% 🚨 <- Critical issue
```

**What it tells you**: New exception pattern or systematic failure

---

#### Widget 4: Loop Iteration Histogram

```
Turns Completed per Session:
1-2 turns:  [█░░░░]  2% <- Bug indicator
3-5 turns:  [█████████░] 45%
6-10 turns: [███████░░░] 30%
11-15 turns:[████░░░░░░] 15%
16-20 turns:[█░░░░░░░░░] 8%
```

**What it tells you**: Normal distribution should be tail-heavy (most complete early on completion signal)

---

## Incident Response

### If Bug Reoccurs: Triage Checklist

```
Incident: Auto mode stops at Turn 2
Reported: _______________
Severity: CRITICAL

Immediate Actions:
- [ ] Page on-call engineer
- [ ] Check if recent commit to launcher/ files
- [ ] Review git log for last 24 hours
- [ ] Check auto.log from failing session
- [ ] Correlate with metric spike

Diagnosis:
- [ ] Run diagnostic: amplihack --auto --max-turns 5 --prompt "test"
- [ ] Check logs for "Loop entry" message
- [ ] Check logs for exceptions
- [ ] Compare to baseline test_auto_mode_basic.log
- [ ] Identify which suspect matches the symptoms

Root Cause: _______________

Mitigation:
- [ ] Revert suspect commit or
- [ ] Apply hot-fix from FIX_DESIGNS.md section ___
- [ ] Verify with CI checks
- [ ] Deploy to prod with monitoring

Post-Incident:
- [ ] Add CI check if missing
- [ ] Add test case if not covered
- [ ] Document in DISCOVERIES.md
- [ ] Update monitoring thresholds
```

---

## Continuous Improvement

### Monthly Review

**First Monday of each month**:

```
Auto Mode Health Review - _______________

Metrics:
- Success Rate: ___%
- Avg Duration: ___ seconds
- Exception Rate: ___%
- Turn 3+ Rate: ___%

Incidents:
- Number: ___
- Severity: ___
- Root Cause: ___
- Resolution: ___

Improvements Made:
- [ ] New test added
- [ ] Documentation updated
- [ ] Monitoring threshold adjusted
- [ ] Code refactored for clarity

Next Month Goals:
- _______________
- _______________
- _______________
```

---

## Rollback Procedure

**If fix introduces new issues**:

```bash
# 1. Identify problematic commit
git log --oneline launcher/auto_mode.py | head -5

# 2. Revert (if safe)
git revert <commit-hash>

# 3. Verify with CI
# Wait for CI checks to pass

# 4. Deploy
git push

# 5. Monitor
# Watch metrics dashboard for recovery

# 6. Post-mortem
# Why did fix not work?
# Update FIX_DESIGNS.md with learnings
```

---

## Known Issues and Workarounds

| Issue | Symptom | Workaround | Status |
|-------|---------|-----------|--------|
| Auto mode stops at Turn 2 | Only Turns 1-2 in logs | Use manual mode | UNFIXED |
| SDK hang on long prompts | Process hangs at Turn 3 | Reduce prompt size | TEMP FIX |
| Exception swallowed | Clean exit but incomplete | Check auto.log | UNKNOWN |

---

## Key Contacts

**Code Owner**: [amplihack maintainers]
**On-Call**: [ops team]
**Release Manager**: [release team]

---

## Related Documentation

- `DIAGNOSTIC_AND_FIX_STRATEGY.md` - Detailed diagnosis approach
- `INSTRUMENTATION_REFERENCE.md` - Logging points to add
- `FIX_DESIGNS.md` - Implementation specifications
- `TEST_PLAN.md` - Test cases and procedures
- `.claude/context/DISCOVERIES.md` - Known issues and learnings
