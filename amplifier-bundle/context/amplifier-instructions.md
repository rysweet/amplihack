# Amplifier-Specific Instructions

This document provides Amplifier-specific guidance for the amplihack bundle.

## Bundle Structure

This is a **thin bundle** that references existing Claude Code components without duplication:

- Skills, agents, and context are in `../.claude/`
- Amplifier-specific modules are in `./modules/`
- This bundle provides the packaging layer for Amplifier compatibility

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

## Module Integration

The following Amplifier modules are included:

| Module | Type | Purpose |
|--------|------|---------|
| `tool-memory` | Tool | SQLite-backed agent memory |
| `tool-lock` | Tool | File locking with debate resolution |
| `tool-session-utils` | Tool | Fork management, instruction append |
| `tool-workflow` | Tool | Workflow tracking and transcripts |
| `tool-goal-agent-generator` | Tool | Goal-driven agent generation |
| `hook-power-steering` | Hook | Session completion verification |
| `hook-agent-memory` | Hook | Memory injection into context |
| `hook-xpia-defense` | Hook | Prompt injection defense |

## Compatibility

This bundle maintains compatibility with both:
- **Claude Code** - Via the `.claude/` directory structure
- **Amplifier** - Via this bundle packaging

The same skills, agents, and context work in both environments.
