# Project Context

**This file provides project-specific context to Claude Code agents.**

When amplihack is installed in your project, customize this file to describe YOUR project. This helps agents understand what you're building and provide better assistance.

## Quick Start

Replace the sections below with information about your project.

---

## Project: amplihack

## Overview

Development framework for popular coding agent systems (Claude Code, Github Copilot CLI, Microsoft Amplifier, codex) that provides structured dev workflows, memory, a package of useful skills and agents, goal-seeking agent generator, auto mode, self-improvement with reflection, and commands for getting the most out of agentic coding. Unlikely to work on Windows without WSL. **📚 [View Full Documentation](https://rysweet.github.io/amplihack/)**

## Multi-Tool Architecture (CRITICAL)

**amplihack is a wrapper framework** that creates a consistent environment across three agentic coding tools:

1. **Claude Code** (`amplihack claude` or `amplihack launch`) - Anthropic's agentic coding CLI
2. **GitHub Copilot** (`amplihack copilot`) - GitHub's agentic coding mode
3. **Amplifier** (`amplihack amplifier`) - Third agentic coding tool

### How amplihack Works

- **File staging**: Manages `.claude/` directory for each tool
- **Environment config**: Sets up tool-specific configurations
- **Unified CLI**: Single interface for all three tools
- **Cross-tool features**: Ensures features work consistently

### Testing Methodology (MANDATORY)

When testing amplihack features:

1. **Use subprocess testing** - Launch via `amplihack <tool>` commands, not from within current session
2. **Test all applicable tools** - Verify features work in claude, copilot, and amplifier
3. **Use TUI testing** - Use gadugi-agentic-test framework for interactive testing
4. **Validate staging** - Ensure `.claude/` files are correctly staged for each tool

**Example**: To test skill discovery, launch `amplihack claude` subprocess and verify skills load there, not just in current session.

## Architecture

### Key Components

- **Component 1**: [Purpose and responsibilities]
- **Component 2**: [Purpose and responsibilities]
- **Component 3**: [Purpose and responsibilities]

### Technology Stack

- **Language**: Python
- **Language**: JavaScript/TypeScript
- **Language**: Rust
- **Framework**: [Main framework if applicable]
- **Database**: [Database system if applicable]

## Development Guidelines

### Code Organization

[How is your code organized? What are the main directories?]

### Key Patterns

[What architectural patterns or conventions does your project follow?]

### Testing Strategy

[How do you test? Unit tests, integration tests, E2E?]

## Domain Knowledge

### Business Context

[What problem does this project solve? Who are the users?]

### Key Terminology

[Important domain-specific terms that agents should understand]

## Common Tasks

### Development Workflow

[How do developers typically work on this project?]

### Deployment Process

[How is the project deployed?]

## Important Notes

[Any special considerations, gotchas, or critical information]

---

## About This File

This file is installed by amplihack to provide project-specific context to AI agents.

**For more about amplihack itself**, see PROJECT_AMPLIHACK.md in this directory.

**Tip**: Keep this file updated as your project evolves. Accurate context leads to better AI assistance.
