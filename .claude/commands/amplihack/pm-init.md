---
description: Initialize PM Architect for current project
---

# PM Initialize

Initialize PM Architect project management in the current directory.

## Usage

```bash
/pm:init
```

This command will:

1. Check if PM is already initialized
2. Ask interactive questions about your project
3. Create `.pm/` directory structure
4. Generate initial configuration and templates

## Implementation

```python
import sys
sys.path.insert(0, str(Path.cwd() / ".claude" / "tools" / "amplihack"))

from pm import cmd_init

exit_code = cmd_init()
if exit_code != 0:
    print("\nInitialization failed. See error above.")
```

## Next Steps

After initialization:

- Add backlog items: `/pm:add "Task title" --priority HIGH`
- Start working: `/pm:start BL-001`
- Check status: `/pm:status`
