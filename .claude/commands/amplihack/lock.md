---
name: lock
version: 3.0.0
description: Enable autonomous co-pilot mode — agent formulates goal and works until done
triggers:
  - "Enable continuous work mode"
  - "Work autonomously"
  - "Don't stop until done"
  - "Keep working through all tasks"
  - "Work toward this goal"
---

# Lock: Autonomous Co-Pilot Mode

**Purpose**: Enable autonomous co-pilot mode. The agent formulates a goal from the user's natural language, defines what "done" looks like, and works until the goal is achieved or it needs human help.

## Instructions

When the user invokes this command:

### Step 1: Formulate the goal

Read the user's message. From their natural language, formulate:

1. **Goal**: A clear, specific objective statement
2. **Definition of Done**: Concrete criteria for when the goal is achieved (e.g. "tests pass", "PR created", "file exists with X content")

Write both to the goal file as a single document:

```bash
mkdir -p .claude/runtime/locks
```

Then use the Write tool to create `.claude/runtime/locks/.lock_goal` with content like:

```
Goal: [clear objective from user's words]

Definition of Done:
- [concrete criterion 1]
- [concrete criterion 2]
- [concrete criterion 3]
```

### Step 2: Enable lock

```bash
python .claude/tools/amplihack/lock_tool.py lock
```

### Step 3: Begin working

Immediately start working toward the goal. Do not ask for confirmation. The LockModeHook will use SessionCopilot to monitor progress and provide guidance on each turn.

## How it works

1. The hook fires on every `provider:request` event
2. SessionCopilot reads the session transcript and reasons about progress
3. If the agent is working — no intervention
4. If the agent is idle — injects specific next-step guidance
5. If the goal is achieved — auto-disables lock mode
6. If stuck — auto-disables and escalates to the user

## Disabling

Lock mode auto-disables when:

- Goal is achieved (`mark_complete`)
- Co-pilot needs human help (`escalate`)
- User runs `/amplihack:unlock`

## Examples

User says: "fix the auth bug and make sure tests pass"
→ Agent writes goal: "Fix the authentication bug. Definition of Done: auth tests pass, no regressions in test suite."
→ Agent enables lock, starts working.

User says: "implement OAuth2 login and create a PR"
→ Agent writes goal: "Implement OAuth2 login flow. Definition of Done: OAuth2 endpoint works, tests cover happy path and error cases, PR created on GitHub."
→ Agent enables lock, starts working.

User says: "keep going"
→ Agent writes goal: "Continue working on the current task until all pending items are complete. Definition of Done: all TODO items resolved, tests pass."
→ Agent enables lock, continues.
