---
name: unlock
version: 2.0.0
description: Release the autonomous-goal commitment and stop on the next natural break
triggers:
  - "Disable continuous work mode"
  - "Stop working autonomously"
  - "Exit lock mode"
  - "You can stop now"
---

# Unlock: Release Autonomous Goal Commitment

Release the commitment made by `/amplihack:lock`. Stop on the next
natural break point and wait for the user.

## Runtime support

There is **no Python tool to invoke**. The previous v1 of this command
ran `python .claude/tools/amplihack/lock_tool.py unlock`, which only
deleted a marker file at `~/.amplihack/.claude/runtime/locks/.lock_active`
that Copilot CLI and most runtimes never read. The contract is now
purely behavioral.

## Instructions

When the user invokes this command:

1. Acknowledge briefly: "Unlocked — stopping after current step."
2. Finish whatever in-flight tool call you've already started (don't
   abandon it mid-step and leave the workspace inconsistent).
3. Provide a short summary of where you ended up:
   - What was completed
   - What remains pending
   - Any open todos in `plan.md` / SQL `todos` that the user should
     know about
4. Call `task_complete` with that summary, OR end your turn cleanly
   without further tool calls.

After unlock, your next response should wait for explicit user
direction before resuming work, even if your prior commitment had
defined more pending criteria.
