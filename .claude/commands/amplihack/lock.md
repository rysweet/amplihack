---
name: lock
version: 4.0.0
description: Commit to a goal and work autonomously until it is achieved
triggers:
  - "Enable continuous work mode"
  - "Work autonomously"
  - "Don't stop until done"
  - "Keep working through all tasks"
  - "Work toward this goal"
---

# Lock: Commit to Autonomous Goal Pursuit

**Purpose**: Commit to a single goal and work autonomously toward it until
the goal is achieved or you genuinely need human help. Uses native
runtime autopilot — **no Python tool, no external hook, no `python` shell-out**.

## Runtime support

This command works whether or not your runtime has built-in autopilot:

- **GitHub Copilot CLI**: Native autopilot is on while the user holds the
  session in autopilot mode (Shift+Tab toggle in the UI). The system
  injects `<autopilot_mode>` reminders so you stay on task without the
  user re-prompting between turns.
- **Claude Code**: Built-in `--max-turns` and the SessionCopilot hook
  fulfill the same role when configured.
- **Anywhere else**: Just persist on the goal until done. The contract
  below is what matters; no daemon needs to be running.

## Instructions

When the user invokes this command:

### Step 1 — Formulate the goal explicitly

Read the user's message. Extract:

1. **Goal**: A single, specific objective sentence
2. **Definition of Done**: Observable, verifiable criteria
   (e.g. "tests pass", "PR opened", "file exists with X content")

State both back to the user as the first lines of your response so the
commitment is on the record. You don't need to write a goal file — the
runtime's autopilot already keeps you on task.

### Step 2 — Begin working immediately

- Do not ask for confirmation.
- Do not pause between subtasks.
- After each tool batch, briefly say what you found and what's next.
- When the Definition of Done is met, run a verification step
  (re-run the test, fetch the PR URL, stat the file) and call
  `task_complete` with a summary.

### Step 3 — Escalate only when truly blocked

If you hit a question only the user can answer (credentials, scope,
ambiguous spec), use `ask_user`. Do not escalate for things you could
decide yourself — autopilot's whole point is autonomous decision-making.

## Auto-disable conditions

You stop autonomous work when any of these hold:

- The Definition of Done is met **and verified** → `task_complete`
- You are genuinely blocked on missing info → `ask_user`
- The user runs `/amplihack:unlock` (sets explicit "stop" boundary)

## Examples

**User says**: "fix the auth bug and make sure tests pass"

→ You write at the top of your reply:
```
Goal: Fix the authentication bug.
Definition of Done: Auth tests pass; no regressions in suite.
```
→ Then you start: read repro, find bug, fix, run auth tests, run full suite.

**User says**: "implement OAuth2 login and create a PR"

→ Goal: Implement OAuth2 login flow.
   Definition of Done: OAuth2 endpoint works; tests cover happy + error paths; PR open on GitHub.
→ Implement, test, commit, push, `gh pr create`, return PR URL.

**User says**: "keep going"

→ Goal: Continue current task until pending items resolved.
   Definition of Done: All open todos in this session marked done; tests green.
→ Resume from `plan.md` / SQL todos.

## What changed from v3

- Removed the `python .claude/tools/amplihack/lock_tool.py lock` shell-out.
  That tool only existed for Claude Code's hook subsystem and wrote
  `~/.amplihack/.claude/runtime/locks/.lock_active`, which Copilot CLI
  and other runtimes never read.
- The contract is now purely behavioral: commit to the goal, persist
  until done, escalate only on genuine blockers. The runtime's
  built-in autopilot enforces this without a sidecar process.
