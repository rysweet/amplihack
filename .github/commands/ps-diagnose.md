# GitHub Copilot Command Reference: ps-diagnose

**Source**: `~/.amplihack/.claude/commands/amplihack/ps-diagnose.md`

---

## Command Metadata

- **name**: ps-diagnose
- **description**: Diagnose power-steering infinite loop issues
- **category**: debugging

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/ps-diagnose.md

# Use patterns from this command
gh copilot suggest --context .github/commands/ps-diagnose.md "your task"
```

---

## Original Command Documentation


# Power Steering Diagnostics

This command analyzes power-steering state and diagnostic logs to detect infinite loop patterns.

## What This Command Does

1. Loads current power-steering state
2. Analyzes diagnostic log for patterns:
   - Counter stall (same value repeated 10+ times)
   - Oscillation (A → B → A → B pattern)
   - High write failure rate (>30%)
3. Displays diagnostic report with:
   - Current state (turn count, blocks)
   - Recent diagnostic events
   - Health status (healthy/warning/critical)
   - Recommended actions

## Usage

```bash
/amplihack:ps-diagnose
```

## Implementation

You should:

1. **Load State**: Get current power-steering state from `~/.amplihack/.claude/runtime/power-steering/{session_id}/turn_state.json`

2. **Analyze Diagnostics**: Use `detect_infinite_loop()` from `power_steering_diagnostics.py`

3. **Display Report**:

   ```
   Power Steering Diagnostics Report
   ==================================

   Current State:
   - Turn Count: {turn_count}
   - Consecutive Blocks: {consecutive_blocks}
   - Session ID: {session_id}

   Infinite Loop Detection:
   - Counter Stall: {detected/not detected}
   - Oscillation: {detected/not detected}
   - Write Failure Rate: {percentage}%

   Health Status: {healthy/warning/critical}

   Recent Events (last 10):
   {list recent diagnostic log entries}

   Recommended Actions:
   {context-specific recommendations}
   ```

4. **Recommendations**:
   - If stall detected: "Counter stuck at {value}. This indicates a write/read bug."
   - If oscillation detected: "Counter oscillating between {values}. Check state persistence."
   - If high failure rate: "Write failures exceeding 30%. Check filesystem and permissions."
   - If healthy: "No issues detected. System operating normally."

## Files to Read

- `~/.amplihack/.claude/runtime/power-steering/{session_id}/turn_state.json` - Current state
- `~/.amplihack/.claude/runtime/power-steering/{session_id}/diagnostic.jsonl` - Diagnostic log

## Implementation Note

Use the TurnStateManager and diagnostic utilities already implemented in:

- `~/.amplihack/.claude/tools/amplihack/hooks/power_steering_state.py`
- `~/.amplihack/.claude/tools/amplihack/hooks/power_steering_diagnostics.py`
