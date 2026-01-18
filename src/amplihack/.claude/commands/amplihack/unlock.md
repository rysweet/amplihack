---
name: amplihack:unlock
version: 1.0.0
description: Disable continuous work mode and resume normal behavior
triggers:
  - "Disable continuous work mode"
  - "Stop working autonomously"
  - "Exit lock mode"
  - "Allow Claude to stop"
---

# Unlock: Disable Continuous Work Mode

Disable continuous work mode to allow Claude to stop normally.

When unlocked, Claude will:

- Stop when appropriate based on task completion
- Follow normal stop behavior
- Allow user interaction for next steps

Use this command to exit continuous work mode after `/amplihack:lock` was enabled.

---

## Instructions

Use the Bash tool to run the lock tool:

```bash
python .claude/tools/amplihack/lock_tool.py unlock
```

This will remove the lock at `.claude/runtime/locks/.lock_active`
