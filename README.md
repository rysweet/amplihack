# Amplihack Bundle for Amplifier

A comprehensive Amplifier bundle that packages the amplihack development framework - systematic AI-powered development workflows with specialized agents, workflow orchestration, and philosophy-driven design.

## Features

- **12 Specialized Agents** for different aspects of development
- **4 Workflow Recipes** for systematic development processes
- **3 Essential Skills** for domain knowledge
- **Philosophy-Driven Context** for consistent design decisions

## Installation

```bash
# Use as a bundle in your Amplifier configuration
amplifier run --bundle git+https://github.com/rysweet/amplifier-amplihack@main
```

Or add to your project's bundle:

```yaml
# In your bundle.md frontmatter
includes:
  - bundle: git+https://github.com/rysweet/amplifier-amplihack@main
```

## What's Included

### Agents (12 unique to amplihack)

| Agent | Purpose |
|-------|---------|
| `amplihack:reviewer` | Code review specialist |
| `amplihack:tester` | Testing pyramid expert (60/30/10) |
| `amplihack:optimizer` | Performance optimization |
| `amplihack:api-designer` | API contract specialist |
| `amplihack:analyzer` | TRIAGE/DEEP/SYNTHESIS analysis modes |
| `amplihack:ambiguity` | Requirements clarification |
| `amplihack:documentation-writer` | Diataxis framework documentation |
| `amplihack:database` | Schema design expert |
| `amplihack:patterns` | Pattern recognition and emergence |
| `amplihack:diagnostics` | Pre-commit + CI failure resolver |
| `amplihack:worktree-manager` | Git worktree management |
| `amplihack:prompt-writer` | Prompt engineering specialist |

### Foundation Agents (Use via delegation)

The bundle composes with `amplifier-foundation`, giving you access to:
- `foundation:zen-architect` - System design
- `foundation:modular-builder` - Implementation
- `foundation:explorer` - Codebase exploration
- `foundation:bug-hunter` - Debugging
- `foundation:git-ops` - Git operations
- `foundation:security-guardian` - Security review

### Recipes (Workflows)

| Recipe | Purpose |
|--------|---------|
| `workflow-selector.yaml` | Auto-routes requests to correct workflow |
| `default-workflow.yaml` | Standard development workflow (22 steps) |
| `investigation-workflow.yaml` | Research and exploration |
| `qa-flow.yaml` | Simple Q&A (minimal overhead) |

### Skills

| Skill | Domain Knowledge |
|-------|------------------|
| `code-smell-detector` | Code quality anti-patterns |
| `design-patterns-expert` | GOF and architectural patterns |
| `test-gap-analyzer` | Test coverage analysis |

## Philosophy

Amplihack embodies:

1. **Ruthless Simplicity** - As simple as possible, but no simpler
2. **Brick Philosophy** - Self-contained, regeneratable modules
3. **Zero-BS Implementations** - No stubs, no placeholders, no TODOs
4. **Autonomous Execution** - Execute with quality, don't stop for approval

## Usage

### Automatic Workflow Selection

```
# Just describe what you need - the bundle auto-routes
"Add user authentication to the API"  → default-workflow
"How does the caching layer work?"    → investigation-workflow
"What's the database schema?"         → qa-flow
```

### Direct Workflow Invocation

```
# Run specific workflow via recipes tool
recipes: execute amplihack:recipes/default-workflow.yaml
  context:
    user_request: "Add caching to the data layer"
```

### Agent Delegation

```
# Amplihack agents for specialized tasks
Use amplihack:reviewer for code review
Use amplihack:diagnostics for build failures

# Foundation agents for core operations
Use foundation:git-ops for commits
Use foundation:zen-architect for design
```

## Bundle Structure

```
amplifier-amplihack/
├── bundle.md                 # Thin bundle entry point
├── behaviors/
│   └── amplihack.yaml        # Agent + context behavior
├── agents/                   # 12 specialized agents
├── context/
│   ├── philosophy.md         # Core philosophy
│   ├── instructions.md       # Operating instructions
│   └── source-workflows/     # Original workflow references
├── recipes/                  # 4 workflow recipes
├── skills/                   # 3 essential skills
└── docs/
    └── FEATURE_MAPPING.md    # Full feature mapping
```

## Comparison with Original Amplihack

| Feature | Original (Claude Code) | This Bundle (Amplifier) |
|---------|----------------------|------------------------|
| Agents | 35+ | 12 unique + foundation |
| Skills | 100+ | 3 essential |
| Workflows | 8 narrative | 4 recipe YAML |
| Commands | 25+ slash | Recipe invocation |
| Hooks | 5 Python | Foundation hooks |

The Amplifier version focuses on **ruthless simplicity** - keeping only what provides clear value while delegating to foundation for common capabilities.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the amplihack philosophy in all changes
4. Submit a PR

## License

MIT

## Related

- [amplifier](https://github.com/microsoft/amplifier) - The Amplifier framework
- [amplifier-foundation](https://github.com/microsoft/amplifier-foundation) - Foundation bundle
- [amplihack](https://github.com/rysweet/amplihack) - Original Claude Code framework
