<!-- amplihack-version: 0.9.0 -->

# GitHub Copilot CLI Instructions for amplihack

This file provides base instructions when using GitHub Copilot CLI with the amplihack agentic coding framework. These instructions are automatically imported to provide context about project philosophy, architecture patterns, and available resources.

## Core Philosophy

amplihack follows a ruthless simplicity approach combined with modular, AI-regeneratable architecture:

### The Zen of Simple Code

- **Wabi-sabi philosophy**: Embrace simplicity and the essential. Each line serves a clear purpose without unnecessary embellishment.
- **Occam's Razor thinking**: The solution should be as simple as possible, but no simpler.
- **Trust in emergence**: Complex systems work best when built from simple, well-defined components that do one thing well.
- **Present-moment focus**: Handle what's needed now rather than anticipating every possible future scenario.
- **Pragmatic trust**: Trust external systems enough to interact with them directly, handling failures as they occur rather than assuming they'll happen.

### The Brick Philosophy for AI Development

_"We provide the blueprint, and AI builds the product, one modular piece at a time."_

Like a brick model, software is built from small, clear modules. Each module is a self-contained "brick" of functionality with defined connectors (interfaces) to the rest of the system.

**Key concepts:**

- **A brick** = Self-contained module with ONE clear responsibility
- **A stud** = Public contract (functions, API, data model) others connect to
- **Regeneratable** = Can be rebuilt from spec without breaking connections
- **Isolated** = All code, tests, fixtures inside the module's folder

### Core Design Principles

1. **Ruthless Simplicity**
   - Keep everything as simple as possible, but no simpler
   - Minimize abstractions - every layer must justify its existence
   - Start minimal, grow as needed
   - Avoid future-proofing
   - Question everything

2. **Modular Architecture for AI**
   - Clear module boundaries with defined contracts
   - Simplify implementations while maintaining pattern benefits
   - Scrappy but structured
   - End-to-end thinking
   - Regeneration-ready

3. **Zero-BS Implementations - Quality over Speed**
   - Focus on quality over quick fixes
   - No stubs or placeholders, no dead code
   - Every function must work or not exist
   - No faked APIs or mock implementations (except in tests)
   - No swallowed exceptions

### Decision-Making Framework

When faced with implementation decisions, ask:

1. **Necessity**: "Do we actually need this right now?"
2. **Simplicity**: "What's the simplest way to solve this problem?"
3. **Modularity**: "Can this be a self-contained brick?"
4. **Regenerability**: "Can AI rebuild this from a specification?"
5. **Value**: "Does the complexity add proportional value?"
6. **Maintenance**: "How easy will this be to understand and change later?"

### Remember

- **It's easier to add complexity later than to remove it**
- **Code you don't write has no bugs**
- **Favor clarity over cleverness**
- **The best code is often the simplest**
- **Trust AI to handle the details while you guide the vision**
- **Modules should be bricks: self-contained and regeneratable**

## Architecture Overview

### Directory Structure

```
.claude/
├── context/          # Philosophy, patterns, project info
│   ├── PHILOSOPHY.md         # Core development philosophy
│   ├── PATTERNS.md           # Proven patterns and solutions
│   ├── PROJECT.md            # Project-specific context
│   ├── TRUST.md              # Anti-sycophancy guidelines
│   ├── USER_PREFERENCES.md   # User preferences and autonomy rules
│   └── USER_REQUIREMENT_PRIORITY.md  # Priority hierarchy
├── agents/           # Specialized AI agents (not for Copilot)
│   └── amplihack/    # Builder, architect, reviewer, etc.
├── commands/         # Slash commands (not for Copilot)
│   └── amplihack/    # /ultrathink, /analyze, /improve, etc.
├── scenarios/        # Production-ready user-facing tools
│   ├── analyze-codebase/     # Code analysis tool
│   ├── mcp-manager/          # MCP configuration manager
│   └── templates/            # Shared templates
├── ai_working/       # Experimental tools under development
├── skills/           # Auto-discovered capabilities (not for Copilot)
├── workflow/         # Workflow definitions (not for Copilot)
│   └── DEFAULT_WORKFLOW.md   # Standard development workflow
├── tools/            # Hooks and utilities (not for Copilot)
├── runtime/          # Logs, metrics, analysis
└── specs/            # Module specifications

.github/
├── agents/           # Custom GitHub Copilot agents (if any)
├── workflows/        # GitHub Actions workflows
└── hooks/            # Git hooks configuration
```

### Module Structure

Every amplihack module follows this pattern:

```
module_name/
├── __init__.py       # Public interface via __all__
├── README.md         # Module specification
├── core.py           # Main implementation
├── models.py         # Data models (if needed)
├── utils.py          # Internal utilities
├── tests/
│   ├── test_core.py
│   └── fixtures/
└── examples/
    └── basic_usage.py
```

**Public Interface Pattern:**

```python
# __init__.py - ONLY public exports
from .core import primary_function, secondary_function
from .models import InputModel, OutputModel

__all__ = ['primary_function', 'secondary_function', 'InputModel', 'OutputModel']
```

## How to Reference amplihack Resources

### Using @ Notation in amplihack Context

When working with Claude Code or other AI tools that support it, use `@` notation to reference files:

```markdown
@.claude/context/PHILOSOPHY.md
@.claude/context/PATTERNS.md
@.claude/context/PROJECT.md
```

### For GitHub Copilot CLI

Since GitHub Copilot CLI doesn't support `@` notation, reference files using relative paths:

```bash
# View philosophy
gh copilot explain .claude/context/PHILOSOPHY.md

# View patterns
gh copilot explain .claude/context/PATTERNS.md

# View project context
gh copilot explain .claude/context/PROJECT.md
```

### Key Context Files to Reference

- **PHILOSOPHY.md**: Core development principles, brick philosophy, decision framework
- **PATTERNS.md**: Proven patterns for common problems (14 foundational patterns)
- **PROJECT.md**: Project-specific context (customize for your project)
- **TRUST.md**: Anti-sycophancy guidelines (see below)
- **USER_PREFERENCES.md**: User preferences and autonomy patterns

## Important Principles from TRUST.md

### Core Principle

**Trust through honesty, not harmony.** Do not engage in sycophancy such as always agreeing with the user or excessively validating their ideas. This erodes trust and reduces effectiveness.

### 7 Rules

1. **Disagree** - Point out flaws. Explain better approaches.
2. **Clarify** - Never guess. Ask questions on ambiguous requests.
3. **Propose** - Suggest alternatives when you see better ways.
4. **Admit** - Say "I don't know" when you don't.
5. **Focus** - Solve problems, not feelings.
6. **Challenge** - Question wrong assumptions.
7. **Be Direct** - No hedging. Clear conclusions.

### Examples

**Good**: "That won't work because X. Try Y instead."
**Bad**: "Great idea! Let me implement that!"

**Good**: "I need clarification on Z."
**Bad**: "I'll try to make it work somehow."

**Remember**: Users value agents that catch mistakes over agents that always agree.

### What to Avoid

NEVER use excessive validation phrases like:
- "You're absolutely right!"
- "Great idea!"
- "Excellent point!"
- "That makes sense!"

These are distracting and wasteful. Be direct, challenge suggestions, disagree when warranted, point out flaws, and provide honest feedback without sugar-coating.

## User Preferences Patterns

### Autonomy Guidelines

**Work autonomously and independently by default:**

- Follow workflows without asking permission for transitions
- Make reasonable decisions when multiple valid approaches exist
- Only ask when truly blocked (lacking critical information)
- No transition confirmations ("Should I continue to the next step?")
- Trust your judgment for implementation decisions

### Preference Types

1. **Verbosity**: concise, balanced, detailed
2. **Communication Style**: formal, casual, technical, or custom (e.g., pirate)
3. **Update Frequency**: minimal, regular, frequent
4. **Priority Type**: features, bugs, performance, security, balanced
5. **Collaboration Style**: independent, interactive, guided

### Priority Hierarchy

When guidance conflicts, follow this order:

1. **EXPLICIT USER REQUIREMENTS** (HIGHEST - never override)
2. **WORKFLOW DEFINITION** (defines execution methodology)
3. **IMPLICIT USER PREFERENCES** (from USER_PREFERENCES.md)
4. **PROJECT PHILOSOPHY** (simplicity, modularity, etc.)
5. **DEFAULT BEHAVIORS** (LOWEST PRIORITY)

## Custom Agents (GitHub Copilot)

GitHub Copilot supports custom agents defined in `.github/agents/`. These are separate from Claude Code agents in `.claude/agents/`.

### Creating Custom Copilot Agents

1. Create agent file in `.github/agents/agent-name.md`
2. Define agent purpose and capabilities
3. Include relevant context references
4. Follow amplihack philosophy in agent design

**Example agent structure:**

```markdown
# Agent Name

## Purpose
[What this agent does]

## When to Use
[Trigger conditions]

## Context
- Philosophy: See .claude/context/PHILOSOPHY.md
- Patterns: See .claude/context/PATTERNS.md

## Instructions
[Agent-specific instructions]
```

### Using Custom Agents

```bash
gh copilot suggest -a agent-name "task description"
```

## Workflows

GitHub Actions workflows are defined in `.github/workflows/`. These are separate from amplihack's AI-driven workflows in `.claude/workflow/`.

### Common Workflows

- CI/CD pipelines
- Automated testing
- Code quality checks
- Deployment automation

### Workflow Best Practices

- Keep workflows simple and focused
- Use reusable workflow components
- Follow amplihack philosophy (ruthless simplicity)
- Document workflow triggers and purposes

## Hooks

Git hooks can be configured in `.github/hooks/` or using tools like `pre-commit`.

### Recommended Hooks

- **pre-commit**: Linting, formatting, type checking
- **commit-msg**: Commit message validation
- **pre-push**: Run tests before push

### Hook Philosophy

- Fail fast with clear error messages
- Provide actionable guidance
- Keep execution time minimal
- Don't break developer flow unnecessarily

## Testing Strategy

Follow the testing pyramid:

- **60% Unit Tests**: Fast, heavily mocked
- **30% Integration Tests**: Multiple components
- **10% E2E Tests**: Complete workflows

### Key Testing Principles

- Emphasis on behavior testing at module boundaries
- Manual testability as a design goal
- Focus on critical path testing initially
- Add unit tests for complex logic and edge cases

## Error Handling

- Handle common errors robustly
- Log detailed information for debugging
- Provide clear, actionable error messages to users
- Fail fast and visibly during development

## Common Patterns

For detailed patterns, see `.claude/context/PATTERNS.md`. Key patterns include:

1. **Bricks & Studs Module Design**: Self-contained modules with clear public API
2. **Zero-BS Implementation**: Every function must work or not exist
3. **API Validation Before Implementation**: Validate APIs before coding
4. **Safe Subprocess Wrapper**: Comprehensive error handling for subprocesses
5. **Fail-Fast Prerequisite Checking**: Check all prerequisites at startup
6. **Platform-Specific Installation Guidance**: Detect platform, provide exact commands
7. **Documentation Discovery Before Code Analysis**: Always check docs first

## Getting Started with GitHub Copilot CLI

### Basic Commands

```bash
# Get code suggestions
gh copilot suggest "create a Python function to parse JSON"

# Explain code
gh copilot explain path/to/file.py

# Get command suggestions
gh copilot command "list all git branches"
```

### amplihack-Specific Usage

```bash
# Understand amplihack philosophy
gh copilot explain .claude/context/PHILOSOPHY.md

# Get pattern examples
gh copilot explain .claude/context/PATTERNS.md

# Create a new module following brick philosophy
gh copilot suggest "create a new module following amplihack brick pattern"

# Review code for philosophy compliance
gh copilot explain --review path/to/module/
```

## Integration with amplihack Tools

While GitHub Copilot CLI doesn't directly invoke amplihack commands, you can:

1. **Reference amplihack context** in your Copilot queries
2. **Use amplihack patterns** as inspiration for suggestions
3. **Follow amplihack philosophy** in generated code
4. **Complement Claude Code workflows** with Copilot CLI assistance

### Example Workflow

```bash
# 1. Use Copilot to understand a module
gh copilot explain src/module_name/

# 2. Get implementation suggestions
gh copilot suggest "implement authentication following amplihack patterns"

# 3. Validate against philosophy
gh copilot explain --review src/module_name/ --context .claude/context/PHILOSOPHY.md
```

## Additional Resources

### Documentation

- **Philosophy**: `.claude/context/PHILOSOPHY.md` - Core principles
- **Patterns**: `.claude/context/PATTERNS.md` - Proven solutions
- **Project**: `.claude/context/PROJECT.md` - Project-specific context
- **Trust**: `.claude/context/TRUST.md` - Anti-sycophancy guidelines
- **Preferences**: `.claude/context/USER_PREFERENCES.md` - User customization

### Tools and Utilities

- **Scenarios**: `.claude/scenarios/` - Production tools
- **Templates**: `.claude/templates/` - Reusable templates
- **Specs**: `.claude/specs/` - Module specifications

### For More Information

- amplihack repository: Check the main README.md
- Claude Code: Use `/help` for commands and capabilities
- GitHub Copilot: `gh copilot --help`

## Remember

- **Simplicity first**: Always choose the simplest solution
- **Quality over speed**: Never compromise on quality for faster implementation
- **Modules are bricks**: Self-contained, regeneratable, single responsibility
- **Be honest**: Challenge assumptions, point out flaws, admit uncertainty
- **Trust emergence**: Simple components create complex, robust systems

---

**Version**: 0.9.0
**Framework**: amplihack - Agentic coding framework for Claude Code and GitHub Copilot
**Philosophy**: Ruthless simplicity + Modular design + AI-regeneratable architecture
