---
name: amplihack-expert
description: Comprehensive knowledge of amplihack framework architecture, patterns, and usage
version: 1.0.0
author: amplihack team
tags: [amplihack, framework, architecture, workflows, agents, commands]

triggers:
  keywords:
    - amplihack
    - ultrathink
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
    - "When.*use.*ultrathink"
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

Multi-CLI agentic framework (Claude Code, Copilot CLI, Amplifier, Rustyclawd): 4 mechanisms, 23-step workflow, 30+ agents, 25 commands, 80+ skills.

## Quick Reference

### Top Commands

| Command              | Purpose              | Use When         |
| -------------------- | -------------------- | ---------------- |
| /ultrathink          | Orchestrate workflow | Non-trivial dev  |
| /analyze             | Code review          | Check compliance |
| /fix                 | Quick fixes          | Common errors    |
| /amplihack:ddd:\*    | Doc-driven dev       | 10+ files        |
| /amplihack:n-version | N-version            | Critical code    |

### Top Agents

| Agent     | Role    | Trigger       |
| --------- | ------- | ------------- |
| architect | Design  | Decomposition |
| builder   | Code    | Generation    |
| reviewer  | Quality | Validation    |
| tester    | Tests   | Generation    |
| fix-agent | Fixes   | Errors        |

### Workflows

| Name                   | Steps   | Purpose   |
| ---------------------- | ------- | --------- |
| DEFAULT_WORKFLOW       | 23      | Main dev  |
| INVESTIGATION_WORKFLOW | 6       | Deep dive |
| FIX_WORKFLOW           | 3 modes | Rapid fix |

## Navigation Guide

**Quick**: SKILL.md | **Architecture**: reference.md | **How-To**: examples.md | **Deep**: all

## Core Concepts

**4 Mechanisms:** Workflow (process), Command (entry), Skill (auto), Agent (delegate)

**Composition:** Commands → Workflows → Agents → Skills

**Execution:** Parallel by default, UltraThink orchestrates

## Related Docs

- reference.md: Architecture (4 mechanisms, 5 layers)
- examples.md: Scenarios (5+ real examples)
- PHILOSOPHY.md: Core principles
- DEFAULT_WORKFLOW.md: 23 steps
