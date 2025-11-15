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

**Agent Skills**: For AI-driven automation tasks
- Location: `.claude/agents/amplihack/specialized/`
- Use when: Task requires intelligent decision-making

**Command Skills**: For user-invoked workflows
- Location: `.claude/commands/amplihack/`
- Use when: Explicit user control needed

**Scenario Skills**: For production tools
- Location: `.claude/scenarios/`
- Use when: Mature, well-tested functionality

## Key Validation Rules

**Name Format**:
- Kebab-case only (lowercase-with-hyphens)
- 3-50 characters
- No underscores or special characters

**Description Quality**:
- 10-200 characters
- Include trigger keywords
- Be specific and actionable
- Example: "Transforms data between JSON, YAML, and XML formats with validation"

**Token Budget**:
- Core instructions: <5,000 tokens (warn >5K, error >20K)
- Use progressive disclosure for details
- Move code to scripts/ directory
- Reference docs in reference.md

**YAML Frontmatter**:
```yaml
---
name: skill-name
description: Clear, keyword-rich description
---
```

## Research Foundation

This skill implements patterns from:
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Anthropic Agent SDK](https://docs.claude.com/en/docs/agent-sdk/skills)
- [Agent Skills Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Cookbooks](https://github.com/anthropics/claude-cookbooks/tree/main/skills)
- [metaskills/skill-builder](https://github.com/metaskills/skill-builder)

## Explicit Command

For explicit invocation with specific parameters:
```bash
/amplihack:skill-builder <skill-name> <skill-type> <description>
```

Example:
```bash
/amplihack:skill-builder data-validator agent "Validates JSON schemas with detailed error reporting"
```

## Integration

This skill works with:
- **Command version**: `/amplihack:skill-builder` for power users
- **Auto-invocation**: Loads automatically when skill building detected
- **Agent orchestration**: Uses prompt-writer, architect, builder, reviewer, tester
- **Philosophy validation**: Ensures ruthless simplicity and zero-BS compliance

## Example Interactions

**User**: "I need to create a skill for analyzing test coverage"

**I activate and**:
1. Clarify: What aspects of test coverage? (unit, integration, E2E)
2. Design: Plan skill structure for test-gap-analyzer
3. Generate: Create SKILL.md with proper frontmatter
4. Validate: Check token budget and description quality
5. Test: Define activation scenarios

**User**: "Build a skill that generates Mermaid diagrams"

**I activate and**:
1. Clarify: What types of diagrams? (flowchart, sequence, class, etc.)
2. Design: Structure for mermaid-diagram-generator
3. Generate: Complete skill with examples
4. Validate: Philosophy compliance check
5. Deliver: Production-ready skill

## Philosophy Alignment

- **Ruthless Simplicity**: Start minimal, add only as needed
- **Self-Contained**: All templates and logic embedded
- **Zero-BS**: No stubs, placeholders, or fake implementations
- **Regeneratable**: Clear specifications for reproducibility
- **Token Efficient**: Progressive disclosure, <5K token core

## Success Criteria

Generated skills must:
- ✅ Have valid YAML frontmatter
- ✅ Include clear, keyword-rich description
- ✅ Stay within token budget
- ✅ Pass philosophy compliance (>85%)
- ✅ Include working examples
- ✅ Have no stubs or placeholders
- ✅ Be immediately usable

---

**Note**: This skill automatically loads when Claude detects skill building intent. For explicit control, use `/amplihack:skill-builder`.
