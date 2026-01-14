# Amplifier-Specific Instructions

This document provides Amplifier-specific guidance for the amplihack bundle.

## Bundle Structure

This is a **thin bundle** that references existing Claude Code components without duplication:

- Skills, agents, and context are in `../.claude/`
- This bundle provides the packaging layer for Amplifier compatibility
- No code duplication - same components work in both environments

## Using with Amplifier

### Direct Usage
```bash
amplifier run --bundle amplihack
```

### As a Dependency
```yaml
includes:
  - bundle: git+https://github.com/rysweet/amplihack@main#amplifier-bundle
```

## What's Referenced

| Component | Location | Count |
|-----------|----------|-------|
| Skills | `../.claude/skills/` | 73 |
| Agents | `../.claude/agents/` | 3 |
| Context | `../.claude/context/` | 3 files |
| Workflows | `../.claude/workflow/` | 7 docs |

## Compatibility

This bundle maintains compatibility with both:
- **Claude Code** - Via the `.claude/` directory structure
- **Amplifier** - Via this bundle packaging

The same skills, agents, and context work in both environments.

## Future: Amplifier Modules

Amplifier-specific tools and hooks will be added in future updates when properly ported from the existing Claude Code implementations in `.claude/tools/amplihack/`. These require conversion to Amplifier's module format with `mount()` entry points and `pyproject.toml` entry point registration.
