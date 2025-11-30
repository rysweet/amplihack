---
name: amplihack:lock
version: 1.0.0
description: Enable continuous work mode without stopping
triggers:
  - "Enable continuous work mode"
  - "Work autonomously"
  - "Don't stop until done"
  - "Keep working through all tasks"
---

# Lock: Enable Continuous Work Mode

**Purpose**: Enable continuous work mode to prevent Claude from stopping until explicitly unlocked.

**Usage**: `amplihack:lock [optional lock message]`

When locked, Claude will:

- use the Bash tool to run the amplihack lock tool:,

**Basic usage (default continuation prompt):**

```bash
python .claude/tools/amplihack/lock_tool.py lock
```

**With custom instruction:**

```bash
python .claude/tools/amplihack/lock_tool.py lock --message "Focus on security fixes first"
```

- Continue working through all TODOs and next steps
- Block stop attempts and keep pursuing the user's objective
- Look for additional work and execute in parallel
- Not stop until `/amplihack:unlock` is run

Use this mode when you want Claude to work autonomously through a complex task without stopping.

## Custom Continuation Messages

The optional message a user can supply on the /amplihack:lock command will be passed to the lock tool with the `--message` flag and allows you to provide a custom instruction that Claude sees when attempting to stop.
This enables:

- Task-specific guidance
- Context about what to prioritize
- Domain-specific instructions
- Direction for autonomous work

**Example custom messages:**

```
"Focus on security fixes first, then performance optimizations"
"Check all API endpoints for authentication issues"
"Run full test suite after each change"
"When condition X is met, you may remove the lock file."
```

**Note**: Messages are limited to 1000 characters. Messages over 500 characters will show a warning.

---

## Instructions

Use the Bash tool to run the lock tool:

**Basic usage (default continuation prompt):**

```bash
python .claude/tools/amplihack/lock_tool.py lock
```

**With custom instruction:**

```bash
python .claude/tools/amplihack/lock_tool.py lock --message "Focus on security fixes first"
```

**Lock files:**

- Lock flag: `.claude/runtime/locks/.lock_active`
- Custom message: `.claude/runtime/locks/.lock_message`
