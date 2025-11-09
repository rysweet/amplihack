# Stop Hook Documentation

## Overview

The stop hook intercepts Claude Code's stop events and can block them to enable continuous work mode (lock mode) or trigger reflection analysis.

## Critical Design Principles

### 1. Lock and Reflection Are Independent

**Lock mode** and **reflection** are two separate, independently controllable features:

- **Lock Mode**: Prevents Claude from stopping by checking for `.lock_active` file
- **Reflection**: Runs AI-powered session analysis when stopping

These features are intentionally independent:
- Lock can work with or without reflection
- Reflection can be enabled or disabled without affecting lock
- Disabling reflection does NOT disable lock

### 2. Execution Order: Lock Before Reflection

The stop hook checks conditions in this order:

1. **Lock Check** (lines 63-82)
   - Checks if `.claude/runtime/locks/.lock_active` exists
   - If lock exists → **BLOCK immediately** with continuation prompt
   - Lock check runs BEFORE reflection check

2. **Reflection Check** (lines 84-88)
   - Only reached if lock is NOT active
   - Checks if reflection should run via `_should_run_reflection()`
   - If reflection disabled → **APPROVE stop**
   - If reflection enabled → Run reflection analysis

3. **Reflection Execution** (lines 90-170)
   - Only reached if no lock AND reflection enabled
   - Runs Claude SDK-powered analysis
   - Blocks to present findings

## How to Disable Reflection

Reflection can be disabled in three ways:

### Method 1: Environment Variable
```bash
export AMPLIHACK_SKIP_REFLECTION=1
amplihack
```

### Method 2: CLI Flag
```bash
amplihack --no-reflection
```

### Method 3: Config File
Edit `.claude/tools/amplihack/.reflection_config`:
```json
{
  "enabled": false
}
```

## How Lock Mode Works

Lock mode is controlled by a file flag:
- **Enable**: Create `.claude/runtime/locks/.lock_active`
- **Disable**: Delete `.claude/runtime/locks/.lock_active`

Lock mode is independent of reflection:
```bash
# Lock works with reflection enabled
create .lock_active → blocks stop

# Lock works with reflection disabled
export AMPLIHACK_SKIP_REFLECTION=1
create .lock_active → still blocks stop!
```

## Common Scenarios

### Scenario 1: Lock Active, Reflection Enabled
```
User tries to stop
→ Lock check: ACTIVE → BLOCK with continuation prompt
→ Reflection never runs (lock blocks first)
```

### Scenario 2: Lock Active, Reflection Disabled
```
User tries to stop
→ Lock check: ACTIVE → BLOCK with continuation prompt
→ Reflection never runs (disabled)
→ RESULT: Lock still works!
```

### Scenario 3: No Lock, Reflection Enabled
```
User tries to stop
→ Lock check: INACTIVE → Continue
→ Reflection check: ENABLED → Run reflection
→ Block to present findings
```

### Scenario 4: No Lock, Reflection Disabled
```
User tries to stop
→ Lock check: INACTIVE → Continue
→ Reflection check: DISABLED → APPROVE stop
→ RESULT: Normal stop
```

## Testing Lock and Reflection Independence

Run the test suite to verify independence:
```bash
python tests/unit/hooks/test_lock_reflection_simple.py
```

Expected output:
```
[TEST 1] Lock blocks when reflection enabled... ✓
[TEST 2] Lock blocks when reflection disabled... ✓
[TEST 3] Stop allowed when no lock and reflection disabled... ✓
[TEST 4] Lock blocks when reflection disabled via config... ✓
[TEST 5] Custom prompt with reflection disabled... ✓
```

## Troubleshooting

### "Lock mode isn't working!"

Check these conditions:

1. **Is lock file actually created?**
   ```bash
   test -f .claude/runtime/locks/.lock_active && echo "EXISTS" || echo "MISSING"
   ```

2. **Is stop hook registered?**
   ```bash
   grep -A 5 '"Stop"' .claude/settings.json
   ```

3. **Are there hook execution errors?**
   ```bash
   cat .claude/runtime/logs/stop.log
   ```

4. **Is reflection interfering?** (It shouldn't, but verify)
   ```bash
   export AMPLIHACK_SKIP_REFLECTION=1  # Disable reflection
   # Try lock mode again
   ```

### "Reflection won't disable!"

Check these conditions:

1. **Is environment variable set?**
   ```bash
   echo $AMPLIHACK_SKIP_REFLECTION  # Should print "1"
   ```

2. **Is config file correct?**
   ```bash
   cat .claude/tools/amplihack/.reflection_config
   # Should show {"enabled": false}
   ```

3. **Is reflection lock file stuck?**
   ```bash
   rm -f .claude/runtime/reflection/.reflection_lock
   ```

## Code Structure

```python
def process(self, input_data):
    # STEP 1: Check lock (ALWAYS FIRST)
    if lock_exists:
        return {"decision": "block", "reason": continuation_prompt}

    # STEP 2: Check if reflection should run
    if not self._should_run_reflection():
        return {"decision": "approve"}  # No lock, no reflection → allow stop

    # STEP 3: Run reflection (only if no lock AND reflection enabled)
    reflection_result = self._run_reflection_sync()
    return {"decision": "block", "reason": present_findings}
```

## Fail-Safe Behavior

The stop hook is designed to fail safely:

- **Lock file access error** → Allow stop (fail-safe: don't block)
- **Reflection error** → Allow stop (fail-safe: don't block)
- **Timeout** → Allow stop (30-second timeout configured)

This ensures Claude Code never gets permanently stuck.

## Related Files

- `stop.py` - Main stop hook implementation
- `.claude/settings.json` - Hook registration
- `.claude/runtime/locks/` - Lock mode files
- `.claude/runtime/reflection/` - Reflection output files
- `tests/unit/hooks/test_lock_reflection_simple.py` - Independence tests
