# Integration: Modifying stop.py

## Purpose

Add power-steering check to existing stop.py hook orchestrator.

## Current stop.py Structure

Based on investigation, stop.py handles:

1. Lock mechanism check
2. Reflection check (if enabled)
3. Neo4j cleanup (if enabled)

## Proposed Modification

Add power-steering as 3rd check, after reflection.

## Exact Changes Required

### Location

`~/.amplihack/.claude/tools/amplihack/hooks/stop.py`

### Change 1: Import PowerSteeringChecker

Add after existing imports:

```python
from .power_steering_checker import PowerSteeringChecker, PowerSteeringResult
```

### Change 2: Add power-steering check in process() method

Find the section after reflection check (around line 150-200), add:

```python
# Power-Steering Check
if self._should_run_power_steering(input_data):
    try:
        ps_checker = PowerSteeringChecker(self.project_root)
        ps_result = ps_checker.check(transcript_path, session_id)

        if ps_result.decision == "block":
            self.log_metric("power_steering_blocked", 1)
            return {
                "decision": "block",
                "reason": "power_steering",
                "continuation_prompt": ps_result.continuation_prompt
            }
        elif ps_result.decision == "approve":
            self.log_metric("power_steering_approved", 1)

            # Display summary if available
            if ps_result.summary:
                print("\n" + "="*80)
                print("SESSION SUMMARY")
                print("="*80)
                print(ps_result.summary)
                print("="*80 + "\n")

    except Exception as e:
        # Log error but don't block on power-steering failures (fail-open)
        self.log_error(f"Power-steering check failed: {e}", exc_info=True)
        self.log_metric("power_steering_error", 1)
        # Continue to approve
```

### Change 3: Add \_should_run_power_steering() helper

Add as new method in StopHookProcessor class:

```python
def _should_run_power_steering(self, input_data: Dict) -> bool:
    """Determine if power-steering should run."""

    # Check 1: Environment variable
    if os.getenv("AMPLIHACK_SKIP_POWER_STEERING"):
        self.logger.info("Power-steering skipped via AMPLIHACK_SKIP_POWER_STEERING")
        return False

    # Check 2: Config file
    config_path = self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                if not config.get("enabled", True):
                    self.logger.info("Power-steering disabled in config")
                    return False
        except Exception as e:
            self.logger.warning(f"Failed to load power-steering config: {e}")
            # Continue - treat as enabled if config can't be loaded

    # Check 3: Semaphore file
    disabled_semaphore = (
        self.project_root / ".claude" / "runtime"
        / "power-steering" / ".disabled"
    )
    if disabled_semaphore.exists():
        self.logger.info("Power-steering disabled via semaphore")
        return False

    return True
```

## Execution Order

With this change, stop.py will execute in this order:

1. **Lock Check** - Prevent concurrent stops
2. **Reflection Check** - Present learning questions (if enabled)
3. **Power-Steering Check** - Verify work completeness (if enabled) ← NEW
4. **Neo4j Cleanup** - Cleanup graph state (if enabled)
5. **Approve Stop** - All checks passed

## Error Handling Philosophy

**Power-steering uses fail-open approach:**

- If power-steering crashes, log error and approve stop
- Don't block user due to power-steering bugs
- Log metric for monitoring

**Rationale:**

- Power-steering is enhancement, not critical path
- Should never prevent user from stopping session
- Better to have false negatives (allow bad stops) than false positives (block good stops)

## Metrics to Log

- `power_steering_blocked`: Stop was blocked
- `power_steering_approved`: Stop was approved
- `power_steering_error`: Power-steering crashed
- `power_steering_skipped_disabled`: Disabled via config/env/semaphore
- `power_steering_skipped_qa`: Skipped due to Q&A session detection

## Testing Integration

After implementing changes:

1. Test stop.py still works without power-steering
2. Test power-steering blocks when expected
3. Test power-steering approves when expected
4. Test disable mechanisms work
5. Test error handling (simulate power-steering crash)
6. Test summary display

## Rollback Plan

If power-steering causes issues:

1. Set `AMPLIHACK_SKIP_POWER_STEERING=1` (immediate)
2. Or edit config: `{"enabled": false}` (persistent)
3. Or remove import and method call from stop.py (permanent)

## Migration Path

1. Deploy power-steering code
2. Deploy with `enabled: false` by default
3. Monitor for issues
4. Enable for beta testers
5. Enable globally after validation

## Compatibility

This change is backward compatible:

- stop.py works if power_steering_checker.py missing (import error caught)
- Power-steering gracefully skips if disabled
- No changes to lock or reflection behavior
- No changes to Claude Code API
