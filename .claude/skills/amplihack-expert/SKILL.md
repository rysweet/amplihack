---
name: amplihack-expert
description: Comprehensive knowledge of amplihack framework architecture, patterns, and usage
version: 2.0.0
author: amplihack team
tags: [amplihack, framework, architecture, workflows, agents, commands]

triggers:
  keywords:
    - amplihack
    - dev-orchestrator
    - smart-orchestrator
    - /dev
    - workstream
    - recipe runner
    - workflow
    - DEFAULT_WORKFLOW
    - /.claude/
    - agent system
    - specialized agent
    - command system
    - hook system
    - continuous work
    - skill system
    - extensibility
  patterns:
    - "How does amplihack.*work"
    - "What is.*amplihack"
    - "amplihack.*(architecture|structure|design)"
    - "How do I.*amplihack"
    - "What.*agents.*available"
    - "How.*orchestrat"
    - "When.*use.*dev|When.*use.*/dev"
  file_paths:
    - "~/.amplihack/"
    - ".claude/agents/"
    - ".claude/commands/"
    - ".claude/workflow/"
    - ".claude/skills/"

token_budget:
  skill_md: 800
  reference_md: 1200
  examples_md: 600
  total: 2600

disclosure_strategy:
  quick_answer: "SKILL.md only"
  architecture_question: "SKILL.md + reference.md"
  how_to_question: "SKILL.md + examples.md"
  comprehensive: "All three files"

references:
  - "reference.md: Comprehensive architecture details"
  - "examples.md: Real-world usage scenarios"
  - "@~/.amplihack/.claude/context/PHILOSOPHY.md: Core principles"
  - "@~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md: Main workflow"
---

# amplihack Expert Knowledge

## What is amplihack?

Engineering system for coding CLIs (Claude, Copilot, Amplifier): 5 mechanisms, 23-step workflow, 30+ agents, 80+ skills. Core entry point: `/dev <task>` — unified task orchestrator with auto-classification, parallel workstream detection, and goal-seeking execution loop.

## Quick Reference

### Top Commands

| Command           | Purpose        | Use When              |
| ----------------- | -------------- | --------------------- |
| /dev              | Orchestrate    | Any non-trivial task  |
| /analyze          | Review         | Check compliance      |
| /fix              | Fix errors     | Common error patterns |
| /amplihack:ddd:\* | Doc-driven dev | 10+ file features     |
| /multitask        | Parallel tasks | Sprint/batch work     |

### Top Agents

| Agent     | Role    |
| --------- | ------- |
| architect | Design  |
| builder   | Code    |
| reviewer  | Quality |
| tester    | Tests   |

### Workflows

| Name             | Steps |
| ---------------- | ----- |
| DEFAULT_WORKFLOW | 23    |
| INVESTIGATION    | 6     |
| FIX              | 3     |

## Navigation Guide

**Quick**: SKILL.md | **Architecture**: reference.md | **How-To**: examples.md | **Deep**: all

## Core Concepts

**5 Mechanisms:** Workflow (process), Command (entry), Skill (auto), Agent (delegate), Hook (runtime)

**Composition:** Commands → Workflows → Agents → Skills

**Execution:** `/dev` orchestrates — classifies task, detects parallel workstreams, executes via smart-orchestrator recipe, goal-seeking loop (3 rounds max)

**Entry point:** `/dev <task>` → dev-orchestrator skill → smart-orchestrator recipe → default-workflow recipe

## dev-orchestrator Architecture

**Entry point**: `/dev <task>` or any non-trivial prompt

**Routing:**

- Q&A → `amplihack:core:analyzer` responds directly
- Operations → bash (simple) or `amplihack:core:builder` (complex)
- Development/Investigation → smart-orchestrator recipe (full orchestration)

**Execution flow:**

1. Classify task (architect agent → JSON decomposition)
2. Detect workstreams (1 = single session, 2-5 = parallel via multitask)
3. Register session in tree (depth/capacity enforcement)
4. Execute rounds (up to 3, goal-seeking reflection loop)
5. Summarize results with PR links and GOAL_STATUS

**Session tree**: Prevents infinite recursion

- `AMPLIHACK_MAX_DEPTH=3` (default) — increase to 5 for deep orchestration
- `AMPLIHACK_MAX_SESSIONS=10` (default) — max concurrent sessions per tree

**Status signals:**

- `GOAL_STATUS: ACHIEVED` — all criteria met
- `GOAL_STATUS: PARTIAL -- [gaps]` — another round will run
- `GOAL_STATUS: NOT_ACHIEVED -- [reason]` — final failure status

## Related Docs

- reference.md: Architecture (5 mechanisms, 5 layers, hooks)
- examples.md: Scenarios (5+ real examples)
- @~/.amplihack/.claude/context/PHILOSOPHY.md: Core principles
- @~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md: 23 steps
- @~/.amplihack/.claude/agents/amplihack/: All agents
- @~/.amplihack/.claude/commands/amplihack/: All commands
- @~/.amplihack/.claude/tools/amplihack/hooks/: Hook system
- amplifier-bundle/recipes/smart-orchestrator.yaml: Core orchestration recipe
- amplifier-bundle/tools/session_tree.py: Recursion guard (depth limits)
- amplifier-bundle/tools/orch_helper.py: JSON extraction helper
