# Auto Mode Transparency Design

## Problem Statement

Auto mode currently operates as a "black box" - users see turn transitions but lack insight into:

- Which turn they're on (out of max turns)
- What phase of the turn is executing
- How long the session has been running

This creates uncertainty and makes it difficult to gauge progress or estimate completion time.

## Design Goals

1. **Minimal Friction**: Add transparency without cluttering output
2. **Actionable Information**: Show data that helps users make decisions
3. **Backward Compatible**: No breaking changes to existing functionality
4. **Clean Implementation**: ~60 LOC addition, maintainable code

## Approach 1: Minimal Progress Indicators (SELECTED)

### Overview

Add lightweight progress indicators to existing turn logging statements.

### Features

1. **Turn Counter**: `[Turn 2/10]` - Shows current turn and max turns
2. **Phase Indicators**: `[Clarifying]`, `[Planning]`, `[Executing]`, `[Evaluating]`, `[Summarizing]`
3. **Elapsed Time**: `[1m 23s]` or `[45s]` - Time since session start

### Output Format

```
[Turn 1/10 | Clarifying | 3s]
[Turn 2/10 | Planning | 45s]
[Turn 3/10 | Executing | 1m 23s]
[Turn 3/10 | Evaluating | 1m 45s]
[Turn 10/10 | Summarizing | 5m 12s]
```

### Integration Points

Current file: `src/amplihack/launcher/auto_mode.py`

#### 1. Track Start Time (Line ~283)

```python
def run(self) -> int:
    """Execute agentic loop."""
    self.start_time = time.time()  # ADD THIS LINE
    self.log(f"Starting auto mode (max {self.max_turns} turns)")
```

#### 2. Add Helper Methods

```python
def _format_elapsed(self, seconds: float) -> str:
    """Format elapsed time as Xm Ys or Xs."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"

def _progress_str(self, phase: str) -> str:
    """Build progress indicator string."""
    elapsed = time.time() - self.start_time
    return f"[Turn {self.turn}/{self.max_turns} | {phase} | {self._format_elapsed(elapsed)}]"
```

#### 3. Update Logging Calls

**Turn 1 - Clarify Objective (Line ~291)**

```python
# BEFORE
self.log(f"\n--- TURN {self.turn}: Clarify Objective ---")

# AFTER
self.log(f"\n--- {self._progress_str('Clarifying')} Clarify Objective ---")
```

**Turn 2 - Create Plan (Line ~311)**

```python
# BEFORE
self.log(f"\n--- TURN {self.turn}: Create Plan ---")

# AFTER
self.log(f"\n--- {self._progress_str('Planning')} Create Plan ---")
```

**Turn 3+ - Execute (Line ~344)**

```python
# BEFORE
self.log(f"\n--- TURN {self.turn}: Execute & Evaluate ---")

# AFTER (split into two logging calls)
self.log(f"\n--- {self._progress_str('Executing')} Execute ---")
# ... execute code ...
```

**Turn 3+ - Evaluate (Line ~371)**

```python
# AFTER execution, before evaluation prompt
self.log(f"--- {self._progress_str('Evaluating')} Evaluate ---")
```

**Summary Phase (Line ~409)**

```python
# BEFORE
self.log("\n--- Summary ---")

# AFTER
self.log(f"\n--- {self._progress_str('Summarizing')} Summary ---")
```

### Implementation Checklist

- [ ] Add `start_time` instance variable tracking
- [ ] Implement `_format_elapsed()` helper method
- [ ] Implement `_progress_str()` helper method
- [ ] Update Turn 1 logging (Clarifying)
- [ ] Update Turn 2 logging (Planning)
- [ ] Split Turn 3+ logging into Executing and Evaluating
- [ ] Update Summary logging (Summarizing)
- [ ] Test output format matches specification
- [ ] Verify backward compatibility (no breaking changes)

### Success Criteria

1. All turn transitions show progress indicator
2. Elapsed time updates correctly throughout session
3. Phase names are clear and descriptive
4. No breaking changes to existing functionality
5. Implementation is clean and minimal (~60 LOC addition)

### Estimated Effort

- **Lines of Code**: ~60 LOC
- **Time**: 2-3 hours
- **Complexity**: Low
- **Risk**: Minimal (purely additive changes)

## Alternative Approaches (Not Selected)

### Approach 2: Rich Progress Dashboard

More comprehensive but higher complexity - deferred for future iteration.

### Approach 3: Structured JSON Logging

Good for programmatic consumption but less human-readable - consider for logging subsystem.

## Testing Strategy

### Manual Testing

```bash
# Test with simple task
amplihack auto "Create a hello world Python script"

# Expected output:
# [AUTO CLAUDE] Starting auto mode (max 10 turns)
# [AUTO CLAUDE]
# --- [Turn 1/10 | Clarifying | 2s] Clarify Objective ---
# [AUTO CLAUDE]
# --- [Turn 2/10 | Planning | 34s] Create Plan ---
# [AUTO CLAUDE]
# --- [Turn 3/10 | Executing | 1m 5s] Execute ---
# [AUTO CLAUDE] --- [Turn 3/10 | Evaluating | 1m 23s] Evaluate ---
# [AUTO CLAUDE] ✓ Objective achieved!
# [AUTO CLAUDE]
# --- [Turn 3/10 | Summarizing | 1m 35s] Summary ---
```

### Integration Testing

- Run with both Claude SDK and subprocess modes
- Verify logging to auto.log file includes progress indicators
- Test with max_turns from 1 to 20
- Verify time formatting for sessions under 1 minute and over 10 minutes

## Branch and PR Information

**Branch**: `feat/auto-transparency-minimal`

**Test Command**:

```bash
uvx --from git+https://github.com/[user]/[repo].git@feat/auto-transparency-minimal amplihack auto "test task"
```

## Future Enhancements

1. **Phase Duration Tracking**: Show time spent in each phase
2. **Progress Percentage**: Estimate completion percentage based on historical data
3. **Estimated Time Remaining**: Predict session completion time
4. **Agent Activity Indicators**: Show which agents are active
5. **Resource Usage**: Memory and CPU metrics for long-running sessions

## References

- Issue: Auto mode transparency enhancement
- Related: Agentic loop orchestrator refactoring
- Philosophy: Ruthless simplicity, minimal friction

---

**Status**: Approved for implementation
**Approach**: Approach 1 (Minimal Progress Indicators)
**Estimated LOC**: ~60
**Estimated Time**: 2-3 hours
