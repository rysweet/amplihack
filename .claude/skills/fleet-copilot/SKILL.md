---
name: fleet-copilot
version: 3.0.0
description: >-
  Autonomous co-pilot — agent formulates goal from natural language and works
  until the goal is achieved. Uses native runtime autopilot (no Python tool).
triggers:
  - "fleet copilot"
  - "copilot mode"
  - "work toward goal"
  - "keep going until done"
  - "autonomous mode"
invocable_by: user
---

# Fleet Co-Pilot Skill

The agent takes the user's natural language, formulates a goal with a
definition of done, and works until the goal is achieved. **No Python
tool is invoked** — autonomous behavior is provided by the runtime's
built-in autopilot (Copilot CLI's autopilot mode, Claude Code's
`--max-turns`, etc.).

## Usage

```
/fleet-copilot fix the auth bug and make sure tests pass
/fleet-copilot implement OAuth2 login and create a PR
/fleet-copilot keep going until all the TODOs are done
```

## Instructions

When this skill is activated:

### Step 1 — Formulate the goal explicitly

From the user's natural language, derive:

1. **Goal**: a single, specific objective sentence
2. **Definition of Done**: observable, verifiable criteria

State both back to the user as the first lines of your response so the
commitment is on the record.

### Step 2 — Begin working immediately

- Do not ask for confirmation.
- Persist between subtasks; the runtime's autopilot keeps you on task
  without a sidecar process.
- After each tool batch, briefly say what you found and what's next.

### Step 3 — Verify and complete

When the Definition of Done is met, run a verification step (re-run
the test, fetch the PR URL, stat the file) and call `task_complete`
with a summary.

## Auto-disable / stop conditions

- Definition of Done is met **and verified** → `task_complete`
- Genuinely blocked on missing info → `ask_user`
- User runs `/amplihack:unlock`

## What changed from v2

- Removed the `python .claude/tools/amplihack/lock_tool.py lock`
  invocation. That tool only worked under Claude Code's hook
  subsystem; in Copilot CLI and other runtimes it was a no-op
  shell-out to a missing relative path.
- Removed the `.claude/runtime/locks/.lock_goal` file write — Copilot
  CLI's autopilot mode does not read that file. The goal lives in
  the conversation, where every runtime can see it.
