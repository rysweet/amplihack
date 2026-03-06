# Project: Amplihack Development Framework

## Overview

Amplihack is a development tool that extends Claude Code with specialized AI agents and automated workflows. It transforms conversational AI assistance into a development orchestrator with autonomous execution, multi-agent coordination, and intelligent automation.

## Purpose

Amplihack enables intelligent delegation to specialized agents, workflow orchestration through customizable multi-step processes, autonomous operation via multi-turn agentic loops, continuous learning by capturing patterns, and philosophy enforcement to maintain ruthless simplicity.

## Architecture

### Core Modules

```
amplihack/
├── launcher/           # Claude Code and proxy integration
├── proxy/             # Azure OpenAI and GitHub Models support
├── bundle_generator/  # Agent bundle creation and distribution
├── knowledge_builder/ # Socratic knowledge acquisition
├── memory/            # Neo4j-based persistent memory
├── security/          # XPIA threat detection system
└── utils/             # Shared utilities
```

### Configuration Structure

```
.claude/
├── agents/           # 29 specialized agents (6 core + 23 specialized)
├── commands/         # Slash commands (/ultrathink, /analyze, /fix)
├── workflow/         # DEFAULT_WORKFLOW.md (customizable workflow)
├── tools/            # Session hooks (SessionStart, Stop, PostToolUse, PreCompact)
├── context/          # Philosophy, patterns, discoveries
└── runtime/          # Logs, metrics, analysis
```

## Key Components

### Agent System (29 Agents)

**Core (6)**: architect, builder, reviewer, tester, api-designer, optimizer
**Specialized (23)**: analyzer, security, database, patterns, cleanup, fix-agent, pre-commit-diagnostic, ci-diagnostic-workflow, knowledge-archaeologist, multi-agent-debate, n-version-validator, and more

Characteristics: Single responsibility, clear delegation triggers, parallel execution by default

### Workflow Engine

Multi-step default workflow: Clarify → Issue → Branch → Test → Implement → Simplify → Test → Commit → PR → Review → Feedback → Philosophy → Merge

Customizable via DEFAULT_WORKFLOW.md, orchestrated by UltraThink, integrates with git/CI/CD/hooks

### Session Hooks

Four hook types providing session lifecycle management:

- SessionStart: Import context, configure environment
- Stop: Save state, capture learnings
- PostToolUse: Log decisions, track metrics
- PreCompact: Preserve critical context

### Autonomous Mode

Multi-turn agentic loops (Clarify → Plan → Execute → Evaluate) working with Claude Code and GitHub Copilot CLI, configurable max turns, comprehensive logging

## Development Workflows

### For Amplihack Developers

**Adding Agents**: Create in `~/.amplihack/.claude/agents/amplihack/specialized/`, define role, add delegation triggers, test, document

**Modifying Workflows**: Edit DEFAULT_WORKFLOW.md, test with `/ultrathink`, document rationale

**Adding Commands**: Create in `~/.amplihack/.claude/commands/amplihack/`, implement logic, add help text, test execution

### For Amplihack Users

```bash
# Installation
uvx --from git+https://github.com/owner/repo amplihack launch

# Usage
amplihack launch                     # Launch Claude Code
amplihack launch --auto              # Launch with auto mode
amplihack launch --with-proxy-config azure.env

# Key Commands
/amplihack:ultrathink <task>        # Orchestrate workflow
/amplihack:analyze <path>           # Code analysis
/amplihack:fix [pattern]            # Intelligent fixes
/amplihack:ddd:1-plan               # Document-driven development
```

## Design Decisions

### 1. Ruthless Simplicity

Minimal abstractions, direct implementations, simple subprocess execution, file-based configuration, no unnecessary classes or complex state management

### 2. Modular Design (Bricks & Studs)

Self-contained modules with clear contracts, independent agents, standalone commands, public interfaces via `__all__`

### 3. AI-First Architecture

Clear specifications enable regeneration, behavior testing over implementation details, documentation is specification

### 4. Parallel Execution by Default

Independent operations run in parallel, sequential only for hard dependencies, agent coordination protocols

### 5. Zero-BS Implementation

No stubs, placeholders, or dead code; every function works or doesn't exist; quality over speed

## Philosophy Alignment

### Core Values

1. Simplicity: Minimal code, clear purpose
2. Modularity: Self-contained components
3. Trust in Emergence: Simple parts, complex behavior
4. Present-Moment Focus: Solve current needs, not hypothetical futures
5. Human-AI Partnership: Humans define, AI executes

### Decision Framework

1. Necessity: Do we actually need this now?
2. Simplicity: What's the simplest solution?
3. Modularity: Can this be a self-contained brick?
4. Regenerability: Can AI rebuild from specification?
5. Value: Does complexity add proportional value?

## Success Metrics

**Development**: Code simplicity (lines vs functionality), module independence (coupling), agent effectiveness (completion rate), documentation quality (code-to-docs ratio)

**User**: Development velocity (spec to working code), parallel efficiency (coordination), learning rate (patterns codified), philosophy compliance

## Contributing to Amplihack

### Development Setup

```bash
git clone https://github.com/owner/repo.git
cd repo
uv pip install -e .
amplihack launch
```

### Making Changes

Fork repository, create branch, follow philosophy (ruthless simplicity), test with real usage, submit PR with clear rationale

### Adding Features

Identify need after 2-3 similar requests, design minimal viable implementation, follow brick philosophy, test thoroughly, document completely, submit PR

## Getting Started

1. Review `~/.amplihack/.claude/context/PHILOSOPHY.md` for core principles
2. Explore `~/.amplihack/.claude/agents/amplihack/` for agent capabilities
3. Study `~/.amplihack/.claude/context/PATTERNS.md` for proven solutions
4. Try `/amplihack:*` commands in practice
5. Examine `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` for process understanding

---

_"Amplihack: Building the tools that build the future"_
