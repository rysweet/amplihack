---
name: skill-builder
version: 1.0.0
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
   - **Enforce Progressive Disclosure**: SKILL.md must be < 500 lines (target 1,000-2,000 tokens)
   - **Validate Navigation**: Multi-file skills MUST include "When to Read Supporting Files" section
   - **Check Source URLs**: Skills based on external docs MUST have `source_urls` in frontmatter
   - Ensure philosophy compliance (>85% score)
   - Test description quality for discovery

5. **Create Tests** (tester agent)
   - Define activation test cases
   - Create edge case validations
   - Document expected behaviors

## Skill Types Supported

- **skill**: Claude Code skills in `~/.amplihack/.claude/skills/` (auto-discovery)
- **agent**: Specialized agents in `~/.amplihack/.claude/agents/amplihack/specialized/`
- **command**: Slash commands in `~/.amplihack/.claude/commands/amplihack/`
- **scenario**: Production tools in `~/.amplihack/.claude/scenarios/`

See [examples.md](./examples.md) for detailed examples of each type.

## Command Interface

For explicit invocation:

```bash
/amplihack:skill-builder <skill-name> <skill-type> <description>
```

Examples in [examples.md](./examples.md).

## Official Best Practices Enforcement

This skill enforces **Claude API Skill Authoring Best Practices**:

1. **Progressive Disclosure Pattern** (MANDATORY)
   - SKILL.md < 500 lines (target 1,000-2,000 tokens)
   - Split content into reference.md, examples.md, patterns.md
   - Content-based splitting: beginner (SKILL.md) vs expert (supporting files)

2. **Navigation Guides** (MANDATORY for multi-file skills)
   - Explicit "When to Read Supporting Files" section
   - Clear guidance on when to read each file
   - Example: "Read reference.md when you need complete API details"

3. **Source Attribution** (MANDATORY for documentation-based skills)
   - `source_urls` field in YAML frontmatter
   - Enables drift detection and proper attribution
   - Format: `source_urls: [list of documentation URLs]`

4. **Token Budget**
   - SKILL.md: 1,000-2,000 tokens (warning at 2,000+)
   - Supporting files: Unbounded (referenced on-demand)
   - Aggressive splitting encouraged for better UX

5. **Quality Thresholds**
   - YAML syntax validation
   - Required fields (name, description, auto_activates, source_urls if applicable)
   - Philosophy compliance > 85%
   - Description clarity for autonomous discovery

## Documentation

**Supporting Files** (progressive disclosure):

- [reference.md](./reference.md): Complete best practices, YAML spec, architecture, validation rules
- [examples.md](./examples.md): Real-world skill creation workflows, testing, troubleshooting

**Original Documentation Sources** (embedded in reference.md):

1. **Official Claude Code Skills**: https://code.claude.com/docs/en/skills
2. **Anthropic Agent SDK Skills**: https://docs.claude.com/en/docs/agent-sdk/skills
3. **Agent Skills Engineering Blog**: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
4. **Claude Cookbooks - Skills**: https://github.com/anthropics/claude-cookbooks/tree/main/skills
5. **Skills Custom Development Notebook**: https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb
6. **metaskills/skill-builder** (Reference): https://github.com/metaskills/skill-builder

All documentation is embedded in reference.md for offline access. Links provided for updates and verification.

---

**Note**: This skill automatically loads when Claude detects skill building intent. For explicit control, use `/amplihack:skill-builder`.
