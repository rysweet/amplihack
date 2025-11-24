# amplihack

**Agentic coding framework that uses specialized AI agents to accelerate software development through intelligent automation and collaborative problem-solving.**

## What is amplihack?

amplihack is a development tool built on Claude Code that leverages multiple specialized AI agents working together to handle complex software development tasks. It combines ruthless simplicity with powerful capabilities to make AI-assisted development more effective and maintainable.

## Key Features

### 🤖 Specialized AI Agents

Deploy purpose-built agents for different aspects of development:

- **Core Agents**: Architect, Builder, Reviewer, Tester
- **Specialized Agents**: API Designer, Security, Database, Integration
- **Workflow Agents**: Ambiguity Handler, Cleanup, Optimizer, Pattern Recognition

### 📋 Structured Workflows

Follow proven methodologies for consistent results:

- **Default Workflow**: 13-step process for feature development
- **Document-Driven Development (DDD)**: Documentation-first approach for large features
- **N-Version Programming**: Generate multiple solutions for critical code
- **Multi-Agent Debate**: Structured debates for complex decisions
- **Investigation Workflow**: Deep knowledge excavation for understanding codebases

### 🎯 Quality & Productivity Features

Built-in features to prevent mistakes and improve workflow:

- **Power-Steering Mode**: Intelligent session completion verification that prevents premature work termination by checking 21 considerations

### ⚡ Powerful Commands

Execute complex tasks with simple slash commands:

- `/ultrathink` - Orchestrate multiple agents following the default workflow
- `/analyze` - Comprehensive code review for philosophy compliance
- `/improve` - Capture learnings and self-improvement
- `/fix` - Intelligent fix workflow for common error patterns
- `/ddd:*` - Document-driven development workflow commands

### 🧱 Modular Design Philosophy

Built on the "Bricks & Studs" principle:

- **Self-contained modules** with clear responsibilities
- **Public contracts** others can connect to
- **Regeneratable** from specifications
- **Zero-BS implementation** - no stubs or placeholders

## Quick Links

### Get Started

- [Installation Guide](PREREQUISITES.md) - Set up amplihack
- [Interactive Setup](INTERACTIVE_INSTALLATION.md) - Step-by-step installation
- [Quick Start](README.md) - Basic usage and examples

### Core Concepts

- [Philosophy](/.claude/context/PHILOSOPHY.md) - Design principles and values
- [Project Overview](/.claude/context/PROJECT.md) - Architecture and structure
- [Patterns](/.claude/context/PATTERNS.md) - Common implementation patterns
- [Trust & Anti-Sycophancy](/.claude/context/TRUST.md) - Critical operating guidelines

### Workflows

- [Default Workflow](/.claude/workflow/DEFAULT_WORKFLOW.md) - Standard 13-step process
- [Document-Driven Development](/document_driven_development/README.md) - Documentation-first approach
- [Investigation Workflow](/.claude/workflow/INVESTIGATION_WORKFLOW.md) - Deep codebase analysis

### Agents

- [Agents Overview](/.claude/agents/amplihack/README.md) - All available agents
- [Architect](/.claude/agents/amplihack/core/architect.md) - System design and specifications
- [Builder](/.claude/agents/amplihack/core/builder.md) - Code implementation
- [Reviewer](/.claude/agents/amplihack/core/reviewer.md) - Quality assurance

### Commands

- [Command Guide](/commands/COMMAND_SELECTION_GUIDE.md) - Choose the right command
- [/ultrathink](/.claude/commands/amplihack/ultrathink.md) - Main orchestration command
- [/ddd:\* commands](/.claude/commands/ddd/0-help.md) - Document-driven development

### Features

- [Power-Steering Mode](/features/power-steering/README.md) - Session completion verification
- [Customization Guide](/features/power-steering/customization-guide.md) - Configure power-steering

## Philosophy

amplihack follows three core principles:

1. **Ruthless Simplicity**: Start with the simplest solution that works. Add complexity only when justified.

2. **Modular Design**: Build self-contained modules (bricks) with clear public contracts (studs) that others can connect to.

3. **Zero-BS Implementation**: No stubs, no placeholders, no dead code. Every function must work or not exist.

## Use Cases

amplihack excels at:

- **Feature Development**: Orchestrate multiple agents to design, implement, test, and document new features
- **Code Review**: Comprehensive analysis for philosophy compliance and best practices
- **Refactoring**: Systematic cleanup and improvement of existing code
- **Investigation**: Deep understanding of complex codebases and architectures
- **Integration**: Connect external services with proper error handling and testing
- **Security**: Vulnerability assessment and secure implementation patterns

## Example Workflow

```bash
# Start with a feature request
/ultrathink "Add user authentication to the API"

# UltraThink will:
# 1. Read the default workflow
# 2. Orchestrate multiple agents (architect, security, api-designer, database, builder, tester)
# 3. Follow all 13 steps systematically
# 4. Ensure quality and philosophy compliance
# 5. Generate tests and documentation
```

## Community

- **GitHub**: [amplihack/amplihack](https://github.com/amplihack/amplihack)
- **Documentation**: [amplihack.github.io/amplihack](https://amplihack.github.io/amplihack/)
- **Issues**: [Report bugs or request features](https://github.com/amplihack/amplihack/issues)

## License

amplihack is open source software. See the LICENSE file for details.

---

**Ready to get started?** Head to the [Installation Guide](PREREQUISITES.md) to set up amplihack in your development environment.
