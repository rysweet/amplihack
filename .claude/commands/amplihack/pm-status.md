---
description: Show PM project or workstream status
---

# PM Status

Display project overview or detailed workstream status.

## Usage

```bash
/pm:status              # Project overview
/pm:status ws-001       # Workstream details
```

## Arguments

- `ws_id` (optional): Workstream ID for details

## Implementation

```python
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / ".claude" / "tools" / "amplihack"))

from pm import cmd_status

# Parse arguments
user_input = """{{USER_INPUT}}"""  # Placeholder for actual user input

# Extract workstream ID if present
ws_id = None
id_match = re.search(r'(ws-\d+)', user_input)
if id_match:
    ws_id = id_match.group(1)

# Execute command
exit_code = cmd_status(ws_id=ws_id)

if exit_code != 0:
    print("\nFailed to get status. See error above.")
```

## Output

**Project Overview** (no args):

```
════════════════════════════════════════════════════════════
PROJECT: my-project [cli-tool]
════════════════════════════════════════════════════════════

⚡ ACTIVE WORKSTREAMS (1):
  • ws-001: Implement feature X [builder]
    Status: RUNNING (30 min elapsed)

📋 BACKLOG (2 items ready):
  • BL-002: Fix bug Y [HIGH] - READY
  • BL-003: Add docs [MEDIUM] - READY

📊 PROJECT HEALTH: 🟢 HEALTHY
   Quality Bar: balanced
   Active: 1 workstream
```

**Workstream Details** (with ws_id):

```
════════════════════════════════════════════════════════════
WORKSTREAM: ws-001
════════════════════════════════════════════════════════════

Title: Implement feature X
Backlog: BL-001
Status: RUNNING
Agent: builder
Started: 2025-11-20T10:40:00Z
Elapsed: 30 minutes
Progress: 60%

Progress Notes:
  • Generated spec
  • Implemented core logic

Process ID: pm-builder-001
Log: .pm/logs/pm-builder-001.log
```
