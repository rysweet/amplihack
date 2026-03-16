---
name: fleet-copilot
version: 2.0.0
description: >-
  Autonomous co-pilot — agent formulates goal from natural language, enables
  lock mode with SessionCopilot reasoning, works until goal is achieved.
triggers:
  - "fleet copilot"
  - "copilot mode"
  - "work toward goal"
  - "keep going until done"
  - "autonomous mode"
invocable_by: user
---

# Fleet Co-Pilot Skill

The agent takes the user's natural language, formulates a goal with definition
of done, writes it to the goal file, enables lock mode, and starts working.
SessionCopilot reasoning monitors progress on each turn.

## Usage

```
/fleet-copilot fix the auth bug and make sure tests pass
/fleet-copilot implement OAuth2 login and create a PR
/fleet-copilot keep going until all the TODOs are done
```

## Instructions

When this skill is activated:

### Step 1: Formulate the goal

From the user's natural language, create:

1. **Goal**: Clear objective statement
2. **Definition of Done**: Concrete, verifiable criteria

### Step 2: Write the goal file

Use the Write tool to create `.claude/runtime/locks/.lock_goal`:

```
Goal: [objective from user's words]

Definition of Done:
- [criterion 1]
- [criterion 2]
- [criterion 3]
```

### Step 3: Enable lock

```bash
python .claude/tools/amplihack/lock_tool.py lock
```

### Step 4: Start working

Begin immediately. The LockModeHook uses SessionCopilot to monitor and guide.

## Auto-disable

Lock mode stops when:

- Goal achieved (`mark_complete`)
- Human needed (`escalate`)
- User runs `/amplihack:unlock`
