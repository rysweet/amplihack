# amplihack

Development framework for Claude Code, GitHub Copilot CLI, and Microsoft
Amplifier. Adds structured workflows, persistent memory, specialized agents,
goal-seeking capabilities, autonomous execution, and continuous improvement for
systematic software engineering.

**📚 [View Full Documentation](https://rysweet.github.io/amplihack/)**

```sh
# Quick start
uvx --from git+https://github.com/rysweet/amplihack amplihack claude
```

## Table of Contents

- [Why amplihack?](#why-amplihack)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Feature Catalog](#feature-catalog)
- [Configuration](#configuration)
- [Documentation Navigator](#documentation-navigator)
- [Development](#development)
- [RustyClawd Integration](#rustyclawd-integration)
- [License](#license)

## Why amplihack?

**The Problem**: Claude Code and GitHub Copilot CLI are barebones development
tools. They provide a chat interface and model access, but no engineering system
for managing complexity, maintaining consistency, or shipping reliable code at
scale.

**The Solution**: amplihack builds the engineering system around your coding
agent:

- **Structured workflows** replace ad-hoc prompting (DEFAULT_WORKFLOW.md defines
  22 systematic steps)
- **Specialized agents** handle architecture, building, testing, and review with
  defined responsibilities
- **Persistent memory** across sessions with knowledge graphs and discoveries
- **Quality gates** enforce philosophy compliance, test coverage, and code
  standards
- **Self-improvement** through reflection, pattern capture, and continuous
  learning

**The Benefit**: Systematic workflows and quality gates produce consistent,
high-quality code.

## Quick Start

### Prerequisites

- **Platform**: macOS, Linux, or WSL (Windows not directly supported)
- **Runtime**: Python 3.12+, Node.js 18+
- **Tools**: git, npm, uv ([astral.sh/uv](https://docs.astral.sh/uv/))
- **Optional**: GitHub CLI (`gh`), Azure CLI (`az`)

Detailed setup:
[docs/PREREQUISITES.md](https://rysweet.github.io/amplihack/PREREQUISITES/)

### Installation

**Option 1: Zero-Install** (try before you commit)

```bash
# Launch with Claude Code
uvx --from git+https://github.com/rysweet/amplihack amplihack claude

# Launch with Microsoft Amplifier
uvx --from git+https://github.com/rysweet/amplihack amplihack amplifier

# Launch with GitHub Copilot
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot
```

**Option 2: Global Install** (for daily use)

```bash
# Install once
uv tool install git+https://github.com/rysweet/amplihack

# Use directly
amplihack claude
amplihack amplifier
amplihack copilot

# Update later
uv tool upgrade amplihack
```

**Alias for convenience**:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias amplihack='uvx --from git+https://github.com/rysweet/amplihack amplihack'

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

### First Session

After launching:

```
# New users - interactive tutorial (60-90 minutes)
Task(subagent_type='guide', prompt='I am new to amplihack. Teach me the basics.')

# Experienced users - start coding
cd /path/to/my/project
[Your prompt here - automatically uses /amplihack:ultrathink workflow]
```

All prompts automatically invoke systematic workflow orchestration. Use
`--no-ultrathink` flag for simple tasks.

## Core Concepts

### Philosophy

- **Ruthless Simplicity**: Start simple, add complexity only when justified
- **Modular Design**: Self-contained modules ("bricks") with clear interfaces
  ("studs")
- **Zero-BS Implementation**: Every function works or doesn't exist (no stubs,
  TODOs, or placeholders)
- **Test-Driven**: Tests before implementation, behavior verification at module
  boundaries

Philosophy guide:
[`~/.amplihack/.claude/context/PHILOSOPHY.md`](~/.amplihack/.claude/context/PHILOSOPHY.md)

### Workflows

All work flows through structured workflows that detect user intent and guide
execution:

- **DEFAULT_WORKFLOW**: 22-step systematic development process (features, bugs,
  refactoring)
- **INVESTIGATION_WORKFLOW**: 6-phase knowledge excavation (understanding
  existing systems)
- **Q&A_WORKFLOW**: 3-step minimal workflow (simple questions, quick answers)
- **OPS_WORKFLOW**: 1-step administrative operations (cleanup, maintenance)

Workflows are customizable - edit
`~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` to change process.

Workflow customization:
[docs/WORKFLOW_COMPLETION.md](https://rysweet.github.io/amplihack/WORKFLOW_COMPLETION/)

## Feature Catalog

### Orchestration & Execution

- **[Workflow Orchestration](#workflows)** - Systematic multi-step workflows for
  development, investigation, and operations
- **[UltraThink](/amplihack:ultrathink)** - Deep multi-agent analysis and
  workflow execution (default for all prompts)
- **[Recipe Runner](docs/recipes/README.md)** - Code-enforced workflows that
  models cannot skip (10 bundled recipes)
- **[Auto Mode](https://rysweet.github.io/amplihack/AUTO_MODE/)** - Autonomous
  agentic loops for multi-turn workflows
- **[Multitask](~/.amplihack/.claude/skills/multitask/SKILL.md)** - Parallel
  workstream execution with subprocess isolation

### Agents & Specialized Analysis

- **[37 Agents](~/.amplihack/.claude/agents/)** (7 core, 30 specialized) -
  Architect, builder, reviewer, tester, security, optimizer, and more
- **[Goal-Seeking Agent Generator](https://rysweet.github.io/amplihack/GOAL_AGENT_GENERATOR_GUIDE/)** -
  Create autonomous agents from simple prompts
- **[Expert Panel](/amplihack:expert-panel)** - Multi-expert review with voting
  for complex decisions
- **[Multi-Agent Debate](/amplihack:debate)** - Structured debate for
  architectural trade-offs
- **[N-Version Programming](/amplihack:n-version)** - Generate multiple
  implementations, select best

### Workflows & Methodologies

- **[Document-Driven Development](https://rysweet.github.io/amplihack/document_driven_development/)** -
  Documentation-first methodology for large features
- **[Fix Workflow](/amplihack:fix)** - Rapid resolution of common error patterns
  (imports, CI, tests, config)
- **[Pre-Commit Diagnostics](~/.amplihack/.claude/agents/amplihack/specialized/pre-commit-diagnostic.md)** -
  Fix linting, formatting, type checking before push
- **[CI Diagnostics](~/.amplihack/.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md)** -
  Iterate until PR is mergeable (never auto-merges)
- **[Cascade Fallback](/amplihack:cascade)** - Graceful degradation for
  resilient operations

### Memory & Knowledge Management

- **[Kuzu Memory System](https://rysweet.github.io/amplihack/AGENT_MEMORY_QUICKSTART/)** -
  Persistent memory and knowledge graphs across sessions
- **[Discoveries](https://rysweet.github.io/amplihack/DISCOVERIES/)** -
  Documented problems, solutions, and learnings
- **[Investigation Workflow](#workflows)** - Deep knowledge excavation with
  auto-documentation
- **[Knowledge Builder](/amplihack:knowledge-builder)** - Build comprehensive
  knowledge base from codebase
- **[Transcripts Management](/amplihack:transcripts)** - Conversation transcript
  tracking and search

### Skills & Tools

- **[85+ Skills](~/.amplihack/.claude/skills/README.md)** - PDF, XLSX, DOCX,
  PPTX manipulation, Azure admin, AzDO, and workflow patterns
- **[Office Skills](~/.amplihack/.claude/skills/README.md)** - Comprehensive
  document processing (PDF, Excel, Word, PowerPoint)
- **[Azure Admin](~/.amplihack/.claude/skills/azure-admin/README.md)** -
  Identity management, RBAC, resource orchestration
- **[Azure DevOps CLI](~/.amplihack/.claude/skills/azure-devops-cli/README.md)** -
  Pipelines, repos, artifacts automation
- **[Pre-Commit Manager](~/.amplihack/.claude/skills/pre-commit-manager/README.md)** -
  Automatic hook setup with preference memory

### Development Tools

- **[Profile Management](https://rysweet.github.io/amplihack/PROFILE_MANAGEMENT/)** -
  Token optimization (72% reduction) via component filtering
- **[Modular Build](/amplihack:modular-build)** - Self-contained modules with
  clear contracts
- **[Cleanup Agent](~/.amplihack/.claude/agents/amplihack/specialized/cleanup.md)** -
  Remove artifacts and enforce philosophy
- **[Worktree Management](~/.amplihack/.claude/agents/amplihack/specialized/worktree-manager.md)** -
  Git worktree automation for parallel development
- **[Statusline](https://rysweet.github.io/amplihack/reference/STATUSLINE/)** -
  Real-time session info (tokens, cost, duration, model)

### Quality & Security

- **[Code Analysis](/amplihack:analyze)** - Comprehensive philosophy compliance
  review
- **[Security Analysis](/amplihack:xpia)** - XPIA cross-prompt injection defense
- **[Reflection](/amplihack:reflect)** - Session analysis and improvement
  recommendations
- **[Socratic Questioning](/amplihack:socratic)** - Challenge claims and clarify
  requirements
- **[Benchmarking](https://rysweet.github.io/amplihack/BENCHMARKING/)** -
  Performance measurement with eval-recipes

### Documentation & Publishing

- **[GitHub Pages Generation](https://rysweet.github.io/amplihack/howto/github-pages-generation/)** -
  Automatic documentation sites with MkDocs
- **[Documentation System](~/.amplihack/.claude/context/PHILOSOPHY.md)** - Eight
  rules of good documentation
- **[Implementation Summary](https://rysweet.github.io/amplihack/IMPLEMENTATION_SUMMARY/)** -
  Architecture overview

### Integration & Compatibility

- **[GitHub Copilot CLI](https://rysweet.github.io/amplihack/github-copilot-litellm-integration/)** -
  Full compatibility with adaptive hooks
- **[Microsoft Amplifier](https://github.com/microsoft/amplifier)** -
  Multi-model support with configuration wizard
- **[Awesome-Copilot Integration](docs/howto/awesome-copilot-integration.md)** -
  MCP server, plugin marketplace, drift detection
- **[RustyClawd Integration](#rustyclawd-integration)** - High-performance Rust
  implementation (5-10x faster startup)
- **[Azure OpenAI Proxy](https://rysweet.github.io/amplihack/PROXY_CONFIG_GUIDE/)** -
  Use Azure models via Claude Code

### Advanced Features

- **[Remote Execution](~/.amplihack/.claude/tools/amplihack/remote/README.md)** -
  Distribute work across Azure VMs (Beta)
- **[Power-Steering](https://rysweet.github.io/amplihack/reference/STATUSLINE/#power-steering)** -
  AI-powered session guidance with redirect detection
- **[Lock Mode](https://rysweet.github.io/amplihack/reference/STATUSLINE/#lock-mode)** -
  Continuous work without stopping
- **[Customization System](/amplihack:customize)** - Manage user preferences
  (verbosity, style, workflow)
- **[Session Logs](~/.amplihack/.claude/runtime/logs/)** - Comprehensive logging
  and decision records

## Configuration

### Claude Code (Default)

Set `$ANTHROPIC_API_KEY` before launching:

```bash
export ANTHROPIC_API_KEY=your-key-here
amplihack claude
```

### GitHub Copilot CLI

All 38 agents and 73 skills work with Copilot:

```bash
# Default mode (no agent)
amplihack copilot -- -p "Your task"

# With specific agent
amplihack copilot -- --agent architect -p "Design REST API"

# List available agents
ls .github/agents/*.md
```

**Note**: Copilot shows "No custom agents configured" until you select one with
`--agent <name>`.

Full guide: [COPILOT_CLI.md](COPILOT_CLI.md)

### Microsoft Amplifier

Interactive configuration wizard on first startup:

```bash
amplihack amplifier
```

Supports all models available in GitHub Copilot ecosystem.

### Azure OpenAI via Proxy

Create `azure.env`:

```env
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview  # Optional
```

Launch with configuration:

```bash
amplihack launch --with-proxy-config ./azure.env
```

**Security**: Never commit API keys to version control.

Full guide:
[docs/PROXY_CONFIG_GUIDE.md](https://rysweet.github.io/amplihack/PROXY_CONFIG_GUIDE/)

### Workflow Customization

Edit `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` to customize the
development process. Changes apply immediately to all commands.

Custom workflows:
[docs/WORKFLOW_COMPLETION.md](https://rysweet.github.io/amplihack/WORKFLOW_COMPLETION/)

## Documentation Navigator

### Getting Started

- **[Prerequisites](https://rysweet.github.io/amplihack/PREREQUISITES/)** -
  Platform setup, runtime dependencies, tool installation
- **[Proxy Configuration](https://rysweet.github.io/amplihack/PROXY_CONFIG_GUIDE/)** -
  Azure OpenAI setup for Claude Code
- **[First Session Tutorial](#first-session)** - Interactive guide to amplihack
  basics

### Core Features

- **[Auto Mode](https://rysweet.github.io/amplihack/AUTO_MODE/)** - Autonomous
  agentic loops for multi-turn workflows
- **[Profile Management](https://rysweet.github.io/amplihack/PROFILE_MANAGEMENT/)** -
  Token optimization via component filtering
- **[Goal Agent Generator](https://rysweet.github.io/amplihack/GOAL_AGENT_GENERATOR_GUIDE/)** -
  Create autonomous agents from prompts
- **[Kuzu Memory System](https://rysweet.github.io/amplihack/AGENT_MEMORY_QUICKSTART/)** -
  Persistent knowledge graphs
- **[Benchmarking](https://rysweet.github.io/amplihack/BENCHMARKING/)** -
  Performance measurement with eval-recipes

### Skills & Integrations

- **[Skills System](~/.amplihack/.claude/skills/README.md)** - 85+ skills
  including office, Azure, and workflow patterns
- **[GitHub Copilot Integration](https://rysweet.github.io/amplihack/github-copilot-litellm-integration/)** -
  Full CLI support
- **[Awesome-Copilot Integration](docs/howto/awesome-copilot-integration.md)** -
  MCP server and plugin marketplace
- **[Azure DevOps Tools](docs/azure-devops/README.md)** - Work item management
  with CLI tools

### Methodology & Patterns

- **[Document-Driven Development](https://rysweet.github.io/amplihack/document_driven_development/)** -
  Documentation-first approach for large features
- **[DDD Phases](https://rysweet.github.io/amplihack/document_driven_development/phases/)** -
  Step-by-step implementation guide
- **[Core Concepts](https://rysweet.github.io/amplihack/document_driven_development/core_concepts/)** -
  Context poisoning, file crawling, retcon writing
- **[Workspace Pattern](https://rysweet.github.io/amplihack/WORKSPACE_PATTERN/)** -
  Multi-project organization

### Configuration & Customization

- **[Hook Configuration](https://rysweet.github.io/amplihack/HOOK_CONFIGURATION_GUIDE/)** -
  Session hooks and lifecycle management
- **[Settings Hook](docs/howto/settings-hook-configuration.md)** - Automatic
  validation and troubleshooting
- **[Workflow Customization](https://rysweet.github.io/amplihack/WORKFLOW_COMPLETION/)** -
  Modify development process
- **[Hooks Comparison](docs/HOOKS_COMPARISON.md)** - Adaptive hook system
  details

### Development & Contributing

- **[Developing amplihack](https://rysweet.github.io/amplihack/DEVELOPING_AMPLIHACK/)** -
  Contributing guide, local setup, testing
- **[Implementation Summary](https://rysweet.github.io/amplihack/IMPLEMENTATION_SUMMARY/)** -
  Architecture overview
- **[Creating Tools](https://rysweet.github.io/amplihack/CREATE_YOUR_OWN_TOOLS/)** -
  Build custom AI-powered tools

### Core Principles

- **[The Amplihack Way](https://rysweet.github.io/amplihack/THIS_IS_THE_WAY/)** -
  Effective strategies for AI-agent development
- **[Philosophy](~/.amplihack/.claude/context/PHILOSOPHY.md)** - Ruthless
  simplicity, modular design, zero-BS implementation
- **[Patterns](~/.amplihack/.claude/context/PATTERNS.md)** - Proven solutions
  for recurring challenges
- **[Discoveries](https://rysweet.github.io/amplihack/DISCOVERIES/)** -
  Problems, solutions, and learnings

### Security

- **[Security Recommendations](https://rysweet.github.io/amplihack/SECURITY_RECOMMENDATIONS/)** -
  Best practices and guidelines
- **[Security Context Preservation](https://rysweet.github.io/amplihack/SECURITY_CONTEXT_PRESERVATION/)** -
  Context handling

## Development

### Contributing

Fork the repository and submit PRs. Add agents to
`~/.amplihack/.claude/agents/`, patterns to
`~/.amplihack/.claude/context/PATTERNS.md`.

Contributing guide:
[docs/DEVELOPING_AMPLIHACK.md](https://rysweet.github.io/amplihack/DEVELOPING_AMPLIHACK/)

### Local Development

```bash
git clone https://github.com/rysweet/amplihack.git
cd amplihack
uv pip install -e .
amplihack launch
```

### Testing

```bash
pytest tests/
```

## RustyClawd Integration

RustyClawd is a high-performance Rust implementation of Claude Code with 5-10x
faster startup, 7x less memory, and Rust safety guarantees. Drop-in compatible
with amplihack.

### Installation

**Option 1: Via cargo**

```bash
cargo install --git https://github.com/rysweet/RustyClawd rusty
```

**Option 2: Build from source**

```bash
git clone https://github.com/rysweet/RustyClawd
cd RustyClawd
cargo build --release
export RUSTYCLAWD_PATH=$PWD/target/release/rusty
```

### Usage

```bash
# Explicit mode
amplihack RustyClawd -- -p "your prompt"

# Environment variable
export AMPLIHACK_USE_RUSTYCLAWD=1
amplihack launch -- -p "your prompt"
```

### Configuration

- **AMPLIHACK_USE_RUSTYCLAWD**: Force RustyClawd usage (1/true/yes)
- **RUSTYCLAWD_PATH**: Custom binary path (optional)

## License

MIT. See [LICENSE](LICENSE).
