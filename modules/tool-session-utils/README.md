# Session Utilities Tool for Amplifier

Session management utilities including fork management and instruction appending.

## Features

### Fork Manager

Duration-based session forking to stay under time limits:

- **Automatic threshold tracking** - Monitors session duration
- **Configurable threshold** - Default 60 minutes, range 5-68 minutes
- **Thread-safe** - Concurrent access with proper locking
- **Status reporting** - Elapsed time, remaining time, fork count

### Append Handler

Append instructions to running auto mode sessions:

- **Security validation** - Detects prompt injection patterns
- **Rate limiting** - Max 10 appends/minute, 100 pending max
- **Size limits** - 100KB max per instruction
- **Atomic writes** - Safe concurrent access

## Installation

```bash
pip install -e .
```

## Usage

### As Amplifier Tool

```json
// Check fork status
{"operation": "fork_status"}

// Reset fork timer
{"operation": "fork_reset"}

// Check if fork needed
{"operation": "fork_check"}

// Append instruction to running session
{"operation": "append", "instruction": "Focus on error handling next"}

// List pending instructions
{"operation": "list_pending", "session_id": "auto_20250101_120000"}
```

### Programmatic API

```python
from amplifier_tool_session_utils import ForkManager, append_instructions

# Fork management
fork = ForkManager(fork_threshold=3600)  # 60 min
fork.reset()  # Start timing

if fork.should_fork():
    print("Time to fork!")
    print(f"Elapsed: {fork.get_elapsed_time()} seconds")

# Instruction appending
from amplifier_tool_session_utils import append_instructions

result = append_instructions(
    instruction="Please focus on error handling next",
    session_id="auto_20250101_120000",  # Optional
)
print(result.filename)  # Timestamped filename
```

## Configuration

### In bundle.yaml

```yaml
tools:
  - module: amplifier_tool_session_utils
    config:
      fork_threshold: 3600  # seconds
```

## Security

### Prompt Injection Protection

The append handler validates instructions against suspicious patterns:

- "ignore previous instructions"
- "disregard all prior"
- "forget everything"
- "new instructions:"
- "system prompt:"
- Script tags, eval(), exec(), __import__

### Rate Limiting

- Max 10 appends per minute
- Max 100 pending instructions
- Instructions expire when processed

### File Security

- Atomic writes with O_EXCL
- Restrictive permissions (600)
- Microsecond timestamp collision prevention

## Fork Thresholds

| Setting | Value | Use Case |
|---------|-------|----------|
| Minimum | 5 min | Testing |
| Default | 60 min | Normal use |
| Maximum | 68 min | Under 69-min hard limit |

## License

MIT
