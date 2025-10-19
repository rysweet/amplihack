# Auto Mode Transparency - Current State Analysis

## Executive Summary

Auto mode currently lacks visibility into its execution state, making it difficult for users to understand what's happening during the autonomous execution loop. This document analyzes the current implementation and its limitations.

## Current Implementation Analysis

### Architecture Overview

Auto mode is implemented in `/src/amplihack/launcher/auto_mode.py` as a class-based orchestrator:

```
AutoMode
├── __init__() - Initialize with SDK, prompt, max_turns
├── run() - Main execution loop
├── run_sdk() - Execute SDK commands (subprocess or Python SDK)
├── run_hook() - Run session_start/stop hooks
└── log() - Basic logging to file and stdout
```

### Execution Flow

1. **Turn 1: Clarify Objective** - Transforms user prompt into clear objectives with evaluation criteria
2. **Turn 2: Create Plan** - Breaks down work into steps, identifies parallel opportunities
3. **Turns 3-N: Execute & Evaluate** - Iteratively executes plan and evaluates progress
4. **Final Turn: Summary** - Provides comprehensive summary of session

### Integration Points

**TUI Integration:**
- Simple TUI exists at `/src/amplihack/testing/simple_tui.py`
- Used for testing, not integrated with auto mode
- Uses subprocess approach with gadugi-agentic-test framework

**Console Integration:**
- Auto mode launched via CLI: `amplihack claude --auto -- -p "prompt"`
- Handled in `/src/amplihack/cli.py` via `handle_auto_mode()`
- Supports both Claude SDK and subprocess approaches

**Output Mechanisms:**
- `self.log()` - Writes to console and `.claude/runtime/logs/auto_{sdk}_{timestamp}/auto.log`
- SDK streaming (Claude SDK only) - Real-time token streaming to console
- Subprocess mirroring - stdout/stderr mirrored in real-time

## Current Pain Points

### 1. Lack of Progress Indication

**Problem:** Users don't know what turn they're on or how much progress has been made.

**Evidence:**
```python
# Line 291: Turn logging is basic
self.log(f"\n--- TURN {self.turn}: Clarify Objective ---")
```

**User Impact:** Users stare at console output without understanding where in the multi-turn loop they are.

### 2. No Time Estimates

**Problem:** No indication of how long execution will take or has taken.

**Evidence:**
```python
# Line 283: Start time tracked but not displayed progressively
self.log(f"Starting auto mode (max {self.max_turns} turns)")
```

**User Impact:** Users can't estimate remaining time or decide whether to wait.

### 3. Opaque Agent Orchestration

**Problem:** When auto mode invokes specialized agents, users don't see which agents are running.

**Evidence:**
```python
# Lines 347-366: Agent orchestration happens invisibly within SDK calls
execute_prompt = f"""{self._build_philosophy_context()}
Task: Execute the next part of the plan using specialized agents where possible.
"""
```

**User Impact:** Users don't understand what agents are doing or why certain decisions are made.

### 4. Limited Context in TUI Mode

**Problem:** TUI integration is minimal and doesn't provide rich visualization.

**Evidence:**
- SimpleTUITester is focused on testing, not user interaction
- No rich progress bars, status indicators, or split-screen views

**User Impact:** Console-only interface lacks visual feedback.

### 5. No Machine-Readable Progress

**Problem:** Progress updates are human-readable logs only, not machine-parseable.

**Evidence:**
```python
# Line 50: Logging is text-based only
with open(self.log_dir / "auto.log", "a") as f:
    f.write(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}\n")
```

**User Impact:** External tools can't monitor or visualize auto mode execution.

### 6. Subprocess Opacity

**Problem:** When using subprocess approach (Copilot, fallback mode), execution is completely opaque until output appears.

**Evidence:**
```python
# Lines 69-161: Subprocess execution with output mirroring
# No progress indication during long-running commands
process = subprocess.Popen(...)
```

**User Impact:** Long pauses with no feedback create anxiety about whether system is working.

## Current Strengths

### 1. Clean Modular Design

The AutoMode class is well-structured and follows the brick philosophy:
- Self-contained module with clear responsibility
- Minimal dependencies (subprocess, Claude SDK)
- Easy to extend with new features

### 2. Dual SDK Support

Supports both Claude SDK (with streaming) and subprocess approach:
- Claude SDK provides token-level streaming
- Subprocess provides real-time output mirroring
- Graceful fallback when SDK unavailable

### 3. Comprehensive Logging

All execution is logged to timestamped directories:
- `.claude/runtime/logs/auto_{sdk}_{timestamp}/auto.log`
- Includes turn-by-turn details
- Preserves full execution history

### 4. Hook Integration

Session start/stop hooks provide extension points:
- `session_start` hook runs before first turn
- `stop` hook runs after completion
- Enables custom logging, metrics, cleanup

## Technical Details

### Key Files

1. **Auto Mode Core:**
   - `/src/amplihack/launcher/auto_mode.py` (422 lines)
   - Class: `AutoMode`
   - Dependencies: subprocess, pty, asyncio, claude_agent_sdk (optional)

2. **CLI Integration:**
   - `/src/amplihack/cli.py`
   - Function: `handle_auto_mode()` (lines 104-134)
   - Launches AutoMode from CLI arguments

3. **TUI Testing:**
   - `/src/amplihack/testing/simple_tui.py`
   - Class: `SimpleTUITester`
   - Currently used for testing only

4. **Documentation:**
   - `/docs/AUTO_MODE.md` - Comprehensive user documentation
   - `.claude/commands/amplihack/auto.md` - Command reference

### Execution Flow Detail

```
User: amplihack claude --auto -- -p "task"
  ↓
cli.py: handle_auto_mode()
  ↓
auto_mode.py: AutoMode.run()
  ↓
Turn 1: run_sdk(clarify_prompt)
  → _run_turn_with_sdk() OR _run_sdk_subprocess()
  → Stream/mirror output to console
  ↓
Turn 2: run_sdk(plan_prompt)
  → (same as Turn 1)
  ↓
Turns 3-N: Loop until complete
  → Execute step
  → Evaluate progress
  → Continue or exit
  ↓
Final: Summary generation
  ↓
Cleanup: stop hook
```

### Data Flow

```
AutoMode.run()
  ├─> self.log() ─> Console (stdout)
  │               └─> File (.claude/runtime/logs/auto_*/auto.log)
  │
  ├─> run_sdk() ─> SDK/Subprocess
  │               └─> Real-time output ─> Console (mirrored)
  │
  └─> run_hook() ─> Hook scripts
                   └─> Custom logging/metrics
```

## Opportunities for Improvement

### High-Priority Opportunities

1. **Progress Visibility:** Show current turn, total turns, elapsed time
2. **Phase Indicators:** Clear visual separation between clarify/plan/execute/evaluate
3. **Agent Transparency:** Show which agents are running and their status
4. **Time Estimates:** Show elapsed time and estimated remaining time

### Medium-Priority Opportunities

1. **Rich TUI:** Terminal UI with progress bars and status indicators
2. **JSON Protocol:** Machine-readable progress updates for external tools
3. **Parallel Agent Visualization:** Show multiple agents running in parallel

### Low-Priority Opportunities

1. **Web Dashboard:** Browser-based monitoring interface
2. **Historical Analytics:** Track performance across multiple runs
3. **Interactive Controls:** Pause/resume functionality

## Constraints and Requirements

### Must Preserve

1. **Ruthless Simplicity:** Any transparency solution must remain simple
2. **Modular Design:** Changes should be self-contained modules (bricks)
3. **Zero Dependencies:** Avoid heavy external dependencies unless justified
4. **Backward Compatibility:** Existing CLI and API must continue to work

### Must Enable

1. **Real-time Feedback:** Users must see progress as it happens
2. **Clear Context:** Users must understand what phase/turn/agent is running
3. **Time Awareness:** Users must know elapsed and estimated remaining time
4. **Non-Intrusive:** Transparency features should not slow down execution

## Next Steps

This analysis forms the foundation for designing multiple approaches to improve auto mode transparency. The following design document will propose 3-4 distinct architectural approaches, each with different trade-offs between complexity, value, and user impact.
