# Auto Mode Execution Bug - Complete Diagnostic and Fix Strategy

**Issue**: #1425 - Auto mode stops after Turn 2 instead of continuing to Turns 3+ (Execution/Evaluation)

**Status**: Diagnostic strategy designed, ready for implementation

**Target**: Fix auto mode execution to properly execute all turns (default 10-20 turns)

---

## Quick Start

### For Project Managers
**Read**: `EXECUTIVE_SUMMARY.md` (5-10 minute read)
- Problem statement and impact
- 4-phase solution approach
- 8-13 hour estimated effort
- Risk assessment

### For Developers (Implementation)
**Read in order**:
1. `DIAGNOSTIC_AND_FIX_STRATEGY.md` - Understand the problem and root cause suspects
2. `INSTRUMENTATION_REFERENCE.md` - Add logging to identify root cause
3. Run diagnostics (Test 1 in TEST_PLAN.md)
4. Select fix from `FIX_DESIGNS.md`
5. Implement fix and run validation tests from `TEST_PLAN.md`

### For QA/Testers
**Read**: `TEST_PLAN.md` (comprehensive test cases)
- Pre-fix baseline tests
- Post-fix validation tests
- Simple and complex scenarios
- CI regression tests

### For DevOps/SRE
**Read**: `MONITORING_AND_REGRESSION_PREVENTION.md`
- 4 levels of automated CI checks
- Production monitoring dashboard
- Incident response procedures
- Regression prevention strategies

---

## Document Map

### Core Strategy Documents

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| **EXECUTIVE_SUMMARY.md** | High-level overview, timeline, risks | PMs, Leads | 2000 words |
| **DIAGNOSTIC_AND_FIX_STRATEGY.md** | Detailed root cause analysis and fix designs | Developers, Architects | 3600 words |
| **INSTRUMENTATION_REFERENCE.md** | Exact logging locations and expected output | Developers | 2200 words |

### Implementation Documents

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| **FIX_DESIGNS.md** | 5 detailed fix implementations with code | Developers | 2800 words |
| **TEST_PLAN.md** | 20+ test cases for validation | QA, Developers | 2600 words |

### Operations Documents

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| **MONITORING_AND_REGRESSION_PREVENTION.md** | Long-term monitoring and regression prevention | DevOps, SRE | 2400 words |

---

## The Problem

Auto mode with Claude SDK stops after Turn 2 with exit code 0 (success), but only executes 2 of 10-20 requested turns.

```
Current (Broken):
Turn 1 (Clarifying): ✓
Turn 2 (Planning):   ✓
Turn 3+ (Executing): ✗ (stops here)
Exit: 0
Duration: 30 seconds

Expected:
Turn 1 (Clarifying): ✓
Turn 2 (Planning):   ✓
Turn 3-10 (Execute/Eval): ✓ (iterations)
Turn 11 (Summary):   ✓
Exit: 0
Duration: 2-10 minutes
```

---

## The Solution (4 Phases)

### Phase 1: Instrumentation (2-4 hours)
Add detailed logging at 7 key regions in `auto_mode.py` to identify where execution stops.

**Reference**: `INSTRUMENTATION_REFERENCE.md` (Regions 1-7)

**Output**: Diagnostic logs showing exact failure point

### Phase 2: Diagnosis (1-2 hours)
Run instrumented code with test cases to confirm root cause (one of 5 suspects).

**Suspects ranked by confidence**:
1. Swallowed Exception (85%)
2. Early Break Before Loop (60%)
3. SDK Hang (50%)
4. Async Coordination (45%)
5. Empty Loop Range (15%)

**Reference**: `DIAGNOSTIC_AND_FIX_STRATEGY.md` (PHASE 1)

**Output**: Confirmed root cause

### Phase 3: Fix Implementation (2-4 hours)
Implement fix for confirmed root cause (typically 10-30 lines of code).

**5 pre-designed fixes available**:
- Fix 1: Exception capture and logging
- Fix 2: Loop range guard
- Fix 3: Timeout protection
- Fix 4: Event loop health check
- Fix 5: Diagnostic reporting

**Reference**: `FIX_DESIGNS.md` (Fixes 1-5)

**Output**: Modified auto_mode.py with fix applied

### Phase 4: Validation (2-3 hours)
Run comprehensive tests to verify fix works and no regressions introduced.

**Test coverage**:
- 7 baseline tests (confirm bug exists)
- 7 validation tests (verify fix works)
- 3 simple scenarios
- 2 complex scenarios
- CI regression tests

**Reference**: `TEST_PLAN.md` (All sections)

**Output**: Verified fix ready for merge

---

## Success Criteria

✓ **Turn 3+ Executes**: Auto mode with `--max-turns 10` shows Turns 1-10 in logs

✓ **Clean Shutdown**: Process exits with code 0, no hangs

✓ **Early Completion**: Loop exits on completion signal before max_turns

✓ **Error Visibility**: Any errors logged to auto.log, not swallowed

✓ **No Regressions**: Existing tests still pass, both async and sync modes work

✓ **CI Passes**: All CI checks pass

✓ **Manual Verification**: Human testing confirms expected behavior

---

## Time Estimate

| Phase | Time | Notes |
|-------|------|-------|
| Phase 1: Instrumentation | 2-4 hrs | Add logging, run tests |
| Phase 2: Diagnosis | 1-2 hrs | Analyze logs, identify root cause |
| Phase 3: Fix Implementation | 2-4 hrs | Code fix, verify syntax |
| Phase 4: Validation | 2-3 hrs | Run all tests, verify fix |
| **Total** | **8-13 hrs** | 1-2 days effort |

---

## Key Findings

### Root Cause (High Confidence)

**Most Likely**: Swallowed exception in main execution loop (lines 1090-1200)

**Evidence**:
- Exit code 0 (indicates clean exit, not crash)
- Only 2 turns executed (suggests loop never reached)
- No error messages in logs
- `_run_turn_with_retry()` catches exceptions but may not propagate them

### Why Suspects Are Ranked

1. **Swallowed Exception (85%)** - Clean exit + no errors = caught exception
2. **Early Break (60%)** - Loop structure allows early exit
3. **SDK Hang (50%)** - Turn 2 works, but Turn 3 might have different SDK behavior
4. **Async Coordination (45%)** - Single event loop could degrade
5. **Empty Range (15%)** - Very unlikely (max_turns defaults to 10)

---

## Critical Files

### Source Code
- **Main bug location**: `/src/amplihack/launcher/auto_mode.py` (lines 994-1220, method `_run_async_session`)
- **Loop body**: Lines 1090-1200 (for loop with execute + evaluate)

---

## Document Checklist

- [x] EXECUTIVE_SUMMARY.md - High-level overview
- [x] DIAGNOSTIC_AND_FIX_STRATEGY.md - Root cause analysis
- [x] INSTRUMENTATION_REFERENCE.md - Logging specification
- [x] FIX_DESIGNS.md - 5 fix implementations
- [x] TEST_PLAN.md - Test cases and procedures
- [x] MONITORING_AND_REGRESSION_PREVENTION.md - Long-term monitoring
- [x] README.md - This file (index and guide)

---

**All diagnostic and fix strategy documentation is complete and ready for implementation.**

**Next step**: Begin Phase 1 (Instrumentation) per instructions in `DIAGNOSTIC_AND_FIX_STRATEGY.md`
