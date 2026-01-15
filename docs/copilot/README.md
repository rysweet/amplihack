# GitHub Copilot CLI with amplihack

Complete documentation for using GitHub Copilot CLI with the amplihack agentic coding framework.

## Overview

amplihack provides a powerful agentic coding framework designed for Claude Code, now accessible through GitHub Copilot CLI. Get access to 37+ specialized agents, 14 foundational patterns, and philosophy-driven development principles.

## Documentation

### Getting Started

**[Getting Started Guide](./GETTING_STARTED.md)**

Quick start guide covering:
- Installation and prerequisites
- First session walkthrough
- Basic agent usage
- Quick wins with amplihack

Start here if ye're new to amplihack or Copilot CLI.

### Complete User Guide

**[Complete User Guide](./USER_GUIDE.md)**

Comprehensive guide covering:
- All 37+ agents with examples
- Command invocation patterns
- Skill usage and workflows
- MCP servers and auto mode
- Advanced features and best practices

Reference guide for all capabilities.

### Migration from Claude Code

**[Migration Guide](./MIGRATION_FROM_CLAUDE.md)**

For users switching from Claude Code:
- Feature parity matrix
- Pattern translations
- Workflow adaptations
- Maintaining dual environments

Learn how Claude Code and Copilot CLI compare.

### Troubleshooting

**[Troubleshooting Guide](./TROUBLESHOOTING.md)**

Solutions to common issues:
- Installation problems
- Agent invocation failures
- Context issues
- Performance optimization
- Debug techniques

Fix problems quickly with targeted solutions.

### Frequently Asked Questions

**[FAQ](./FAQ.md)**

Answers to common questions:
- When to use Claude vs Copilot?
- How does @ notation work?
- Can I use both simultaneously?
- Cost and performance comparisons
- Philosophy principles explained

Quick answers to frequent questions.

### API Reference

**[API Reference](./API_REFERENCE.md)**

Complete reference documentation:
- All CLI commands with examples
- Python API documentation
- Agent reference (37+ agents)
- Pattern reference (14 patterns)
- MCP server tools

Complete technical reference.

## Quick Links

### Essential Resources

- **amplihack repository:** https://github.com/rysweet/amplihack
- **Full documentation site:** https://rysweet.github.io/amplihack/
- **GitHub Discussions:** https://github.com/rysweet/amplihack/discussions
- **Issue tracker:** https://github.com/rysweet/amplihack/issues

### Core Context Files

After initializing amplihack in yer project:

```
.claude/context/
├── PHILOSOPHY.md              # Core development principles
├── PATTERNS.md                # 14 foundational patterns
├── TRUST.md                   # Anti-sycophancy guidelines
├── USER_PREFERENCES.md        # User customization
└── USER_REQUIREMENT_PRIORITY.md  # Priority hierarchy

.github/
├── copilot-instructions.md    # Copilot context
└── agents/                    # Converted agents (37+)
```

## Quick Start

### 1. Install

```bash
# Install Copilot CLI
npm install -g @github/copilot

# Install amplihack
pip install git+https://github.com/rysweet/amplihack

# Authenticate
gh auth login
```

### 2. Initialize Project

```bash
cd /path/to/your/project
amplihack init
amplihack convert-agents
```

### 3. Launch

```bash
amplihack copilot
```

### 4. Use Agents

```
> @architect: Design authentication module following amplihack philosophy
> @builder: Implement the module from architect's spec
> @tester: Generate comprehensive tests
> @reviewer: Check philosophy compliance
```

## Key Concepts

### Philosophy

amplihack follows three core principles:

1. **Ruthless Simplicity** - Start simple, add complexity only when justified
2. **Brick Philosophy** - Modular design with clear interfaces
3. **Zero-BS Implementation** - Every function works or doesn't exist

### Agents

37+ specialized agents for different tasks:

- **Core agents** (6): architect, builder, reviewer, tester, api-designer, optimizer
- **Specialized agents** (31+): security, database, cleanup, patterns, integration, analyzer, and more

### Patterns

14 foundational patterns for common problems:

- Bricks & Studs Module Design
- Zero-BS Implementation
- API Validation Before Implementation
- Safe Subprocess Wrapper
- Fail-Fast Prerequisite Checking
- And 9 more proven patterns

### Workflows

Reference-based workflow execution:

- DEFAULT_WORKFLOW (22 steps)
- Document-Driven Development (DDD)
- Investigation Workflow
- Fault Tolerance Patterns

## Comparison: Claude Code vs Copilot CLI

| Feature                | Claude Code          | Copilot CLI              |
| ---------------------- | -------------------- | ------------------------ |
| **Command Execution**  | Direct (/ultrathink) | Reference-based          |
| **Agent Invocation**   | Native Task tool     | @ notation               |
| **Cost Model**         | API usage            | Subscription             |
| **Model**              | Claude Opus/Sonnet   | GPT-4 variants           |
| **Philosophy Access**  | ✓ Full               | ✓ Full                   |
| **Pattern Library**    | ✓ Full               | ✓ Full                   |
| **Python Tools**       | ✓ All                | ✓ All                    |

**Recommendation:** Use both! They access the same resources and complement each other.

## Common Use Cases

### Design a Module

```
> Following amplihack brick philosophy, @architect: Design a rate limiting
  module with clear public API and single responsibility
```

### Implement from Spec

```
> Following Zero-BS implementation principles, @builder: Implement the rate
  limiting module from architect's spec with no stubs or placeholders
```

### Review Code

```
> @reviewer: Check this PR for amplihack philosophy compliance:
  - Ruthless simplicity
  - Modular design (bricks & studs)
  - Zero-BS implementation
  - Pattern usage
```

### Generate Tests

```
> Following TDD pyramid (60/30/10), @tester: Generate comprehensive tests for
  the rate limiting module including edge cases
```

### Apply Patterns

```
> Using the Safe Subprocess Wrapper pattern from PATTERNS.md, handle git
  commands with proper error handling and user-friendly messages
```

### Security Audit

```
> @security: Audit this authentication module for vulnerabilities including:
  - Input validation
  - Token handling
  - Session management
  - Error information leakage
```

## Advanced Features

### Fault Tolerance Patterns

- **N-Version Programming** - Generate multiple solutions, select best
- **Multi-Agent Debate** - Structured debate for complex decisions
- **Fallback Cascade** - Graceful degradation for resilience

### Document-Driven Development

Documentation-first methodology for large features:

1. Plan and align
2. Write documentation (retcon)
3. Manual approval gate
4. Implement code matching docs
5. Test and cleanup

### Investigation Workflow

Deep knowledge excavation for understanding codebases:

1. Clarify scope
2. Discover structure
3. Deep dive analysis
4. Verify understanding
5. Synthesize findings
6. Generate documentation

## Support

### Documentation

- **Getting Started:** [GETTING_STARTED.md](./GETTING_STARTED.md)
- **User Guide:** [USER_GUIDE.md](./USER_GUIDE.md)
- **Migration:** [MIGRATION_FROM_CLAUDE.md](./MIGRATION_FROM_CLAUDE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **FAQ:** [FAQ.md](./FAQ.md)
- **API Reference:** [API_REFERENCE.md](./API_REFERENCE.md)

### Community

- **Discussions:** https://github.com/rysweet/amplihack/discussions
- **Issues:** https://github.com/rysweet/amplihack/issues
- **Documentation:** https://rysweet.github.io/amplihack/

### In-Session Help

```
> How do I use amplihack agents?
> Show me available amplihack patterns
> What is the brick philosophy?
> Which agent should I use for [task]?
```

## Contributing

Contributions welcome! See main repository for contribution guidelines.

## License

Same license as main amplihack project.

---

**Happy coding with Copilot CLI and amplihack!** 🚀
