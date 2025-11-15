---
name: skill-builder
description: Creates, refines, and validates Claude Code skills following amplihack philosophy and official best practices. Automatically activates when building, creating, generating, or designing new skills.
---

# Skill Builder

## Purpose

Helps users create production-ready Claude Code skills that follow best practices from official Anthropic documentation and amplihack's ruthless simplicity philosophy.

## When I Activate

I automatically load when you mention:
- "build a skill" or "create a skill"
- "generate a skill" or "make a skill"
- "design a skill" or "develop a skill"
- "skill builder" or "new skill"
- "skill for [purpose]"

## What I Do

I orchestrate the skill creation process using amplihack's specialized agents:

1. **Clarify Requirements** (prompt-writer agent)
   - Understand skill purpose and scope
   - Define target users and use cases
   - Identify skill type (agent, command, scenario)

2. **Design Structure** (architect agent)
   - Plan YAML frontmatter fields
   - Design skill organization (single vs multi-file)
   - Calculate token budget allocation
   - Choose appropriate templates

3. **Generate Skill** (builder agent)
   - Create SKILL.md with proper YAML frontmatter
   - Write clear instructions and examples
   - Include supporting files if needed
   - Follow progressive disclosure pattern

4. **Validate Quality** (reviewer agent)
   - Check YAML frontmatter syntax
   - Verify token budget (<5,000 tokens core)
   - Ensure philosophy compliance (>85% score)
   - Test description quality for discovery

5. **Create Tests** (tester agent)
   - Define activation test cases
   - Create edge case validations
   - Document expected behaviors

## Skill Types Supported

- **skill**: Claude Code skills in `.claude/skills/` (auto-discovery)
- **agent**: Specialized agents in `.claude/agents/amplihack/specialized/`
- **command**: Slash commands in `.claude/commands/amplihack/`
- **scenario**: Production tools in `.claude/scenarios/`

See [examples.md](./examples.md) for detailed examples of each type.

## Command Interface

For explicit invocation:
```bash
/amplihack:skill-builder <skill-name> <skill-type> <description>
```

Examples in [examples.md](./examples.md).

## Documentation

**Comprehensive guides**:
- [reference.md](./reference.md): Architecture, patterns, YAML spec, best practices
- [examples.md](./examples.md): Real-world usage, testing, troubleshooting

**Official sources** (embedded in reference.md):
- Claude Code Skills docs
- Anthropic Agent SDK docs
- Engineering blog posts
- Claude Cookbooks
- Community examples

---

**Note**: This skill automatically loads when Claude detects skill building intent. For explicit control, use `/amplihack:skill-builder`.
