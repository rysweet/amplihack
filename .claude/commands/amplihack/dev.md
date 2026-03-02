---
name: dev
version: 2.1.0
description: |
  Primary entry point for all development and investigation work.
  Classifies task, decomposes into workstreams if parallel-capable,
  and launches execution via recipe runner. The default orchestrator.
triggers:
  - "implement"
  - "build"
  - "create"
  - "fix"
  - "refactor"
  - "investigate"
  - "develop"
  - "make"
  - "add feature"
invokes:
  - type: recipe
    name: smart-orchestrator
  - type: recipe
    name: default-workflow
  - type: recipe
    name: investigation-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/smart-orchestrator.yaml
examples:
  - "/dev add user authentication"
  - "/dev build a webui and an API for user management"
  - "/dev fix the login timeout bug"
  - "/dev investigate how the caching layer works"
  - "/dev implement OAuth and add structured logging"
---

## EXECUTION INSTRUCTIONS (DO THIS IMMEDIATELY)

**YOUR VERY FIRST ACTION** after reading this command MUST be a Bash tool call
that executes the recipe runner. Do NOT classify, do NOT read files, do NOT
create task lists first. Execute this code NOW:

> Note: Replace `TASK_DESCRIPTION` below with the actual user text passed to
> this command. Do not pass the literal string `"{TASK_DESCRIPTION}"`.

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.recipes.adapters import ClaudeSDKAdapter

adapter = ClaudeSDKAdapter()
result = run_recipe_by_name(
    "smart-orchestrator",
    adapter=adapter,
    user_context={
        "task_description": "<the actual task from the user>",
        "repo_path": ".",
    }
)
```

**There are no fallback paths.** If `run_recipe_by_name` fails with an
ImportError, report the error to the user and stop. Do NOT silently fall back to
direct execution, skill invocation, or manual classification.

## Task Description

```
{TASK_DESCRIPTION}
```

---

## Reference (for humans, not execution)

### What This Command Does

The `/dev` command is the primary entry point for all development work in
amplihack. It classifies your task, detects parallel workstreams, and executes
via recipe runner.

### Flow

```
/dev <request>
      |
      v
[smart-orchestrator recipe]
      |
      +- Q&A -----------------------------> analyzer agent (direct answer)
      |
      +- Ops -----------------------------> builder agent (executes operation)
      |
      +- 1 workstream --------------------> default-workflow recipe
      |
      +- N workstreams (parallel) ---------> multitask orchestrator
      |         [if BLOCKED by depth limit: falls back to]
      +-----------------------------------> single-session execution
                                                    |
                                                    v
                                           [Reflect on goal]
```

### Glossary

**Workstream**: An isolated parallel execution unit. When your request contains
multiple independent components (e.g., "build an API and a webui"), the
orchestrator splits them into separate workstreams that run concurrently in
`/tmp/amplihack-workstreams/`.

**Recipe**: A YAML workflow definition that specifies the exact sequence of steps
Claude follows. The `smart-orchestrator` recipe is what runs when you invoke
`/dev`.

**Recipe Runner**: The Python execution engine
(`amplihack.recipes.run_recipe_by_name`) that executes recipes with
code-enforced step ordering. It is the REQUIRED execution method for all
Development and Investigation tasks. There is no prompt-based alternative.

**Session Tree**: A lightweight state tracker in
`/tmp/amplihack-session-trees/` that prevents infinite recursive orchestration
by tracking active sessions and enforcing depth and capacity limits.

**Goal-Seeking Loop**: The up-to-3-round retry mechanism. After each execution
round, a reviewer agent evaluates whether the goal was achieved. If PARTIAL or
NOT_ACHIEVED, another round runs automatically (up to 3 total). After all rounds
complete, a `reflect-final` step runs for all completed development and
investigation tasks to produce the definitive `GOAL_STATUS` assessment used in
the summary.

**Recursion Guard Fallback**: When the session depth limit is reached and
parallel workstream spawning is blocked, the orchestrator automatically falls
back to single-session execution (via `execute-single-fallback-blocked`). The
task runs as a single Claude session without sub-workstream spawning.

### Auto-Routing (Without Typing /dev)

The `UserPromptSubmit` hook automatically injects intent-routing guidance on
every message (except slash commands and short conversational turns). Claude
classifies your intent and invokes `dev-orchestrator` when appropriate.

- **Disable**: `/amplihack:no-auto-dev` (toggles instantly, no restart needed)
- **Re-enable**: `/amplihack:auto-dev`
- **Override for one prompt**: Include "just answer" or "without workflow"
- **Legacy env var**: `export AMPLIHACK_AUTO_DEV=false` (still works)

### What to Expect During Execution

When you run `/dev fix the login bug`, here is what you will see:

1. **Classification** (~1 minute): The orchestrator analyzes your request and
   outputs a structured plan. You will see agent reasoning and a JSON
   decomposition.

2. **Execution** (~5-15min for a typical bug fix, longer for complex features):
   The builder agent does the actual work -- you will see detailed
   implementation output streaming in real time.

3. **Reflection** (~1 minute): A reviewer evaluates whether the goal was
   achieved. If not, another round runs automatically (up to 3 total). You will
   see `GOAL_STATUS: PARTIAL` or `GOAL_STATUS: ACHIEVED` in the output.

4. **Summary**: When complete, look for
   `# Dev Orchestrator -- Execution Complete` at the bottom. This contains the
   structured summary including PR links and goal status.
