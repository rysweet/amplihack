# Fleet Co-Pilot — Autonomous Lock Mode

The fleet co-pilot merges lock mode with SessionCopilot reasoning into a single
feature. When you tell Claude to work autonomously, it formulates a goal,
enables lock mode, and uses LLM reasoning to stay on track until the goal is
achieved.

## Quick Start

Tell Claude what you want done using natural language:

```
/amplihack:lock fix the auth bug, make sure all tests pass, then create a PR
```

Or use the fleet-copilot skill:

```
/fleet-copilot implement OAuth2 login with PKCE flow and add integration tests
```

Claude will:

1. Formulate a goal and definition of done from your words
2. Write the goal to `.claude/runtime/locks/.lock_goal`
3. Enable lock mode
4. Start working immediately

## CLI Commands

### fleet setup

Check prerequisites and install azlin if missing. Run on a new machine:

```
fleet setup
```

### fleet copilot-status

Show whether the co-pilot is active, the current goal, and lock state:

```
fleet copilot-status
```

### fleet copilot-log

View the co-pilot's decision history (what it decided and why):

```
fleet copilot-log
fleet copilot-log --tail 5     # last 5 decisions
```

## How It Works

Two hooks work together:

### LockModeHook (provider:request)

Injects the goal as a system directive on every LLM call so the agent always
has context about what it's working toward. Passive — no reasoning here.

### Stop Hook (on stop)

When the agent tries to stop, the Stop hook:

1. Reads the goal file
2. Calls `SessionCopilot.suggest()` which:
   - Reads the full session transcript
   - Builds rich context (first user message + summarized middle + recent entries)
   - Reasons about progress toward the goal
3. Based on the suggestion:
   - **send_input** (confidence >= 0.6): Blocks stop with specific next-step guidance
   - **wait**: Blocks stop with a generic "keep working toward goal" prompt
   - **mark_complete**: Auto-disables lock, tells agent to summarize completed work
   - **escalate**: Auto-disables lock, tells agent to ask the user for help

Every decision is logged to `.claude/runtime/copilot-decisions/decisions.jsonl`
for debugging and auditing. View logs with `fleet copilot-log` or in the TUI
Copilot Log tab.

## Smart Transcript Reading

The co-pilot uses `build_rich_context()` to give the LLM the best possible
context for reasoning:

1. **First user message**: Always included — this is the original intent
2. **Summarized middle**: For long sessions, the middle section is summarized
   (tool counts, file list, error summary) rather than included verbatim
3. **Recent entries**: The last 500 entries are included in full — no truncation

This means even in a 10-hour session with thousands of entries, the co-pilot
knows what you originally asked for, what happened along the way, and exactly
what's happening right now.

## Auto-Disable

Lock mode automatically disables when:

- **Goal achieved**: SessionCopilot returns `mark_complete`
- **Needs human help**: SessionCopilot returns `escalate`
- **Manual unlock**: User runs `/amplihack:unlock`

When auto-disabled, the lock and goal files are removed and the agent is told
to either summarize completed work or explain why it needs help.

## Files

| File                                                             | Purpose                                  |
| ---------------------------------------------------------------- | ---------------------------------------- |
| `.claude/runtime/locks/.lock_active`                             | Lock state (exists = locked)             |
| `.claude/runtime/locks/.lock_goal`                               | Goal + definition of done                |
| `.claude/runtime/copilot-decisions/decisions.jsonl`              | Copilot decision log                     |
| `.claude/tools/amplihack/lock_tool.py`                           | CLI: lock/unlock/check                   |
| `amplifier-bundle/tools/amplihack/hooks/stop.py`                 | Stop hook (delegates to copilot handler) |
| `amplifier-bundle/tools/amplihack/hooks/copilot_stop_handler.py` | Copilot reasoning + decision logging     |
| `amplifier-bundle/modules/hook-lock-mode/`                       | Provider:request hook for goal injection |
| `src/amplihack/fleet/fleet_copilot.py`                           | SessionCopilot engine                    |
| `src/amplihack/fleet/prompts/copilot_system.prompt`              | LLM system prompt                        |
| `src/amplihack/fleet/prompts/lock_mode_directive.prompt`         | Goal injection template                  |
| `src/amplihack/fleet/_constants.py`                              | All configurable thresholds              |

## Examples

### Simple task

```
/amplihack:lock fix the failing test in test_auth.py
```

Goal formulated: "Fix the failing test in test_auth.py. Definition of Done: test_auth.py passes, no regressions."

### Multi-step task

```
/amplihack:lock implement user profile page with avatar upload, write tests, create PR
```

Goal formulated: "Implement user profile page with avatar upload. Definition of Done: profile page renders, avatar upload works, tests cover happy path and errors, PR created on GitHub."

### Keep going

```
/amplihack:lock keep going until all the TODOs are done
```

Goal formulated: "Complete all pending TODO items. Definition of Done: no remaining TODO items in task list, tests pass."
