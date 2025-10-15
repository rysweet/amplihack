# AGENTS.md - GitHub Copilot CLI Guide

This file provides guidance to GitHub Copilot CLI when working with code in this
repository through the amplihack framework.

## Project Overview

**Microsoft Hackathon 2025 - Agentic Coding Framework**

An advanced agentic coding framework that leverages AI agents to accelerate
software development through intelligent automation, code generation, and
collaborative problem-solving.

## Important Context Files

When starting a session, reference these files for context:

```
@.claude/context/PHILOSOPHY.md
@.claude/context/PROJECT.md
@.claude/context/PATTERNS.md
@.claude/context/TRUST.md
@.claude/context/USER_PREFERENCES.md
@.claude/context/USER_REQUIREMENT_PRIORITY.md
@.claude/context/DISCOVERIES.md
```

## Core Philosophy

### Ruthless Simplicity

- Keep implementations as simple as possible
- Minimize abstractions and layers
- Start minimal, grow as needed
- Avoid future-proofing for hypothetical requirements
- Question every complexity

### The Brick Philosophy

Software is built from small, clear modules ("bricks") with defined interfaces
("studs"). Each module:

- Has ONE clear responsibility
- Can be rebuilt from its specification
- Contains all its code, tests, and fixtures
- Connects through stable public contracts

## The Workflow

Follow the workflow defined in `@.claude/workflow/DEFAULT_WORKFLOW.md`. This
15-step workflow defines:

- Order of operations (sequential steps)
- Git workflow (branch, commit, push, PR)
- CI/CD integration points
- Review and merge requirements

For non-trivial tasks, use the UltraThink approach to orchestrate multi-agent
execution.

## Using Subagents with Copilot CLI

### What are Subagents?

Subagents are specialized AI assistants defined in `.claude/agents/**/*.md`
files. Each agent has expertise in a specific domain (architecture, testing,
security, etc.).

### How to Invoke Subagents

To use a subagent from GitHub Copilot CLI:

1. **Select the appropriate agent** from `.claude/agents/amplihack/` based on
   the task
2. **Craft a specific prompt** with context and instructions
3. **Launch as subprocess** using copilot with the agent file included

**Example**:

```bash
copilot --allow-all-tools -p "Include @.claude/agents/amplihack/core/prompt-writer.md -- Improve this prompt: <user-prompt>"
```

### Available Subagents

**Core Agents** (`.claude/agents/amplihack/core/`):

- `architect.md` - System design and specifications
- `builder.md` - Code implementation from specs
- `reviewer.md` - Code review and philosophy compliance
- `tester.md` - Test generation and validation
- `cleanup.md` - Code simplification and refactoring
- `analyzer.md` - Deep code understanding
- `ambiguity.md` - Clarifying unclear requirements
- `prompt-writer.md` - Improving and clarifying prompts

**Specialized Agents** (`.claude/agents/amplihack/specialized/`):

- `api-designer.md` - API contract definitions
- `database.md` - Schema and query optimization
- `integration.md` - External service connections
- `optimizer.md` - Performance improvements
- `security.md` - Security vulnerability assessment
- `patterns.md` - Identifying reusable solutions

**Workflow Agents** (`.claude/agents/amplihack/workflows/`):

- `ci-diagnostic-workflow.md` - CI/CD troubleshooting
- `pre-commit-diagnostic.md` - Pre-commit hook debugging
- `fix-agent.md` - Rapid error pattern resolution

### When to Use Subagents

**Always delegate when possible**. Use subagents for:

- System design → `architect.md`
- Implementation → `builder.md`
- Code review → `reviewer.md`
- Testing → `tester.md`
- API design → `api-designer.md`
- Performance → `optimizer.md`
- Security → `security.md`
- Cleanup → `cleanup.md`

**Default to parallel execution** unless dependencies require sequential order.

## Using Commands with Copilot CLI

### What are Commands?

Commands are AI-powered operations defined in `.claude/commands/**/*.md` files.
Each command is a structured prompt for a specific operation.

### How to Invoke Commands

To run a command from GitHub Copilot CLI:

```bash
copilot --allow-all-tools -p "Include @.claude/commands/<path>/<command>.md <args> <additional instructions>"
```

**Example**:

```bash
copilot --allow-all-tools -p "Include @.claude/commands/amplihack/test.md -- Run tests for authentication module"
```

### Available Commands

Browse `.claude/commands/` directory for available commands. Common commands
include test execution, documentation generation, and code analysis.

## Decision Recording

**IMPORTANT**: Record significant decisions in session logs:

Format: `What was decided | Why | Alternatives considered`

Location: `.claude/runtime/logs/<session_id>/DECISIONS.md`

When to record:

- Architectural choices
- Trade-offs between approaches
- Decisions affecting system design

## User Requirement Priority

**MANDATORY BEHAVIOR**: Follow this priority hierarchy:

1. **EXPLICIT USER REQUIREMENTS** (HIGHEST - NEVER OVERRIDE)
2. **IMPLICIT USER PREFERENCES**
3. **PROJECT PHILOSOPHY**
4. **DEFAULT BEHAVIORS** (LOWEST)

When user says "ALL files", "include everything", or provides specific
requirements in quotes, these CANNOT be optimized away by simplification.

See `@.claude/context/USER_REQUIREMENT_PRIORITY.md` for complete guidelines.

## Autonomous Mode (Auto Mode)

When running via `amplihack copilot --auto`, you're in an agentic loop that:

1. Clarifies objectives with evaluation criteria
2. Creates execution plans with parallel opportunities
3. Executes plans autonomously
4. Evaluates progress iteratively
5. Continues until objective achieved or max turns reached

**In auto mode**:

- Work autonomously - make concrete changes
- Use subagents liberally for specialized tasks
- Document your progress clearly
- Report completion with "TASK COMPLETED: [description]"
- Ask questions with "QUESTION: [your question]"

## Session Hooks

Auto mode will run hooks at appropriate times:

- `session_start` - At beginning of session
- `stop` - At end of session

(Note: Tool hooks and other hooks aren't supported in Copilot CLI auto mode)

## Key Differences from Claude Code

When using Copilot CLI vs Claude Code:

1. **Subagent invocation**: Must explicitly launch subprocess with copilot
   command
2. **Commands**: Must explicitly include command .md file in prompt
3. **Hooks**: Only session_start and stop hooks run in auto mode
4. **Context**: Must manually include context files when needed

## Best Practices

1. **Keep it simple** - Favor simplicity over complexity
2. **Delegate aggressively** - Use subagents for specialized work
3. **Document decisions** - Record significant choices
4. **Test locally** - Always test changes before committing
5. **Follow the workflow** - Respect the 15-step process
6. **Respect user requirements** - Never optimize away explicit requirements
7. **Work in modules** - Build regeneratable "bricks"

## Remember

- The workflow is authoritative - follow it
- Simplicity beats cleverness
- Modules should be self-contained bricks
- Trust AI to handle details while humans guide vision
- Code you don't write has no bugs
- It's easier to add complexity later than remove it

## Getting Help

- Read `@.claude/context/PHILOSOPHY.md` for development principles
- Check `@.claude/workflow/DEFAULT_WORKFLOW.md` for process steps
- Browse `.claude/agents/` for available subagents
- Review `.claude/context/DISCOVERIES.md` for project learnings

---

This framework serves as your guide when working with GitHub Copilot CLI through
amplihack. Follow these principles, leverage the tools provided, and build with
ruthless simplicity.
