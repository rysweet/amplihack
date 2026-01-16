# Getting Started with Copilot CLI and amplihack

Quick start guide to using GitHub Copilot CLI with the amplihack agentic coding framework.

## What You'll Get

amplihack provides a powerful agentic coding framework designed for Claude Code, now accessible through GitHub Copilot CLI:

- **Specialized AI agents** (37+ agents for architecture, testing, security, etc.)
- **Proven patterns** (14 foundational patterns for common problems)
- **Philosophy-driven development** (ruthless simplicity + modular design)
- **Working tools** (code analysis, MCP management, test generation)

## Prerequisites

Before starting, ensure ye have:

- **Node.js 18+** and **npm** installed
- **GitHub account** with Copilot access
- **Git** installed
- **Python 3.8+** (for amplihack tools)

### Check Prerequisites

```bash
# Check Node.js and npm
node --version  # Should be 18+
npm --version

# Check Git
git --version

# Check Python
python --version  # Should be 3.8+
```

## Installation

### Step 1: Install GitHub Copilot CLI

```bash
npm install -g @github/copilot
```

Verify installation:

```bash
copilot --version
```

### Step 2: Authenticate with GitHub

```bash
gh auth login
```

Follow the prompts to authenticate. Ensure yer account has GitHub Copilot access.

### Step 3: Install amplihack (Optional but Recommended)

Install amplihack to get access to agents, patterns, and tools:

```bash
# Using uvx (recommended)
uvx --from git+https://github.com/rysweet/amplihack amplihack launch

# Or install directly
pip install git+https://github.com/rysweet/amplihack
```

### Step 4: Initialize amplihack in Your Project

Navigate to yer project directory and initialize:

```bash
cd /path/to/your/project
amplihack init
```

This creates the `.claude/` directory with agents, patterns, and tools.

## First Session

### Launch Copilot CLI with amplihack Context

```bash
# Navigate to your project
cd /path/to/your/project

# Start Copilot CLI with full filesystem access
copilot --allow-all-tools --add-dir /path/to/your/project
```

Or use amplihack's launcher (sets up context automatically):

```bash
amplihack copilot
```

### Verify amplihack Context

In the Copilot CLI session, reference amplihack resources:

```
> What is the amplihack philosophy?
```

Copilot should reference `.claude/context/PHILOSOPHY.md` in its response.

## Quick Wins

### 1. Understand Code with Philosophy Context

```
> Explain this module following amplihack's brick philosophy
```

Copilot will analyze the code with amplihack's modular design principles.

### 2. Get Pattern Recommendations

```
> Which amplihack pattern should I use for handling subprocess errors?
```

Copilot will reference `.claude/context/PATTERNS.md` and recommend the "Safe Subprocess Wrapper" pattern.

### 3. Generate Philosophy-Compliant Code

```
> Create a new module for user authentication following amplihack patterns
```

Copilot will generate code that follows:
- Bricks & Studs architecture
- Zero-BS implementation (no stubs)
- Clear public API with `__all__`

### 4. Review Code for Philosophy Compliance

```
> Review this code for amplihack philosophy compliance
```

Copilot will check against:
- Ruthless simplicity
- Modular design
- Zero-BS implementation
- Pattern usage

### 5. Use Specialized Agents

amplihack agents are automatically available through Copilot:

```
> @architect: Design a module for rate limiting
```

Copilot invokes the architect agent with amplihack context.

## Basic Agent Usage

### Core Agents

These agents handle fundamental development tasks:

```bash
# Architecture and design
> @architect: Design a caching system

# Implementation
> @builder: Implement the caching module from the spec

# Code review
> @reviewer: Review this PR for philosophy compliance

# Testing
> @tester: Generate tests for this module

# API design
> @api-designer: Design REST API for user management

# Performance
> @optimizer: Analyze bottlenecks in this module
```

### Specialized Agents

For specific problem domains:

```bash
# Security review
> @security: Audit this authentication module

# Database design
> @database: Design schema for user profiles

# Cleanup and simplification
> @cleanup: Simplify this complex function

# Pattern recognition
> @patterns: Identify reusable patterns in this codebase
```

See the [Complete User Guide](./USER_GUIDE.md) for all 37+ agents.

## Next Steps

### Learn More

- **[Complete User Guide](./USER_GUIDE.md)** - All features and capabilities
- **[Migration Guide](./MIGRATION_FROM_CLAUDE.md)** - Switching from Claude Code
- **[API Reference](./API_REFERENCE.md)** - All commands and APIs
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Common issues and solutions
- **[FAQ](./FAQ.md)** - Frequently asked questions

### Explore amplihack Resources

```bash
# View core philosophy
cat .claude/context/PHILOSOPHY.md

# View proven patterns
cat .claude/context/PATTERNS.md

# Browse available agents
ls .claude/agents/amplihack/core/
ls .claude/agents/amplihack/specialized/

# Check available tools
ls .claude/scenarios/
```

### Try Advanced Features

Once comfortable with basics, explore:

- **Workflow execution** - Multi-step development processes
- **MCP servers** - External tool integrations
- **Auto mode** - Autonomous agentic loops
- **Skill invocation** - Claude Code skills from Copilot
- **Pattern application** - Using proven solutions

## Getting Help

### In-Session Help

```
> How do I use amplihack agents?
> Show me available amplihack patterns
> What is the brick philosophy?
```

### Documentation

- [Full documentation site](https://rysweet.github.io/amplihack/)
- [GitHub repository](https://github.com/rysweet/amplihack)
- [Issue tracker](https://github.com/rysweet/amplihack/issues)

### Common Issues

See [Troubleshooting Guide](./TROUBLESHOOTING.md) for solutions to:
- Copilot CLI not finding amplihack resources
- Agent invocation failures
- Context window issues
- Performance problems

## Quick Reference

### Essential Commands

```bash
# Start Copilot CLI with amplihack
amplihack copilot

# Or manually
copilot --allow-all-tools --add-dir /path/to/project

# Get code suggestions
> @architect: [task description]

# Reference philosophy
> Following amplihack philosophy, [request]

# Apply patterns
> Using amplihack patterns, [task]
```

### Essential Files

```
.claude/context/PHILOSOPHY.md     # Core principles
.claude/context/PATTERNS.md       # Proven solutions
.claude/context/TRUST.md          # Anti-sycophancy
.claude/agents/amplihack/         # All agents
.github/copilot-instructions.md   # Copilot context
```

## Remember

- **Philosophy first** - Always reference amplihack principles
- **Patterns over custom** - Use proven patterns when available
- **Agents for specialization** - Delegate to expert agents
- **Quality over speed** - Never compromise on implementation quality
- **Simplicity always** - Start simple, add complexity only when justified

Ye're now ready to use Copilot CLI with amplihack! Navigate to the [Complete User Guide](./USER_GUIDE.md) for comprehensive feature documentation.
