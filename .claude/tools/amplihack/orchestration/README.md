# Orchestration Infrastructure

Complete orchestration infrastructure for managing multiple Claude CLI processes with different execution patterns.

## Overview

This module provides the core building blocks for orchestrating Claude processes:

- **ClaudeProcess**: Manages a single subprocess with output capture, timeout, and logging
- **ProcessResult**: Structured result with exit code, output, duration, and process ID
- **OrchestratorSession**: Session management with logging and process factory
- **Execution Helpers**: Functions for parallel, sequential, fallback, and batched execution

## Module Structure

```
orchestration/
├── README.md               # This file
├── EXAMPLE_USAGE.py        # Comprehensive usage examples
├── __init__.py             # Public exports
├── claude_process.py       # Core process management
├── execution.py            # Execution strategies
├── session.py              # Session management
└── patterns/               # Reusable patterns (future)
    └── __init__.py
```

## Core Components

### ClaudeProcess

Manages a single Claude CLI subprocess:

```python
from orchestration import ClaudeProcess

process = ClaudeProcess(
    prompt="Analyze this code",
    process_id="security-analysis",
    working_dir=Path("/project"),
    log_dir=Path("/logs"),
    model="claude-3-opus",
    stream_output=True,
    timeout=300
)

result = process.run()
print(f"Exit code: {result.exit_code}")
print(f"Duration: {result.duration}s")
print(f"Output: {result.output}")
```

**Features**:

- PTY-based stdin to prevent blocking
- Real-time output streaming
- Thread-based output capture
- Timeout support with graceful termination
- Comprehensive logging

### ProcessResult

Structured result from process execution:

```python
@dataclass
class ProcessResult:
    exit_code: int      # 0=success, -1=timeout, other=error
    output: str         # Combined stdout
    stderr: str         # Stderr output
    duration: float     # Execution time in seconds
    process_id: str     # Process identifier
```

### OrchestratorSession

Session management with logging:

```python
from orchestration import OrchestratorSession

session = OrchestratorSession(
    pattern_name="parallel-analysis",
    working_dir=Path("/project")
)

# Factory method creates configured processes
p1 = session.create_process("Analyze security", "security")
p2 = session.create_process("Analyze performance", "performance")

session.log("Starting analysis")
```

## Execution Strategies

### Parallel Execution

Run multiple processes concurrently:

```python
from orchestration import run_parallel

results = run_parallel(processes, max_workers=3)

successful = [r for r in results if r.exit_code == 0]
print(f"{len(successful)}/{len(results)} succeeded")
```

**Use cases**:

- Multi-agent analysis
- Independent tasks
- Batch processing

### Sequential Execution

Run processes one at a time:

```python
from orchestration import run_sequential

# With output passing
results = run_sequential(
    processes,
    pass_output=True,      # Pass output to next process
    stop_on_failure=True   # Stop on first error
)
```

**Use cases**:

- Pipeline stages
- Dependent tasks
- Iterative refinement

### Fallback Strategy

Try processes until one succeeds:

```python
from orchestration import run_with_fallback

result = run_with_fallback(processes, timeout=300)

if result.exit_code == 0:
    print(f"Succeeded with: {result.process_id}")
```

**Use cases**:

- Multiple approaches
- Different models
- Retry with degraded capabilities

### Batched Execution

Run processes in parallel batches:

```python
from orchestration import run_batched

results = run_batched(
    processes,
    batch_size=3,
    pass_output=True  # Pass batch outputs to next batch
)
```

**Use cases**:

- Resource-limited parallelism
- Progressive processing
- Batch dependencies

## Usage Examples

### Multi-Agent Parallel Analysis

```python
from pathlib import Path
from orchestration import OrchestratorSession, run_parallel

# Create session
session = OrchestratorSession("multi-agent")

# Create agent processes
agents = [
    session.create_process("Analyze security", "security"),
    session.create_process("Analyze performance", "performance"),
    session.create_process("Analyze maintainability", "maintainability"),
]

# Run in parallel
results = run_parallel(agents, max_workers=3)

# Process results
for result in results:
    if result.exit_code == 0:
        print(f"✓ {result.process_id}: {result.duration:.1f}s")
    else:
        print(f"✗ {result.process_id}: FAILED")
```

### Sequential Pipeline

```python
session = OrchestratorSession("pipeline")

stages = [
    session.create_process("Analyze codebase", "analyze"),
    session.create_process("Create improvement plan", "plan"),
    session.create_process("Implement improvements", "implement"),
]

results = run_sequential(stages, pass_output=True, stop_on_failure=True)
```

### Adaptive Fallback

```python
session = OrchestratorSession("adaptive")

strategies = [
    session.create_process("Advanced analysis", "advanced", timeout=300),
    session.create_process("Standard analysis", "standard", timeout=300),
    session.create_process("Basic analysis", "basic", timeout=300),
]

result = run_with_fallback(strategies, timeout=300)
```

## Design Principles

### Ruthless Simplicity

- Direct implementation, no over-engineering
- Reuse proven patterns from auto_mode.py
- Clear contracts and boundaries

### Modular Design (Bricks & Studs)

- **ClaudeProcess** = Brick (self-contained subprocess management)
- **Execution helpers** = Studs (clear coordination interfaces)
- **OrchestratorSession** = Context (shared session state)

### Zero-BS Implementation

- No stubs or placeholders
- Every function works or doesn't exist
- Comprehensive error handling
- Real logging and output capture

## Regeneration

This module can be regenerated from:

1. This README (specification)
2. auto_mode.py (proven subprocess patterns)
3. Project philosophy (PHILOSOPHY.md)

Key extraction points from auto_mode.py:

- Lines 69-161: Subprocess mechanics with PTY
- Lines 82-97: PTY setup and Popen
- Lines 103-128: Thread-based output capture
- Lines 110-127: PTY stdin feeding

## Future Extensions

Potential additions (not implemented yet):

1. **Pattern Library**: Pre-built orchestration patterns
2. **Result Aggregation**: Structured result combination
3. **Progress Tracking**: Real-time progress monitoring
4. **Resource Management**: CPU/memory limits per process
5. **Retry Logic**: Configurable retry strategies
6. **Output Filtering**: Selective output capture

## Testing

To test the infrastructure:

```python
# Run examples
python orchestration/EXAMPLE_USAGE.py

# Check logs
ls -la .claude/runtime/logs/

# Verify specific session
cat .claude/runtime/logs/<session_id>/session.log
```

## Integration

The orchestration infrastructure is designed to be integrated with:

- **Auto mode**: Replace inline subprocess logic
- **Workflow engine**: Orchestrate workflow steps
- **Agent system**: Coordinate multiple agents
- **CI/CD**: Parallel test execution

## Contract

### ClaudeProcess Contract

**Inputs**:

- prompt: str (required)
- process_id: str (required)
- working_dir: Path (required)
- log_dir: Path (required)
- model: Optional[str]
- stream_output: bool = True
- timeout: Optional[int] = None

**Outputs**:

- ProcessResult with exit_code, output, stderr, duration, process_id

**Guarantees**:

- Logs all operations
- Cleans up resources (PTY, threads)
- Handles timeout gracefully
- Never blocks indefinitely
- Captures all output

### Execution Helpers Contract

**run_parallel**:

- Input: List[ClaudeProcess], optional max_workers
- Output: List[ProcessResult] in completion order
- Guarantees: All processes execute, exceptions converted to failed results

**run_sequential**:

- Input: List[ClaudeProcess], optional pass_output, stop_on_failure
- Output: List[ProcessResult] in execution order
- Guarantees: Order preserved, output passing works, stops on failure if requested

**run_with_fallback**:

- Input: List[ClaudeProcess], optional timeout
- Output: Single ProcessResult (first success or last failure)
- Guarantees: Tries all until success, applies timeout to each

**run_batched**:

- Input: List[ClaudeProcess], batch_size, optional pass_output
- Output: List[ProcessResult] in batch completion order
- Guarantees: Batches process in order, batch outputs can pass to next batch

## License

Part of the Microsoft Hackathon 2025 Agentic Coding Framework.
