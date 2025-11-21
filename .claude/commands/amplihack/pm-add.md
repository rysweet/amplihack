---
description: Add item to PM backlog
---

# PM Add Item

Add a new work item to the project backlog.

## Usage

```bash
/pm:add "Implement feature X" --priority HIGH
/pm:add "Fix bug Y" --priority MEDIUM --estimated-hours 2
```

## Arguments

- `title` (required): Item title
- `--priority`: HIGH, MEDIUM, LOW (default: MEDIUM)
- `--description`: Detailed description (optional)
- `--estimated-hours`: Estimated hours (default: 4)
- `--tags`: Comma-separated tags (optional)

## Implementation

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / ".claude" / "tools" / "amplihack"))

from pm import cmd_add

# Parse arguments from user input
# For now, use simple approach - enhance later with proper arg parsing
import re

# Extract from context
user_input = """{{USER_INPUT}}"""  # Placeholder for actual user input

# Simple parsing (enhance as needed)
title_match = re.search(r'"([^"]+)"', user_input)
title = title_match.group(1) if title_match else "Untitled task"

priority = "MEDIUM"
if "--priority HIGH" in user_input or "--priority high" in user_input:
    priority = "HIGH"
elif "--priority LOW" in user_input or "--priority low" in user_input:
    priority = "LOW"

estimated_hours = 4
hours_match = re.search(r'--estimated-hours (\d+)', user_input)
if hours_match:
    estimated_hours = int(hours_match.group(1))

description = ""
desc_match = re.search(r'--description "([^"]+)"', user_input)
if desc_match:
    description = desc_match.group(1)

# Execute command
exit_code = cmd_add(
    title=title,
    priority=priority,
    description=description,
    estimated_hours=estimated_hours,
)

if exit_code != 0:
    print("\nFailed to add backlog item. See error above.")
```

## Output

```
✅ Added BL-001: Implement feature X [HIGH]
   Edit details: .pm/backlog/items.yaml
```
