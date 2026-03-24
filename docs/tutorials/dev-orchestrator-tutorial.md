# Getting Started with /dev — The amplihack Dev Orchestrator

**Time**: ~20 minutes | **Level**: Beginner to Intermediate

This tutorial walks you through the primary entry point for amplihack development
work: the `/dev` command and its underlying smart-orchestrator. By the end you
will understand how to use it effectively for single tasks, parallel workstreams,
and how to interpret what you see during execution.

---

## Contents

- [Prerequisites](#prerequisites)
- [Part 1: Your First /dev Command](#part-1-your-first-dev-command-5-minutes)
- [Part 2: Parallel Workstreams](#part-2-parallel-workstreams-5-minutes)
- [Part 3: Investigation + Implementation](#part-3-investigation--implementation-5-minutes)
- [Part 4: The Goal-Seeking Loop](#part-4-the-goal-seeking-loop-5-minutes)
- [Part 5: Interpreting Output](#part-5-interpreting-output-2-minutes)
- [Common Patterns](#common-patterns)
- [Auto-Routing: How It Works](#auto-routing-how-it-works)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Prerequisites

- amplihack installed and running in a Claude Code session
- A git repository to work in (any project works)

---

## Part 1: Your First /dev Command (5 minutes)

### What /dev does

`/dev` is the unified entry point for all development and investigation work. It:

1. **Classifies** your request (Q&A, Operations, Investigation, or Development)
2. **Decomposes** it into workstreams if it contains independent parallel components (hybrid "investigate then build" requests become multiple workstreams)
3. **Executes** via the recipe runner with a goal-seeking loop (up to 3 rounds)
4. **Reflects** on whether the goal was achieved

### Try it

Claude Code opens an interactive chat prompt in your terminal (not a bash shell). Type slash commands directly into that prompt. At the `>` or input line, type:

```
/dev fix the login timeout bug
```

### What you will see

```
[dev-orchestrator] Classified as: Development | Workstreams: 1 — starting execution...
```

The builder agent starts streaming output — you will see it reading files,
writing code, and creating a PR. This takes 1–5 minutes for a typical bug fix.

After execution completes, look for the final summary at the bottom:

```
# Dev Orchestrator -- Execution Complete

**Task**: fix the login timeout bug
**Type**: Development
**Workstreams**: 1

## Summary

PR created: https://github.com/your-org/your-repo/pull/42
Goal status: ACHIEVED — JWT expiry logic corrected, tests passing.
```

**Key signals to watch:**

| Signal                                  | Meaning                             |
| --------------------------------------- | ----------------------------------- |
| `GOAL_STATUS: ACHIEVED`                 | Done — review the PR                |
| `GOAL_STATUS: PARTIAL -- [description]` | Another round running automatically |
| `GOAL_STATUS: NOT_ACHIEVED -- [reason]` | Failed — check the error above      |

---

## Part 2: Parallel Workstreams (5 minutes)

When your task has clearly independent components, `/dev` splits them and runs
them simultaneously.

### Try it

```
/dev build a REST API and a React webui for user management
```

### What you will see

```
[dev-orchestrator] Classified as: Development | Workstreams: 2 — starting execution...
Launching parallel workstreams (tree: abc12345, depth: 0):
[{"issue": "TBD", "branch": "feat/orch-1-rest-api", ...},
 {"issue": "TBD", "branch": "feat/orch-2-react-webui", ...}]
---
[TBD] Launched PID 12345 (recipe mode)
[TBD] Launched PID 12346 (recipe mode)
2 workstreams launched in parallel (recipe mode)
```

Both workstreams run in isolated `/tmp` clones. When they complete, you get two
PRs — one for the API, one for the webui.

### When does /dev use parallel workstreams?

The architect agent decides. These decompose into parallel workstreams:

- "build X **and** Y" — two independent features
- "add auth **and** add logging" — independent concerns
- "investigate X **then** implement Y" — two sequential phases

These stay as a single workstream:

- "fix the login timeout bug" — one cohesive task
- "add pagination to the user API" — one feature

### Force single workstream

If you want to prevent parallel execution:

```bash
export AMPLIHACK_MAX_DEPTH=0
/dev build a REST API and a React webui
# Falls back to single-session execution
```

---

## Part 3: Investigation + Implementation (5 minutes)

For tasks requiring understanding before building, use the hybrid pattern:

```
/dev investigate how the payment service handles retries, then add exponential backoff
```

### What typically happens

> The architect agent decides workstream decomposition. "investigate X then implement Y"
> usually produces two workstreams, but may produce one for simpler cases.

1. **Workstream 1** (investigation-workflow): Explores the payment service code,
   maps the retry logic, produces findings.
2. **Workstream 2** (default-workflow): Uses the investigation findings as context
   for implementing exponential backoff.

This is the recommended pattern for any non-trivial change to unfamiliar code.
Running investigation first prevents the builder from making wrong assumptions
about existing structure.

---

## Part 4: The Goal-Seeking Loop (5 minutes)

If the first execution does not fully achieve the goal, `/dev` automatically
tries again — up to 3 rounds.

### How it works

After each execution round, a reviewer agent evaluates:

> "Was the goal achieved? Were all success criteria met?"

If the answer is `PARTIAL` or `NOT_ACHIEVED`, another round starts automatically:

```
Round 1: Builder implements fix
Round 1 reflection: GOAL_STATUS: PARTIAL -- tests not updated
Round 2: Builder adds missing tests
Round 2 reflection: GOAL_STATUS: ACHIEVED
```

You will see each round's output stream by. The final summary reflects the
consolidated result after all rounds complete.

### Manual override

If you want single-round execution (faster, less thorough), simply re-run `/dev`
with more specific instructions if the first result is insufficient. Adding
explicit success criteria in your prompt helps the goal-seeking loop converge
faster:

```
/dev fix the login timeout bug — ensure existing tests pass and add a regression test
```

---

## Part 5: Interpreting Output (2 minutes)

### During execution

| You see                                             | Meaning                                                               |
| --------------------------------------------------- | --------------------------------------------------------------------- |
| `[dev-orchestrator] Classified as: ...`             | Classification complete, execution starting                           |
| Agent output streaming                              | The builder is working                                                |
| `GOAL_STATUS: PARTIAL -- [reason]`                  | Round N incomplete, round N+1 starting                                |
| `NOTE: Session registration failed`                 | Tree tracking inactive (non-blocking)                                 |
| `WARNING: Could not parse decomposition JSON`       | Architect output was ambiguous; defaulted to Development/1-workstream |
| `NOTE: Parallel workstream spawning is unavailable` | Depth/capacity limit hit; running as single session                   |

### At completion

```
# Dev Orchestrator -- Execution Complete

**Task**: [your task]
**Type**: [Q&A | Development | Investigation | Operations]
**Workstreams**: [number]

## Summary

[PR links, goal status, what was accomplished, any remaining work]
```

If you see an empty Summary section for a Q&A or Operations task, that is
expected — those task types respond directly and do not generate summaries.

---

## Common Patterns

```bash
# Bug fix
/dev fix the 500 error on the /users endpoint

# New feature
/dev add OAuth login with Google

# Investigation only
/dev investigate why database queries are slow on the dashboard

# Parallel features
/dev add rate limiting and add request logging to the API

# Investigation then implement
/dev understand the existing test structure then add tests for the auth module

# Code review
/dev review PR #42 for security issues

# Simple Q&A (no workflow overhead)
/dev what does the circuit breaker pattern do?
```

---

## Auto-Routing: How It Works

The `UserPromptSubmit` hook injects a routing prompt on every message (except
slash commands like `/dev` or `/analyze`). This routing prompt uses **parallel
signal evaluation** — it detects multiple signals in your message simultaneously
and resolves them with priority rules.

### The 4-Layer Classification Pipeline

Your message passes through 4 classification layers:

1. **`routing_prompt.txt`** — Injected every turn by `dev_intent_router.py`. Detects 5 parallel signals (UNDERSTAND, IMPLEMENT, FILE_EDIT, SHELL_ONLY, QUESTION) and resolves with priority rules. This is the primary classifier.
2. **`CLAUDE.md`** — Classification table loaded at session start. Provides keyword guidance and the mandatory code-file-edit rule.
3. **`workflow_classification_reminder.py`** — Fires at topic boundaries (new conversations, direction changes). Reinforces classification.
4. **`dev-orchestrator/SKILL.md`** — When the skill activates, guides decomposition into workstreams.

### Signal Detection and Resolution

The routing prompt evaluates these signals in parallel:

| Signal     | Keywords                                           | Example             |
| ---------- | -------------------------------------------------- | ------------------- |
| UNDERSTAND | explain, how does, why, analyze, research, explore | "why is CI failing" |
| IMPLEMENT  | build, fix, add, create, refactor, update, write   | "fix the login bug" |
| FILE_EDIT  | any .py/.yaml/.md/.ts/.json will change            | "update the README" |
| SHELL_ONLY | run tests, git status, check logs                  | "git status"        |
| QUESTION   | what is, how do I, explain, compare                | "what is OAuth?"    |

Then resolves by priority:

| Signals detected                | Classification  | Action                                  |
| ------------------------------- | --------------- | --------------------------------------- |
| UNDERSTAND + IMPLEMENT          | **HYBRID**      | dev-orchestrator (parallel workstreams) |
| SHELL_ONLY + IMPLEMENT          | **HYBRID**      | dev-orchestrator                        |
| FILE_EDIT or IMPLEMENT alone    | **DEV**         | dev-orchestrator                        |
| UNDERSTAND alone                | **INVESTIGATE** | dev-orchestrator                        |
| SHELL_ONLY alone                | **OPS**         | Execute directly                        |
| QUESTION alone                  | **Q&A**         | Answer directly                         |
| "just answer" / "skip workflow" | **SKIP**        | Bypass                                  |

The hook itself does NOT classify — it injects the same routing guidance for
every message. Claude's natural language understanding handles the rest.

**Disable auto-routing:**

```
/amplihack:no-auto-dev           # toggles instantly during a session
```

Or via environment variable:

```bash
export AMPLIHACK_AUTO_DEV=false   # for one session
echo 'export AMPLIHACK_AUTO_DEV=false' >> ~/.bashrc  # permanent
```

**Re-enable:**

```
/amplihack:auto-dev
```

**Override for a single prompt:** Include "just answer" or "without workflow"
anywhere in your message. Claude reads these phrases in the routing prompt's
SKIP category and responds directly.

---

## Execution Modes

The dev-orchestrator supports two execution modes for the recipe runner.

### Default: Direct Execution

Recipes run via plain `subprocess.Popen` — no tmux required. This works
everywhere: local shells, containers, CI, Windows native, and restricted
environments.

```
[dev-orchestrator] starting recipe runner (direct mode)...
```

### Optional: Durable Execution via tmux

For long-running recipes (typically >15 minutes) or environments that kill
background processes on disconnection (SSH sessions without session managers),
use the tmux-based durable execution mode.

```bash
# Enable durable mode for the current session
export AMPLIHACK_DURABLE_EXEC=1
/dev your long-running task
```

In durable mode, the Python payload is written to a temporary script file
before launching tmux — this avoids nested quoting failures that occurred in
older versions when task descriptions contained quotes:

```bash
tmux new-session -d -s recipe-runner "python3 $SCRIPT_FILE 2>&1 | tee $LOG_FILE"
```

If the tmux session appears to start but produces no output, ensure you are
using amplihack v0.9.1 or later which includes the temp-script fix (PR #3216).

### Agent Binary Selection

By default, amplihack uses `claude` as the agent binary. To use a different
agent, set `AMPLIHACK_AGENT_BINARY`:

```bash
export AMPLIHACK_AGENT_BINARY=claude   # default
```

This variable is preserved across nested agent launches — subagents spawned by
the recipe runner use the same binary as the parent.

---

## Troubleshooting

**"BLOCKED: max_depth exceeded"**

You are hitting the recursion depth limit. Increase it for deeper orchestration:

```bash
export AMPLIHACK_MAX_DEPTH=5
```

**"WARNING: Could not parse decomposition JSON"**

The architect agent's response was not parseable. The task will still run as a
Development/1-workstream default. Re-run for better results or simplify the
task description.

**"orch_helper.py not found"**
The recipe cannot locate its helper module. This happens when:

- **Cloned-repo users**: Not running from the repo root. Fix:
  ```bash
  cd /path/to/amplihack
  /dev your task
  # OR set AMPLIHACK_HOME:
  export AMPLIHACK_HOME=/path/to/your/amplihack
  ```
- **`uvx` users**: This indicates a packaging issue. Try reinstalling:
  ```bash
  uv tool install --reinstall git+https://github.com/rysweet/amplihack
  ```

**Execution appears stuck with no output**

The agent is working — there are no progress bars between major steps. A complex
task can take 10–15 minutes. Output resumes when the current agent call
completes.

**"Dev Orchestrator started when I didn't type /dev"**
The auto-routing hook injected a routing prompt, and Claude classified your
message as a development task.

- To disable for this session: `export AMPLIHACK_AUTO_DEV=false`
- To override for one prompt: prefix with "just answer", "without workflow", or "skip orchestration"
- To check whether the hook would inject the routing prompt:
  ```python
  import sys
  sys.path.insert(0, 'amplifier-bundle/tools/amplihack/hooks')
  from dev_intent_router import should_auto_route
  ok, ctx = should_auto_route("your prompt here")
  print(f"would_inject={ok}")
  print(f"injection_length={len(ctx)} chars")
  ```

---

## Next Steps

- **[DEFAULT_WORKFLOW](../../.claude/workflow/DEFAULT_WORKFLOW.md)**: The
  23-step process the builder agent follows for each workstream
- **[Amplihack Tutorial](amplihack-tutorial.md)**: Full overview of all 8
  workflow types and when to use each
- **[multitask skill](../../.claude/skills/multitask/SKILL.md)**: Direct
  control over parallel workstreams with JSON configuration
- **[Command Selection Guide](../commands/COMMAND_SELECTION_GUIDE.md)**: When
  to use `/dev` vs `/dev investigate` vs other commands
