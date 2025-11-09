# Investigation: Lock Mode and Reflection Independence

## Summary

**Finding**: Lock mode and reflection ARE properly independent. The reported bug does not exist in the code.

**Status**: All tests pass. Lock works correctly regardless of reflection settings.

## Investigation Details

### Reported Issue
"When reflection is disabled, it's breaking lock mode. Lock and reflection stop hooks must be independently enabled/disabled."

### Investigation Steps

1. **Code Review** (`.claude/tools/amplihack/hooks/stop.py`)
   - Lock is checked FIRST (lines 69-94)
   - Reflection is checked SECOND (lines 96-103)
   - Lock returns immediately when active, regardless of reflection settings
   - Code structure is correct

2. **Test Suite Created** (`tests/unit/hooks/test_lock_reflection_simple.py`)
   - Test 1: Lock blocks when reflection enabled ✓
   - Test 2: Lock blocks when reflection disabled (via env var) ✓
   - Test 3: Stop allowed when no lock and reflection disabled ✓
   - Test 4: Lock blocks when reflection disabled (via config) ✓
   - Test 5: Custom prompt works with reflection disabled ✓

3. **Results**: All 5 tests PASSED

### Root Cause Analysis

The code is **CORRECT**. Lock and reflection are properly independent:

```python
def process(self, input_data):
    # STEP 1: Check lock FIRST
    if lock_exists:
        return {"decision": "block"}  # Blocks regardless of reflection

    # STEP 2: Check reflection SECOND (only if no lock)
    if not self._should_run_reflection():
        return {"decision": "approve"}

    # STEP 3: Run reflection (only if no lock AND reflection enabled)
    return run_reflection()
```

**Key insight**: Lock is checked at line 72 and returns at line 91. Reflection check doesn't happen until line 99, AFTER the lock check completes.

### Why Might User Think It's Broken?

Possible explanations:

1. **Lock file not actually created**
   - User may not have created `.claude/runtime/locks/.lock_active`
   - Solution: Verify with `test -f .claude/runtime/locks/.lock_active`

2. **Hook not registered properly**
   - Stop hook may not be configured in `.claude/settings.json`
   - Solution: Verify hook registration

3. **Confusion about behavior**
   - User may have expected different behavior
   - Solution: Clear documentation (now added)

4. **Different issue entirely**
   - The problem may be elsewhere in the system
   - Solution: Ask user for specific repro steps

## Changes Made

### 1. Enhanced Logging (`stop.py`)

Added explicit logging to make execution flow clear:
```python
self.log("NOTE: Lock blocks even if reflection is disabled")
self.log("NOTE: This does NOT affect lock mode (lock checked first)")
```

### 2. Defensive Comments (`stop.py`)

Added comments explaining independence:
```python
# STEP 1: CHECK LOCK (ALWAYS FIRST, HIGHEST PRIORITY)
# This runs regardless of reflection settings

# NOTE: This blocks REGARDLESS of reflection settings
# Lock and reflection are independent features
```

### 3. Documentation (`README_STOP_HOOK.md`)

Created comprehensive documentation covering:
- Design principles (lock and reflection independence)
- Execution order (lock before reflection)
- How to disable reflection (3 methods)
- How lock mode works
- Common scenarios with examples
- Troubleshooting guide

### 4. Test Suite (`test_lock_reflection_simple.py`)

Created comprehensive test suite that can be run anytime to verify independence:
```bash
python tests/unit/hooks/test_lock_reflection_simple.py
```

## Verification

```bash
$ python tests/unit/hooks/test_lock_reflection_simple.py
======================================================================
TESTING: Lock and Reflection Independence
======================================================================

[TEST 1] Lock blocks when reflection enabled... ✓
[TEST 2] Lock blocks when reflection disabled... ✓
[TEST 3] Stop allowed when no lock and reflection disabled... ✓
[TEST 4] Lock blocks when reflection disabled via config... ✓
[TEST 5] Custom prompt with reflection disabled... ✓

======================================================================
RESULTS: 5 passed, 0 failed
======================================================================

✅ ALL TESTS PASSED: Lock and reflection are properly independent
```

## Conclusion

**The code is correct**. Lock and reflection are properly independent. No bug fix needed.

Changes made:
1. Enhanced logging for clarity
2. Added defensive comments
3. Created comprehensive documentation
4. Added test suite for ongoing verification

**Recommendation**: If user still reports issues, ask for:
- Exact steps to reproduce
- Output of `test -f .claude/runtime/locks/.lock_active`
- Contents of `.claude/runtime/logs/stop.log`
- Whether stop hook is actually being called

## Testing Proof

The test suite provides concrete proof that lock works independently:

```python
def test_lock_blocks_when_reflection_disabled():
    """THE CRITICAL TEST"""
    # Lock active
    hook.lock_flag.touch()

    # Reflection disabled
    os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    # Execute
    result = hook.process({})

    # Verify: Lock MUST still block
    assert result["decision"] == "block"  # ✓ PASSES
```

This test explicitly verifies that when:
- Lock is active (file exists)
- Reflection is disabled (env var set)

Then:
- Lock still blocks stop (returns "block" decision)

**This is exactly what the user said was broken, but the test proves it works correctly.**
