# Component Catalog Usage Guide

## Overview

The Component Catalog (`COMPONENT_CATALOG.md`) is an auto-generated reference for all workflows, commands, skills, and agents in the amplihack framework. It's extracted from frontmatter metadata in component files.

## Regenerating the Catalog

To regenerate the catalog after adding or modifying components:

```bash
python3 .claude/tools/generate_catalog.py
```

Or use the Makefile:

```bash
make catalog
```

## What's Included

The catalog contains:

- **Workflows** (9): All workflow files in `.claude/workflow/`
- **Commands** (33): All command files in `.claude/commands/`
- **Skills** (46): All SKILL.md files in `.claude/skills/`
- **Agents** (35): All agent files in `.claude/agents/`
  - Core Agents (6)
  - Specialized Agents (24)
  - Workflow Agents (2)
  - Other Agents (3)

**Total**: 123 components

## Catalog Structure

Each component entry includes:

### Workflows
- Name and version
- Description
- Number of steps/phases
- Phase names
- File location

### Commands
- Command name (with proper prefix)
- Version and description
- Trigger keywords
- What it invokes (workflows, agents, files)
- File location

### Skills
- Name and version
- Description
- Activation keywords
- Auto-activation status
- File location

### Agents
- Name and version
- Description
- Role
- File location

## Using the Catalog

The catalog is a reference document for:

1. **Discovery**: Finding the right component for a task
2. **Understanding**: Learning what each component does
3. **Integration**: Understanding invocation relationships
4. **Documentation**: Providing component overviews

## Frontmatter Requirements

For a component to appear in the catalog, it must have YAML frontmatter with at least:

```yaml
---
name: component-name
version: 1.0.0
description: Clear description of what this does
---
```

Additional fields vary by component type (see examples in existing files).

## Automated Updates

The catalog should be regenerated:

- After adding new components
- After updating component frontmatter
- Before major releases
- When component descriptions change

## Integration

The catalog is referenced in:

- `CLAUDE.md` (project instructions)
- Documentation workflows
- Component discovery processes
- System architecture documentation
