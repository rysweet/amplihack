---
description: Start workstream for backlog item
---

# PM Start Workstream

Start a new workstream to work on a backlog item.

## Usage

```bash
/pm:start BL-001
/pm:start BL-002 --agent reviewer
```

## Arguments

- `backlog_id` (required): Backlog item ID (BL-001)
- `--agent`: Agent role (default: builder)
  - builder: Implementation
  - reviewer: Code review
  - tester: Test generation

## Implementation

```python
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / ".claude" / "tools" / "amplihack"))

from pm import cmd_start

# Parse arguments
user_input = """{{USER_INPUT}}"""  # Placeholder for actual user input

# Extract backlog ID
id_match = re.search(r'(BL-\d+)', user_input)
if not id_match:
    print("❌ Error: Backlog ID required (e.g., BL-001)")
    sys.exit(1)

backlog_id = id_match.group(1)

# Extract agent (default: builder)
agent = "builder"
if "--agent reviewer" in user_input:
    agent = "reviewer"
elif "--agent tester" in user_input:
    agent = "tester"

# Execute command
exit_code = cmd_start(
    backlog_id=backlog_id,
    agent=agent,
)

if exit_code != 0:
    print("\nFailed to start workstream. See error above.")
```

## Process

1. Validates no active workstream (Phase 1 limit)
2. Creates delegation package
3. Spawns ClaudeProcess with agent
4. Tracks workstream state

## Output

```
PM: Preparing delegation package...
PM: Spawning builder agent...

✅ Workstream ws-001 started
   Title: Implement feature X
   Agent: builder
   Estimated: 4 hours

Monitor: /pm:status ws-001
```
