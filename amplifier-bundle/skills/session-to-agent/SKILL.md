---
name: session-to-agent
version: 1.0.0
description: >-
  Converts interactive Claude Code or GitHub Copilot session goals and processes
  into a reusable goal-seeking agent with memory. Extracts goals, constraints,
  and approaches from session transcripts and generates agent prompts via the
  amplihack goal_agent_generator CLI.
auto-detection:
  triggers:
    - "session to agent"
    - "turn session into agent"
    - "convert session"
    - "create agent from session"
    - "extract agent from conversation"
    - "reusable agent from session"
    - "productize this workflow"
invokes:
  - tools: [Read, Write, Glob, Grep, Bash]
  - commands: [amplihack new]
  - skills: [goal-seeking-agent-pattern, knowledge-extractor]
allowed-tools: ["Read", "Write", "Glob", "Grep", "Bash"]
target-agents: ["architect", "builder"]
priority: medium
complexity: medium
maturity: production
---

# Session-to-Agent Skill

Convert an interactive coding session into a reusable goal-seeking agent with
memory. The skill reads session transcripts, extracts goals and patterns, and
generates a complete agent via `amplihack new`.

## Quick Start

### Step 1: Invoke the skill

```
User: /session-to-agent
```

Or describe what you want:

```
User: Turn this session into a reusable agent
```

### Step 2: The skill extracts from the current session

It analyzes the session transcript to identify:

- **Primary goal** and sub-goals
- **Constraints** (technical, operational, time)
- **Tools and commands** used
- **Patterns and strategies** observed
- **Domain knowledge** gained during the session

### Step 3: A goal-seeking agent is generated

The skill writes a `prompt.md` file and runs:

```bash
amplihack new --file prompt.md --sdk copilot --enable-memory
```

The generated agent can be re-run autonomously to repeat or extend the
session's workflow.

## What It Extracts

| Category             | Examples                                             |
| -------------------- | ---------------------------------------------------- |
| **Primary Goal**     | "Implement JWT authentication for the REST API"      |
| **Sub-Goals**        | Token generation, middleware, refresh flow, tests    |
| **Constraints**      | Must use RS256, tokens expire in 1h, no external IdP |
| **Tools Used**       | pytest, ruff, git, curl, Bash, Read, Edit            |
| **Patterns**         | Outside-in TDD, error-first validation, retry logic  |
| **Domain Knowledge** | JWT spec details, library quirks, API contract rules |
| **Success Criteria** | All tests pass, CI green, security review approved   |

## Customizing the Generated Agent

After generation, you can refine the agent by editing:

- `prompt.md` -- the goal description and constraints
- `plan.yaml` -- the execution phases and dependencies
- `skills.yaml` -- the required skills and tool mappings
- `metadata.json` -- SDK, memory, and multi-agent settings

Re-run the generator after edits:

```bash
amplihack new --file prompt.md --sdk copilot --enable-memory
```

## Memory Export (Optional)

When `--enable-memory` is used, the skill can optionally export the current
session's Kuzu memory database as the agent's initial knowledge base. This
seeds the new agent with facts, discoveries, and context from the session
that created it.

```bash
# Export is offered interactively after agent generation
# Or specify explicitly:
amplihack new --file prompt.md --enable-memory --sdk copilot
```

## When to Use This Skill

- After completing a multi-step workflow you want to repeat
- When a session reveals a reusable process worth automating
- To hand off a workflow to a colleague as a runnable agent
- To create a CI/CD or SRE automation agent from manual steps
- When session knowledge should persist as an executable artifact

## When NOT to Use This Skill

- For trivial single-command tasks (use a script instead)
- When the session was exploratory with no clear repeatable goal
- When the workflow is already captured as a recipe or agent

## Supporting Files

| Need                                    | File                             |
| --------------------------------------- | -------------------------------- |
| Full extraction algorithm and templates | [reference.md](reference.md)     |
| Worked examples with real sessions      | [examples.md](examples.md)       |
| Goal-seeking agent design guidance      | goal-seeking-agent-pattern skill |
| Knowledge extraction from sessions      | knowledge-extractor skill        |
