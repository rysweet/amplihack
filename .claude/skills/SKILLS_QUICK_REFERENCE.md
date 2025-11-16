# Skills Quick Reference

Fast lookup for all amplihack Skills, their triggers, and what they do.

## Development Workflow

### Architecting Solutions

**Triggers**: "how should I", "what's the best way", design questions, architecture discussions
**Does**: Analyzes problems, creates design specs, provides solution options with tradeoffs
**Invokes**: Architect agent
**Status**: ✅ Implemented

### Setting Up Projects

**Triggers**: New project, missing configs, "setup project", pre-commit gaps
**Does**: Creates project structure, configs, pre-commit hooks, quality tooling
**Invokes**: Builder agent + templates
**Status**: ✅ Implemented

### Debugging Issues

**Triggers**: Errors, "why doesn't", "not working", troubleshooting
**Does**: Systematic diagnostic approach, identifies likely causes, suggests fixes
**Invokes**: Debugging workflow
**Status**: ⏳ Planned (Phase 2)

---

## Code Quality

### Reviewing Code

**Triggers**: "review this", "check my code", before PR, quality checks
**Does**: Multi-level code review (correctness, security, maintainability)
**Invokes**: Reviewer agent, Security agent
**Status**: ✅ Implemented

### Testing Code

**Triggers**: New features, "add tests", missing coverage, test gaps
**Does**: Generates comprehensive tests (unit, integration, edge cases)
**Invokes**: Tester agent
**Status**: ✅ Implemented

### Securing Code

**Triggers**: Auth code, secrets, validation, "security check"
**Does**: Security analysis, vulnerability detection, OWASP compliance
**Invokes**: Security agent
**Status**: ⏳ Planned (Phase 2)

---

## Research & Learning

### Researching Topics

**Triggers**: "how does X work", "what is Y", unfamiliar terms, need info
**Does**: Quick web research, synthesis, key concepts, actionable summary
**Invokes**: WebSearch + synthesis
**Escalates**: /knowledge-builder for deep dive
**Status**: ✅ Implemented

### Explaining Concepts

**Triggers**: "explain", "what is", "how does", learning requests
**Does**: Progressive explanations, ELI5 to deep dive, builds mental models
**Invokes**: Teaching methodology
**Status**: ⏳ Planned (Phase 3)

### Building Knowledge

**Triggers**: Documentation tasks, "document this", knowledge gaps
**Does**: Quick documentation generation (lighter than /knowledge-builder)
**Invokes**: Simplified knowledge-builder workflow
**Escalates**: /knowledge-builder for comprehensive research
**Status**: ⏳ Planned (Phase 3)

---

## Meta-Cognitive

### Analyzing Problems Deeply

**Triggers**: "I'm not sure", "help me think", ambiguity, complex problems
**Does**: Structured deep analysis, surfaces assumptions, explores options
**Invokes**: Ultrathink methodology
**Status**: ✅ Implemented

### Evaluating Tradeoffs

**Triggers**: "should I use X or Y", "which approach", decision points
**Does**: Multi-perspective tradeoff analysis, systematic comparison
**Invokes**: Consensus/debate workflow
**Status**: ⏳ Planned (Phase 3)

---

## Collaboration

### Creating Pull Requests

**Triggers**: "create PR", "ready to merge", "make pull request"
**Does**: Analyzes commits, generates comprehensive PR description, creates PR
**Invokes**: Git analysis + gh CLI
**Status**: ✅ Implemented

### Writing RFCs

**Triggers**: "design doc", "RFC", major architectural changes
**Does**: Structured RFC creation with template, architecture documentation
**Invokes**: RFC template + Architect agent
**Status**: ⏳ Planned (Phase 3)

---

## Quick Comparison: Skills vs Slash Commands

| Situation        | Use Skill (Auto)       | Use Command (Explicit)             |
| ---------------- | ---------------------- | ---------------------------------- |
| Design question  | Architecting Solutions | /ultrathink (deeper)               |
| Quick research   | Researching Topics     | /knowledge-builder (comprehensive) |
| Code review      | Reviewing Code         | /review --custom-rules             |
| Need tests       | Testing Code           | Manual test writing                |
| Create PR        | Creating Pull Requests | Manual PR creation                 |
| Complex decision | Analyzing Deeply       | /consensus (multi-stakeholder)     |

## Activation Examples

### Example 1: Architecture

```
You: "I'm building a chat app. Should I use WebSockets or polling?"

Auto-Activates: Architecting Solutions skill
Provides: Problem analysis, solution options (WebSockets, long-polling, SSE),
          tradeoff analysis, recommendation with justification
```

### Example 2: Research

```
You: "What's the difference between JWT and session tokens?"

Auto-Activates: Researching Topics skill
Provides: Quick overview, key differences, security implications,
          use case recommendations
Suggests: /knowledge-builder for deep dive
```

### Example 3: Code Review

```
You: "Review this authentication code before I commit."

Auto-Activates: Reviewing Code skill
Provides: Security analysis, finds timing attack vulnerability,
          suggests fixes, checks test coverage
```

### Example 4: Deep Analysis

```
You: "I'm not sure whether to use PostgreSQL or MongoDB."

Auto-Activates: Analyzing Problems Deeply skill
Provides: Problem decomposition, multi-perspective analysis,
          assumption surfacing, tradeoff matrix, clear recommendation
```

## When Skills Don't Activate

If a skill doesn't activate when you expect:

1. **Be more explicit**: "Design this architecture" vs "I need to build X"
2. **Use trigger phrases**: Check skill's "When to Activate" section
3. **Use slash command**: Explicit control when auto-detection misses
4. **File issue**: Help improve trigger matching

## Disabling Skills

If you prefer manual control:

**Per-Task**: Ignore skill activation and proceed with manual approach
**Per-Project**: Create `.claude/config` with `skills: disabled`
**Permanently**: User settings in `~/.claude/config`

## Status Legend

- ✅ **Implemented**: Complete SKILL.md, ready to use
- 🚧 **In Progress**: Being developed
- ⏳ **Planned**: Designed, not yet implemented
- 💡 **Proposed**: Under consideration

## Implementation Timeline

**Phase 1** (Weeks 1-2): Foundation

- ✅ Architecting Solutions
- ✅ Reviewing Code
- ✅ Researching Topics
- ✅ Setting Up Projects

**Phase 2** (Weeks 3-4): Quality & Depth

- ✅ Testing Code
- ✅ Analyzing Problems Deeply
- ⏳ Securing Code
- ⏳ Debugging Issues

**Phase 3** (Weeks 5-6): Collaboration

- ✅ Creating Pull Requests
- ⏳ Explaining Concepts
- ⏳ Evaluating Tradeoffs
- ⏳ Writing RFCs

## Getting Help

- **Skill Details**: See individual SKILL.md files
- **Architecture**: See `Specs/SkillsIntegration.md`
- **Roadmap**: See `Specs/SkillsImplementationRoadmap.md`
- **Summary**: See `Specs/SkillsIntegrationSummary.md`
- **Catalog**: See `.claude/skills/README.md`

## Skill Categories

```
12 Total Skills
├── Development (4): Architecture, Setup, Debugging, PRs
├── Quality (3): Review, Testing, Security
├── Research (3): Research, Explain, Document
└── Meta (2): Deep Analysis, Tradeoffs

7 Implemented ✅
5 Planned ⏳
```

---

**Pro Tip**: Skills work best when you describe what you're trying to do in natural language. Don't try to "trigger" skills - just explain your needs and let them activate automatically.

**Remember**: Skills complement, not replace, slash commands. Use whichever is most natural for your workflow.
