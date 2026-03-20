# Streaming Output Monitoring in Recipe Adapters

## Overview

Recipe adapters implement streaming output monitoring to replace hard timeouts with intelligent progress tracking. This provides a better user experience for long-running agent operations while maintaining fast feedback for quick tasks.

## Problem

Previous implementation used hard 30-minute timeouts on agent steps, which:

- Killed legitimate long-running operations prematurely
- Provided no progress feedback during execution
- Created anxiety for users ("is it still working?")
- Was inflexible for operations requiring different durations

## Solution

Replace timeouts with streaming output monitoring:

### Agent Steps (No Timeout)

- Use `subprocess.Popen` instead of `subprocess.run`
- Stream output to a log file in real-time
- Background thread tails the log file
- Print progress every 2 seconds when output changes
- Print heartbeat every 60 seconds when idle
- Process runs until completion (no artificial timeout)

### Bash Steps (Keep Timeout)

- Use `subprocess.run` with explicit timeout (default 120s)
- Bash commands should be fast (file operations, git commands)
- Timeout prevents runaway shell commands
- Failures are explicit and immediate

## Implementation Details

### CLISubprocessAdapter

```python
def execute_agent_step(self, prompt: str, ...) -> str:
    """Execute agent step without timeout, stream output."""
    # 1. Create log file for output capture
    output_file = output_dir / f"agent-step-{int(time.time())}.log"

    # 2. Launch process with Popen (no timeout parameter)
    with open(output_file, "w") as log_fh:
        proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)

    # 3. Start background thread to tail output
    tail_thread = threading.Thread(
        target=self._tail_output,
        args=(output_file, stop_event),
        daemon=True
    )
    tail_thread.start()

    # 4. Wait for completion (no timeout)
    proc.wait()

    # 5. Stop monitoring and cleanup
    stop_event.set()
    tail_thread.join(timeout=2)
```

### NestedSessionAdapter

Same pattern as CLISubprocessAdapter, plus:

- Uses isolated temporary directories for each invocation
- Properly cleans up resources after execution

### Progress Monitoring

The Rust recipe runner's heartbeat thread monitors the agent's output log file:

```rust
// Background heartbeat thread (simplified)
let mut last_size = 0u64;
let mut last_activity = Instant::now();
let start_time = Instant::now();

loop {
    let current_size = metadata(&output_path).len();

    if current_size > last_size {
        // Print last meaningful line as progress
        eprintln!("  [agent] {}", last_line_of(output_path));
        last_activity = Instant::now();
    } else if last_activity.elapsed() > Duration::from_secs(30) {
        // Heartbeat when idle — show total elapsed, idle time, and PID status
        eprintln!("  [agent] ... working ({}s elapsed, {}s since last output, pid {} alive)",
            start_time.elapsed().as_secs(),
            last_activity.elapsed().as_secs(),
            child_pid);
        last_activity = Instant::now();
    }

    sleep(Duration::from_secs(2));
}
```

Key design decisions:

- **30-second heartbeat interval** (reduced from 60s) for faster feedback
- **Total elapsed time** shown so users know how long the step has been running
- **PID alive check** confirms the process hasn't crashed silently
- **Step-type hints** in progress listener: agent steps show `[agent — may take several minutes]`

## User Experience

### Before (Hard Timeout)

```
Running agent step...
[30 minutes of silence]
ERROR: TimeoutExpired after 1800s
```

### After (Streaming Monitor)

```
▶ step-02b-analyze-codebase [agent — may take several minutes]
  [agent] Analyzing codebase structure...
  [agent] Found 23 Python modules
  [agent] Checking test coverage...
  [agent] ... working (45s elapsed, 32s since last output, pid 12345 alive)
  [agent] ... working (78s elapsed, 33s since last output, pid 12345 alive)
  [agent] Generating report...
  ✓ step-02b-analyze-codebase (95.2s)
```

## Testing

Comprehensive tests verify:

- Agent steps use Popen (no timeout)
- Bash steps use run with timeout
- Output streams to log file
- Background thread monitors progress
- Heartbeat printed on idle
- Thread stops and cleans up properly
- Child environment cleaned via shared utility

See `tests/unit/recipes/test_streaming_adapters.py` for complete test coverage.

## Benefits

1. **No Arbitrary Timeouts**: Long-running operations complete successfully
2. **Progress Feedback**: Users see what's happening in real-time
3. **Heartbeat Monitoring**: Idle operations show they're still alive
4. **Clean Architecture**: Separation between fast (bash) and slow (agent) operations
5. **Resource Cleanup**: Log files removed after execution
6. **Nested Session Support**: Works inside Claude Code

## Migration Notes

### From Old Pattern

```python
# OLD: Hard timeout, no progress
result = subprocess.run(cmd, timeout=1800, ...)
```

### To New Pattern

```python
# NEW: Streaming output, no timeout for agents
with open(log_file, "w") as fh:
    proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)

# Monitor in background
threading.Thread(target=tail_output, args=(log_file, stop_event)).start()

# Wait without timeout
proc.wait()
```

### Bash Steps Unchanged

```python
# Bash steps KEEP timeout (they should be fast)
subprocess.run(["/bin/bash", "-c", command], timeout=120)
```

## Future Enhancements

Potential improvements:

- Configurable heartbeat interval (currently 30s, was 60s)
- Structured progress events (not just text)
- Cancellation support (user abort)
- Multiple concurrent monitors
- Progress bars for estimated durations

## Related Issues

- Issue #2360: Original feature implementation
- PR #2010: Security fix for shell=True
- Related to multitask skill output monitoring
