---
name: lock
version: 2.0.0
description: Enable continuous work mode — dumb or smart co-pilot
triggers:
  - "Enable continuous work mode"
  - "Work autonomously"
  - "Don't stop until done"
  - "Keep working through all tasks"
  - "Work toward this goal"
---

# Lock: Enable Continuous Work Mode

**Purpose**: Enable continuous work mode to prevent Claude from stopping until explicitly unlocked.

**Two modes:**

1. **Dumb mode** (no goal): Injects "continue" on every turn. Cheap, fast, no reasoning.
2. **Smart co-pilot mode** (with `--goal`): Uses SessionCopilot LLM reasoning to suggest contextual next actions, track progress, and auto-disable on goal completion or escalation.

**Usage**: `amplihack:lock [optional lock message]` or `amplihack:lock --goal "your objective"`

When locked, Claude will use the Bash tool to run the amplihack lock tool:

**Basic usage (dumb mode — bare continue):**

```bash
python .claude/tools/amplihack/lock_tool.py lock
```

**With custom instruction (dumb mode with focus):**

```bash
python .claude/tools/amplihack/lock_tool.py lock --message "Focus on security fixes first"
```

**Smart co-pilot mode (LLM-reasoned guidance):**

```bash
python .claude/tools/amplihack/lock_tool.py lock --goal "Fix the auth bug, write tests, create PR"
```

**Combined (goal + message):**

```bash
python .claude/tools/amplihack/lock_tool.py lock --goal "Implement OAuth2 login" --message "Use PKCE flow"
```

## Smart Co-Pilot Mode

When `--goal` is provided, the hook uses `SessionCopilot` from the fleet module to:

- **Read the session transcript** and detect the current agent status
- **Reason about the next action** using LLM-powered analysis
- **Inject specific guidance** instead of generic "continue"
- **Track progress** toward the stated goal
- **Auto-disable** when the goal is achieved (`mark_complete`)
- **Escalate** to the human when the co-pilot is uncertain

The co-pilot actions:
| Action | Behavior |
|--------|----------|
| `send_input` (confidence >= 0.6) | Injects reasoned next step |
| `wait` | Agent is working — no intervention |
| `mark_complete` | Goal achieved — auto-disables lock |
| `escalate` | Needs human — auto-disables lock |

## Custom Continuation Messages

The optional `--message` flag provides a custom instruction that Claude sees when attempting to stop.

**Example custom messages:**

```
"Focus on security fixes first, then performance optimizations"
"Check all API endpoints for authentication issues"
"Run full test suite after each change"
```

**Note**: Messages are limited to 1000 characters.

---

## Instructions

Use the Bash tool to run the lock tool. Parse the user's command to determine if they provided a goal, a message, or both.

**If the user provides a goal (smart mode):**

```bash
python .claude/tools/amplihack/lock_tool.py lock --goal "user's goal here"
```

**If the user provides just a message (dumb mode):**

```bash
python .claude/tools/amplihack/lock_tool.py lock --message "user's message here"
```

**If the user provides both:**

```bash
python .claude/tools/amplihack/lock_tool.py lock --goal "user's goal" --message "user's focus"
```

**If the user provides nothing (plain dumb mode):**

```bash
python .claude/tools/amplihack/lock_tool.py lock
```

**Lock files:**

- Lock flag: `.claude/runtime/locks/.lock_active`
- Custom message: `.claude/runtime/locks/.lock_message`
- Goal (smart mode): `.claude/runtime/locks/.lock_goal`
