# Claude Code Skills for Amplihack

This directory contains production-ready Claude Code Skills that extend amplihack's capabilities across coding, creative work, and knowledge management.

## 📚 About Claude Code Skills

Claude Code Skills are modular, reusable capabilities that extend Claude's functionality. They consist of folders containing a `SKILL.md` file with YAML frontmatter and Markdown instructions, along with optional supporting scripts and resources.

**Key Benefits:**

- **Token Efficient**: Skills load on-demand, consuming minimal tokens until needed
- **Auto-Detection**: Claude automatically uses skills based on context
- **Philosophy Aligned**: All skills follow amplihack's ruthless simplicity and modular design
- **Portable**: Work across Claude.ai, API, and Claude Code environments
- **Self-Contained**: Each skill is independently usable and testable

## 🎯 Skill Types

Amplihack has **TWO types of skills** that work together:

### Type 1: Capability Skills (13 skills)

**Purpose**: Provide specific new functionality for tasks beyond coding.

These skills add NEW capabilities like decision recording, email drafting, meeting synthesis, etc. They don't wrap existing agents - they provide genuinely new functionality.

| Skill                         | Score | Description                                                                        | Issue                                                                                | PR                                                                                 |
| ----------------------------- | ----- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **module-spec-generator**     | 50.0  | Generate brick module specifications                                               | [#1219](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1219) | -                                                                                  |
| **meeting-synthesizer**       | 50.0  | Extract action items and decisions from meetings                                   | [#1220](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1220) | [#1231](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1231) |
| **decision-logger**           | 49.5  | Structured decision recording (What\|Why\|Alternatives)                            | [#1221](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1221) | [#1231](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1231) |
| **mermaid-diagram-generator** | 48.0  | Converts descriptions to Mermaid diagrams                                          | [#1222](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1222) | [#1268](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1268) |
| **email-drafter**             | 47.0  | Professional email generation (formal/casual/technical)                            | [#1223](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1223) | [#1232](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1232) |
| **philosophy-guardian**       | 45.5  | Reviews code against amplihack philosophy                                          | [#1224](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1224) | [#1235](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1235) |
| **test-gap-analyzer**         | 44.5  | Identifies untested functions and coverage gaps                                    | [#1225](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1225) | [#1233](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1233) |
| **storytelling-synthesizer**  | 44.0  | Transforms technical work into compelling narratives                               | [#1226](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1226) | [#1236](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1236) |
| **learning-path-builder**     | 43.5  | Creates personalized technology learning paths                                     | [#1227](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1227) | [#1237](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1237) |
| **code-smell-detector**       | 42.5  | Detects anti-patterns and over-engineering                                         | [#1228](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1228) | [#1234](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1234) |
| **knowledge-extractor**       | 40.5  | Extracts learnings to DISCOVERIES.md and PATTERNS.md                               | [#1229](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1229) | [#1238](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1238) |
| **pr-review-assistant**       | 40.0  | Philosophy-aware PR reviews                                                        | [#1230](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1230) | [#1258](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1258) |
| **context-management**        | 48.5  | Proactive context window management via token monitoring and intelligent snapshots | [#1347](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1347) | -                                                                                  |

### Type 2: Domain Expert Analyst Skills (23 skills) 🆕

**Purpose**: Analyze events through specialized disciplinary lenses using rigorous academic frameworks.

These skills provide deep domain expertise for multi-perspective analysis of events, policies, and phenomena. Each analyst applies discipline-specific theories, methods, and evidence.

**Social Sciences** (5):

- **economist-analyst** - Markets, incentives, supply/demand, policy analysis
- **political-scientist-analyst** - Power, institutions, IR theory, comparative politics
- **historian-analyst** - Causation, continuity/change, historical context, precedents
- **sociologist-analyst** - Social structures, inequality, collective behavior
- **anthropologist-analyst** - Cultural analysis, ethnography, cross-cultural comparison

**Humanities & Communication** (4):

- **novelist-analyst** - Narrative structure, character development, dramatic tension
- **journalist-analyst** - Investigation, verification, 5Ws+H, fact-checking
- **poet-analyst** - Metaphor, imagery, close reading, emotional truth
- **futurist-analyst** - Scenario planning, trend analysis, strategic foresight

**Natural Sciences** (5):

- **physicist-analyst** - Physical principles, conservation laws, modeling
- **chemist-analyst** - Molecular structure, reactions, synthesis planning
- **psychologist-analyst** - Cognition, behavior, social influence, neuroscience
- **environmentalist-analyst** - Ecosystems, climate, sustainability, biodiversity
- **biologist-analyst** - Evolution, genetics, ecology, systems biology

**Applied Fields** (6):

- **computer-scientist-analyst** - Algorithms, complexity, systems design
- **cybersecurity-analyst** - Threat modeling, defense, incident response
- **lawyer-analyst** - Legal analysis, IRAC, statutory interpretation
- **indigenous-leader-analyst** - Traditional knowledge, Seven Generations, Two-Eyed Seeing
- **engineer-analyst** - Systems analysis, optimization, failure analysis, trade-offs
- **urban-planner-analyst** - Land use, zoning, transportation, housing, sustainability

**Philosophy & Ethics** (3):

- **ethicist-analyst** - Moral frameworks, value conflicts, normative analysis
- **philosopher-analyst** - Logic, epistemology, metaphysics, conceptual analysis
- **epidemiologist-analyst** - Disease patterns, public health, outbreak investigation

**Key Features**:

- All 23 analysts have comprehensive test suites (tests/quiz.md with 5 scenarios each)
- Domain-specific search capability (see ANALYST_SEARCH_CAPABILITY.md)
- Progressive disclosure structure (SKILL.md + README.md + QUICK_REFERENCE.md)
- 100+ scholarly sources preserved across all agents
- Consistent 16-section template pattern
- PR: [#1346](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1346)

### Type 3: Agent-Wrapper Skills (7 skills)

**Purpose**: Auto-detect when to invoke existing agents, reducing need to remember command names.

These skills are thin coordination layers that automatically trigger amplihack's existing agents based on conversation context.

| Skill                         | Auto-Triggers                                              | Invokes                        | Location                                                                       |
| ----------------------------- | ---------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------ |
| **Architecting Solutions**    | Design questions, "how should I", architecture discussions | Architect agent                | [development/architecting-solutions/](development/architecting-solutions/)     |
| **Reviewing Code**            | "review this", before PR, quality checks                   | Reviewer agent                 | [quality/reviewing-code/](quality/reviewing-code/)                             |
| **Testing Code**              | New features, "add tests", test gaps                       | Tester agent                   | [quality/testing-code/](quality/testing-code/)                                 |
| **Researching Topics**        | "how does X work", unfamiliar terms                        | Web search + knowledge builder | [research/researching-topics/](research/researching-topics/)                   |
| **Analyzing Problems Deeply** | Complex problems, "I'm not sure", ambiguity                | Ultrathink workflow            | [meta-cognitive/analyzing-deeply/](meta-cognitive/analyzing-deeply/)           |
| **Setting Up Projects**       | New projects, missing configs, pre-commit setup            | Builder agent + templates      | [development/setting-up-projects/](development/setting-up-projects/)           |
| **Creating Pull Requests**    | "create PR", ready to merge                                | Smart PR generation            | [collaboration/creating-pull-requests/](collaboration/creating-pull-requests/) |

## 📖 Research & Documentation

### Research Reports

- **[Complete Research Report](../runtime/logs/20251108_skills_research/RESEARCH.md)** (357 lines)
  - Comprehensive analysis of Claude Code Skills ecosystem
  - Comparison with MCP (Model Context Protocol)
  - 23+ documented skills from Anthropic and community
  - Key insights from Simon Willison and other experts

- **[Evaluation Matrix & Ideas](../runtime/logs/20251108_skills_research/EVALUATION_MATRIX_AND_IDEAS.md)** (842 lines)
  - 6-criteria evaluation framework aligned with amplihack philosophy
  - 20 brainstormed skill ideas with priority scores
  - Implementation phases and effort estimates
  - Detailed scoring rubrics

### Evaluation Criteria (Capability Skills)

Capability skills were evaluated on:

1. **Ruthless Simplicity** (1-5): Single clear purpose, minimal dependencies
2. **Modular Design** (1-5): Self-contained, clear interfaces (bricks & studs)
3. **Zero-BS Implementation** (1-5): Actually works, no stubs
4. **Reusability** (1-5): Useful across multiple contexts
5. **Maintenance Burden** (1-5, lower is better): Stable dependencies
6. **User Value** (1-5): Solves frequent pain points, measurable time savings

**Priority Score Formula:**

```
Priority = (Simplicity * 2) + (Modular * 2) + (Zero-BS * 1.5) +
           (Reusability * 1.5) + ((6 - Maintenance) * 1) + (User Value * 2.5)
Max Score: 50 points
```

All 12 capability skills scored 40.0-50.0 (HIGH priority).

## 🔍 Using Skills

Skills are automatically discovered from:

- User settings: `~/.config/claude/skills/`
- Project settings: `.claude/skills/`
- Plugin-provided skills
- Built-in skills

### Invoking Skills

**Capability Skills** (explicit invocation):

```
Claude, use the decision-logger skill to record this architectural decision.
Claude, analyze test coverage using test-gap-analyzer.
Claude, generate a Mermaid diagram for this workflow.
```

**Agent-Wrapper Skills** (automatic detection):

```
User: "How should I design the authentication system?"
→ Architecting Solutions skill auto-activates
→ Provides design analysis automatically

User: "Can you review this code?"
→ Reviewing Code skill auto-activates
→ Performs comprehensive review
```

### Managing Skills

```bash
/agents                # List available agents and skills
/reload-skills         # Reload after modifications
```

## 🏗️ Skill Structure

Each skill follows this structure:

```
skill-name/
├── SKILL.md           # Required: YAML frontmatter + instructions
├── README.md          # Optional: User-facing documentation
├── examples/          # Optional: Example usage
└── tests/             # Optional: Validation tests
```

### SKILL.md Format

```yaml
---
name: skill-name
description: |
  Clear description of what this skill does and when Claude should use it.
  Include both the capability AND the usage context.
---

# Skill Instructions

Detailed instructions for Claude on how to use this skill...

## Examples
Concrete examples with input/output...
```

## 📊 Quality Standards

All skills meet these quality standards:

- ✅ **Complete Documentation**: SKILL.md with YAML frontmatter
- ✅ **Clear Examples**: Real-world usage demonstrations
- ✅ **Philosophy Aligned**: Ruthless simplicity, modular design, zero-BS
- ✅ **Tested**: Quality review completed
- ✅ **Production Ready**: No stubs, TODOs, or placeholders

## 🚀 Creating New Skills

### For Capability Skills

To create a new capability skill:

1. **Research**: Check if similar skills exist
2. **Evaluate**: Score against 6 criteria (target score: 40+)
3. **Create**: Follow skill structure above
4. **Document**: Clear SKILL.md with examples
5. **Test**: Validate with real usage
6. **Review**: Ensure philosophy compliance

See [Evaluation Matrix](../runtime/logs/20251108_skills_research/EVALUATION_MATRIX_AND_IDEAS.md) for guidance on prioritization.

### For Agent-Wrapper Skills

To create an agent-wrapper skill:

1. **Identify Pattern**: Find repetitive agent invocations
2. **Define Triggers**: What phrases/contexts should activate this?
3. **Create Thin Wrapper**: Just detection logic + agent invocation
4. **No Logic Duplication**: All real work stays in agents
5. **Test Auto-Detection**: Verify skill activates appropriately

## 📚 Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Project overview and agent system
- [PHILOSOPHY.md](../context/PHILOSOPHY.md) - Ruthless simplicity principles
- [PATTERNS.md](../context/PATTERNS.md) - Reusable solution patterns
- [Agent Catalog](../agents/CATALOG.md) - Specialized agents

## 🤝 Contributing

When adding new skills:

1. Determine skill type (capability vs. agent-wrapper)
2. Create GitHub issue with rationale
3. Implement in separate worktree/branch
4. Follow naming: `feat/issue-{number}-{skill-name}`
5. Create PR with comprehensive description
6. Link to research and evaluation docs (if capability skill)
7. Ensure quality review completed

---

**Last Updated**: November 10, 2025
**Total Skills**: 19 (12 capability + 7 agent-wrapper)
**Status**: Production Ready

🤖 Skills documentation maintained as part of amplihack project
