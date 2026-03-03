---
name: skill-builder
description: Creates, refines, and validates Agent Skills following the open standard at agentskills.io, Claude Code extensions, and Anthropic best practices. Use when building, creating, generating, or designing new skills.
metadata:
  version: "2.0"
  author: amplihack
---

# Skill Builder

## Purpose

Creates production-ready Agent Skills following the official specifications
and best practices.

## When I Activate

I automatically load when you mention:

- "build a skill" or "create a skill"
- "generate a skill" or "make a skill"
- "design a skill" or "new skill"

## Authoritative References (Read These First)

Before creating any skill, read the current versions of these docs:

1. **Agent Skills Specification** (the open standard):
   https://agentskills.io/specification
2. **Skill Authoring Best Practices** (Anthropic):
   https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
3. **Claude Code Skills Documentation** (Claude Code extensions):
   https://docs.claude.com/en/docs/claude-code/skills
4. **Example Skills** (reference implementations):
   https://github.com/anthropics/skills

These are the source of truth. If anything in this skill contradicts those
docs, the official docs win.

## What I Do

Create skills in 5 steps:

1. **Clarify** → Define purpose, scope, activation keywords
2. **Design** → Plan structure, decide on progressive disclosure
3. **Generate** → Create SKILL.md with proper frontmatter and body
4. **Validate** → Check against spec and best practices
5. **Test** → Verify activation and behavior

## Frontmatter (Agent Skills Spec)

Only two fields are required:

```yaml
---
name: my-skill
description: What this skill does and when to use it. Include specific keywords for discovery.
---
```

Optional fields: `license`, `compatibility`, `metadata`, `allowed-tools`.

Claude Code adds: `disable-model-invocation`, `user-invocable`, `model`,
`context`, `agent`, `hooks`, `argument-hint`.

**Do NOT use**: `version` (use `metadata.version`), `auto_activates`,
`priority_score`, `source_urls`, `evaluation_criteria`, `invokes`,
`philosophy`, `maturity` — none of these are recognized by any runtime.

## Key Best Practices

From the [official best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices):

### Conciseness

- Claude is already smart. Only add context it doesn't have.
- Challenge every paragraph: "Does this justify its token cost?"
- SKILL.md body under 500 lines.

### Description Quality

- Write in **third person** ("Processes Excel files", not "I help you")
- Include both what the skill does AND when to use it
- Include specific trigger keywords for discovery
- Max 1024 characters

### Progressive Disclosure

- Metadata loaded at startup (name + description only)
- SKILL.md loaded when skill activates
- Supporting files loaded only when needed
- Keep references **one level deep** from SKILL.md

### Degrees of Freedom

- **High freedom**: Multiple valid approaches, context-dependent
- **Medium freedom**: Preferred pattern exists, some variation OK
- **Low freedom**: Fragile operations, exact sequence required

### No Time-Sensitive Content

- Never write "as of today", "recently added", "new in v3.0"
- Use an "old patterns" section for historical context if needed

### Feedback Loops

- Run validator → fix errors → repeat
- Include verification steps for critical operations

## Validation Checklist

✅ **Frontmatter**: `name` and `description` present and valid
✅ **Name**: Lowercase, hyphens only, 1-64 chars, matches directory name
✅ **Description**: 1-1024 chars, third person, includes trigger keywords
✅ **Body**: Under 500 lines
✅ **References**: One level deep from SKILL.md
✅ **No stale content**: No temporal references
✅ **Consistent terminology**: One term per concept throughout
✅ **Tested**: Works with at least 3 representative prompts

## Supporting Files

- [reference.md](./reference.md): Detailed patterns, architecture, validation rules
- [examples.md](./examples.md): Skill creation workflows and examples
