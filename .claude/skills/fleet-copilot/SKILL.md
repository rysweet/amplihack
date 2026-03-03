---
name: fleet-copilot
version: 1.0.0
description: >-
  Smart autonomous guidance — enables lock mode with a goal so the session
  co-pilot uses LLM reasoning to keep the agent moving toward the objective.
triggers:
  - "fleet copilot"
  - "smart lock"
  - "autonomous goal"
  - "work toward goal"
  - "copilot mode"
invocable_by: user
---

# Fleet Co-Pilot Skill

Convenience wrapper that enables lock mode with a goal, activating the smart
session co-pilot. This merges the old lock mode ("keep going") with the fleet
co-pilot's LLM reasoning into a single feature.

## What It Does

When invoked with a goal, the skill:

1. Enables lock mode via `lock_tool.py lock --goal "..."`
2. The LockModeHook detects the goal file and switches to smart mode
3. On each provider:request, the hook uses `SessionCopilot.suggest()` to:
   - Read the session transcript
   - Reason about what to do next
   - Inject specific, contextual guidance (not generic "continue")
4. Auto-disables when the goal is achieved or escalation is needed

## Usage

```
/fleet-copilot Fix the auth bug, write tests, create PR
/fleet-copilot Implement OAuth2 with PKCE flow and add integration tests
```

## Instructions

When this skill is activated:

1. Extract the goal from the user's message (everything after the command name)
2. Run the lock tool with the goal:

```bash
python .claude/tools/amplihack/lock_tool.py lock --goal "USER_GOAL_HERE"
```

3. Confirm to the user that smart co-pilot mode is active with their goal.

The hook will now use SessionCopilot reasoning on every turn to guide the agent
toward the stated goal. The agent should then begin working on the goal
immediately.

## Disabling

The co-pilot auto-disables when:
- Goal is achieved (mark_complete action)
- Co-pilot needs human help (escalate action)
- User runs `/amplihack:unlock`

## Relationship to Lock Mode

This skill IS lock mode with a goal. The `--goal` flag is the dial between:
- **No goal** = dumb mode (bare "continue")
- **With goal** = smart co-pilot (LLM-reasoned guidance)
