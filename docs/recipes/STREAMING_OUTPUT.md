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

- Unsets `CLAUDECODE` environment variable to allow nested sessions
- Uses isolated temporary directories for each invocation
- Properly cleans up resources after execution

### Progress Monitoring

The `_tail_output` helper function:

```python
@staticmethod
def _tail_output(path: Path, stop: threading.Event) -> None:
    """Tail file and print progress/heartbeat."""
    last_size = 0
    last_activity = time.time()

    while not stop.is_set():
        current_size = path.stat().st_size

        if current_size > last_size:
            # Print last meaningful line as progress
            print(f"  [agent] {lines[-1][:120]}")
            last_activity = time.time()
        elif time.time() - last_activity > 60:
            # Heartbeat when idle
            print(f"  [agent] ... still running ({elapsed}s since last output)")
            last_activity = time.time()

        stop.wait(2)  # Check every 2 seconds
```

## User Experience

### Before (Hard Timeout)

```
Running agent step...
[30 minutes of silence]
ERROR: TimeoutExpired after 1800s
```

### After (Streaming Monitor)

```
Running agent step...
  [agent] Analyzing codebase structure...
  [agent] Found 23 Python modules
  [agent] Checking test coverage...
  [agent] ... still running (62s since last output)
  [agent] Generating report...
Done!
```

## Testing

Comprehensive tests verify:

- Agent steps use Popen (no timeout)
- Bash steps use run with timeout
- Output streams to log file
- Background thread monitors progress
- Heartbeat printed on idle
- Thread stops and cleans up properly
- CLAUDECODE unset in nested sessions

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

- Configurable heartbeat interval
- Structured progress events (not just text)
- Cancellation support (user abort)
- Multiple concurrent monitors
- Progress bars for estimated durations

## Related Issues

- Issue #2360: Original feature implementation
- PR #2010: Security fix for shell=True
- Related to multitask skill output monitoring
