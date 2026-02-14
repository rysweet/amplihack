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

I create skills in 5 steps using amplihack's specialized agents:

1. **Clarify** → Define purpose, scope, users (prompt-writer)
2. **Design** → Plan structure, token budget, templates (architect)
3. **Generate** → Create SKILL.md with proper format (builder)
4. **Validate** → Enforce progressive disclosure, check compliance (reviewer)
5. **Test** → Define activation tests and edge cases (tester)

For detailed requirements, see [Validation Checklist](#validation-checklist) below.

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

## Validation Checklist

Before creating any skill, verify:

✅ **Name Validation**:

- Kebab-case format (lowercase with hyphens)
- 3-64 characters
- No spaces or underscores

✅ **Description Quality**:

- 10-1024 characters
- Includes trigger keywords for auto-discovery
- Specific, not generic

✅ **File Size Limits**:

- SKILL.md < 500 lines (target 300-400 lines)
- SKILL.md < 2,000 tokens (target 1,000-2,000)
- Use `wc -l SKILL.md` to verify

✅ **Progressive Disclosure** (multi-file skills):

- "When to Read Supporting Files" section exists
- Clear navigation guidance
- Content split: beginner → SKILL.md, expert → reference.md

✅ **Source Attribution** (docs-based skills):

- `source_urls` in YAML frontmatter
- Links to official documentation

✅ **Philosophy Compliance**:

- Score > 85%
- No stubs or placeholders
- Zero-BS implementation

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
