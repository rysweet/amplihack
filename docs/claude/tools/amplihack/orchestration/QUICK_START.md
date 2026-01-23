# Orchestration Infrastructure - Quick Start

## 5-Minute Guide

### Installation

The orchestration infrastructure is already installed at:

```
.claude/tools/amplihack/orchestration/
```

### Basic Import

```python
from pathlib import Path
from orchestration import (
    OrchestratorSession,
    run_parallel,
    run_sequential,
)
```

## Common Patterns

### Pattern 1: Parallel Multi-Agent Analysis

Run multiple agents in parallel:

```python
# Create session
session = OrchestratorSession("parallel-agents")

# Create agent processes
agents = [
    session.create_process("Analyze security", "security"),
    session.create_process("Analyze performance", "performance"),
    session.create_process("Analyze maintainability", "maintainability"),
]

# Run in parallel
results = run_parallel(agents, max_workers=3)

# Check results
for r in results:
    if r.exit_code == 0:
        print(f"✓ {r.process_id} completed in {r.duration:.1f}s")
```

### Pattern 2: Sequential Pipeline

Run stages with output passing:

```python
session = OrchestratorSession("pipeline")

stages = [
    session.create_process("Analyze code", "analyze"),
    session.create_process("Create plan", "plan"),
    session.create_process("Implement", "implement"),
]

results = run_sequential(stages, pass_output=True)
```

### Pattern 3: Retry with Fallback

Try different approaches:

```python
from orchestration import run_with_fallback

session = OrchestratorSession("retry")

attempts = [
    session.create_process("Complex approach", "advanced", timeout=300),
    session.create_process("Simple approach", "basic", timeout=300),
]

result = run_with_fallback(attempts)
```

### Pattern 4: Batched Processing

Process many items in controlled batches:

```python
from orchestration import run_batched

session = OrchestratorSession("batch")

# Create many processes
processes = [
    session.create_process(f"Process item {i}", f"item-{i}")
    for i in range(20)
]

# Run in batches of 5
results = run_batched(processes, batch_size=5)
```

## Quick Reference

### OrchestratorSession

```python
session = OrchestratorSession(
    pattern_name="my-pattern",      # Pattern identifier
    working_dir=Path("/project"),   # Optional: defaults to cwd
    base_log_dir=Path("/logs"),     # Optional: defaults to .claude/runtime/logs
    model="claude-3-opus"           # Optional: defaults to CLI default
)

# Factory method
process = session.create_process(
    prompt="Task description",
    process_id="task-001",          # Optional: auto-generated if omitted
    timeout=300                     # Optional: seconds
)
```

### ClaudeProcess

```python
from orchestration import ClaudeProcess

process = ClaudeProcess(
    prompt="Analyze this code",
    process_id="analyze-001",
    working_dir=Path.cwd(),
    log_dir=Path(".logs"),
    model="claude-3-sonnet",        # Optional
    stream_output=True,             # Optional: default True
    timeout=300                     # Optional: default None (no timeout)
)

result = process.run()
```

### ProcessResult

```python
# After running a process
result = process.run()

# Check result
if result.exit_code == 0:
    print(f"Success! Output:\n{result.output}")
else:
    print(f"Failed with code {result.exit_code}")
    print(f"Error: {result.stderr}")

print(f"Duration: {result.duration:.1f}s")
```

### Execution Helpers

```python
from orchestration import (
    run_parallel,
    run_sequential,
    run_with_fallback,
    run_batched
)

# Parallel (independent tasks)
results = run_parallel(processes, max_workers=3)

# Sequential (dependent tasks)
results = run_sequential(
    processes,
    pass_output=True,       # Pass output to next
    stop_on_failure=True    # Stop on first error
)

# Fallback (retry until success)
result = run_with_fallback(processes, timeout=300)

# Batched (controlled parallelism)
results = run_batched(
    processes,
    batch_size=5,
    pass_output=True        # Pass batch outputs
)
```

## Logging

All operations are logged automatically:

```bash
# Session log
.claude/runtime/logs/<session_id>/session.log

# Process logs
.claude/runtime/logs/<session_id>/<process_id>.log
```

## Exit Codes

- `0`: Success
- `-1`: Timeout or fatal error
- `> 0`: Claude CLI error

## Common Mistakes to Avoid

### ❌ Don't: Create processes without a session

```python
# Hard to manage logs and state
process = ClaudeProcess(prompt, id, cwd, log_dir, ...)
```

### ✅ Do: Use session factory

```python
session = OrchestratorSession("my-pattern")
process = session.create_process(prompt, id)
```

### ❌ Don't: Run sequential when parallel is possible

```python
# Slower for independent tasks
results = run_sequential(independent_tasks)
```

### ✅ Do: Use parallel for independent tasks

```python
results = run_parallel(independent_tasks)
```

### ❌ Don't: Forget timeout for long-running tasks

```python
process = session.create_process(prompt)  # No timeout!
```

### ✅ Do: Set reasonable timeouts

```python
process = session.create_process(prompt, timeout=300)
```

## Examples

See detailed examples in:

- `EXAMPLE_USAGE.py` - Runnable examples
- `README.md` - Complete documentation

## Troubleshooting

### Import Error

```python
# Add to path
import sys
sys.path.insert(0, '.claude/tools/amplihack')
from orchestration import *
```

### Process Hangs

- Check timeout is set
- Verify working directory exists
- Check logs in `~/.amplihack/.claude/runtime/logs/`

### Parallel Execution Issues

- Reduce `max_workers` if resource-constrained
- Check individual process logs
- Verify processes are independent

## Next Steps

1. **Read**: `README.md` for complete documentation
2. **Run**: `EXAMPLE_USAGE.py` for working examples
3. **Integrate**: Replace subprocess logic in existing code
4. **Extend**: Create patterns in `patterns/` directory

## Support

- Documentation: `README.md`
- Implementation: `IMPLEMENTATION_SUMMARY.md`
- Examples: `EXAMPLE_USAGE.py`
- Source: `claude_process.py`, `execution.py`, `session.py`
