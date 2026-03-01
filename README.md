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

- **Platform**: macOS, Linux, or Windows via WSL (native Windows is not
  supported)
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

After launching amplihack (e.g., `amplihack claude`), you'll be inside an
**interactive agent session** — a chat interface powered by your chosen coding
agent. Everything you type in this session is interpreted by amplihack's
workflow engine, not by your regular shell.

**New users** — start with the interactive tutorial:

```
I am new to amplihack. Teach me the basics.
```

This triggers a guided tutorial (60-90 minutes) that walks you through
amplihack's core concepts and workflows.

**Experienced users** — just describe what you want to build:

```
cd /path/to/my/project
Add user authentication with OAuth2 support
```

The `/dev` command automatically classifies your task, detects parallel
workstreams, and orchestrates execution.

### Developer Quick Example

Here is a complete end-to-end example of amplihack in action:

**1. Single task** — fix a bug:

```bash
cd /path/to/your/project
/dev fix the authentication bug where JWT tokens expire too early
```

What happens:

- Classifies as: `Development` | `1 workstream`
- Builder agent follows the full 23-step DEFAULT_WORKFLOW
- Creates a branch, implements the fix, creates a PR
- Reviewer evaluates the result — if incomplete, automatically runs another
  round
- Final output: `# Dev Orchestrator -- Execution Complete` with PR link

**2. Parallel task** — two independent features at once:

```bash
/dev build a REST API and a React webui for user management
```

What happens:

- Classifies as: `Development` | `2 workstreams`
- Both workstreams launch in parallel (separate `/tmp` clones)
- Each follows the full workflow independently
- Both PRs created simultaneously

**3. Investigation** — understand existing code before changing it:

```bash
/dev investigate how the caching layer works, then add Redis support
```

What happens:

- Detects two workstreams: investigate + implement
- Investigation phase runs first, findings pass to implementation
- Result: informed implementation with full context

**What you'll see during execution:**

1. `[dev-orchestrator] Classified as: Development | Workstreams: 2 — starting execution...`
2. Builder agent output streaming (the actual work)
3. Reviewer evaluation with `GOAL_STATUS: ACHIEVED` or `PARTIAL`
4. If partial — another round runs automatically (up to 3 total)
5. `# Dev Orchestrator -- Execution Complete` with summary and PR links

> **Note**: The `Task()` syntax shown in some documentation is an advanced
> programmatic API for scripting agent workflows. For interactive use, plain
> natural language prompts are all you need.

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

For most tasks, type `/dev <your task>` — the smart-orchestrator automatically
selects the right workflow.

- **DEFAULT_WORKFLOW**: 23-step systematic development process, steps 0–22
  (features, bugs, refactoring)
- **INVESTIGATION_WORKFLOW**: 6-phase knowledge excavation (understanding
  existing systems)
- **Q&A_WORKFLOW**: 3-step minimal workflow (simple questions, quick answers)
- **OPS_WORKFLOW**: 1-step administrative operations (cleanup, maintenance)

Workflows are customizable - edit
`~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` to change process.

Workflow customization:
[docs/WORKFLOW_COMPLETION.md](https://rysweet.github.io/amplihack/WORKFLOW_COMPLETION/)

## Features

### What Most People Use

These are the features you'll use daily:

| Feature              | What It Does                                                                 |
| -------------------- | ---------------------------------------------------------------------------- |
| **`/dev <task>`**    | The main command. Classifies your task, runs the right workflow, creates PRs |
| **37 Agents**        | Specialized AI agents (architect, builder, reviewer, tester, security, etc.) |
| **Recipe Runner**    | Code-enforced workflows that models cannot skip                              |
| **`/fix <pattern>`** | Rapid resolution of common errors (imports, CI, tests, config)               |
| **85+ Skills**       | PDF/Excel/Word processing, Azure admin, pre-commit management, and more      |

### Everything Else

<details>
<summary>Orchestration & Execution (6 features)</summary>

- **[dev-orchestrator (`/dev`)](/dev)** — Unified task orchestrator with
  goal-seeking loop
- **[Recipe Runner](docs/recipes/README.md)** — Code-enforced workflows (10
  bundled recipes)
- **[Auto Mode](https://rysweet.github.io/amplihack/AUTO_MODE/)** — Autonomous
  agentic loops
- **[Multitask](~/.amplihack/.claude/skills/multitask/SKILL.md)** — Parallel
  workstream execution
- **[Expert Panel](/amplihack:expert-panel)** — Multi-expert review with voting
- **[N-Version Programming](/amplihack:n-version)** — Generate multiple
  implementations, select best

</details>

<details>
<summary>Workflows & Methodologies (5 features)</summary>

- **[Document-Driven Development](https://rysweet.github.io/amplihack/document_driven_development/)**
  — Docs-first for large features
- **[Pre-Commit Diagnostics](~/.amplihack/.claude/agents/amplihack/specialized/pre-commit-diagnostic.md)**
  — Fix linting before push
- **[CI Diagnostics](~/.amplihack/.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md)**
  — Iterate until PR is mergeable
- **[Cascade Fallback](/amplihack:cascade)** — Graceful degradation
- **[Quality Audit](/amplihack:analyze)** — Seek/validate/fix/recurse quality
  loop

</details>

<details>
<summary>Memory & Knowledge (5 features)</summary>

- **[Kuzu Memory System](https://rysweet.github.io/amplihack/AGENT_MEMORY_QUICKSTART/)**
  — Persistent memory across sessions
- **[Investigation Workflow](#workflows)** — Deep knowledge excavation with
  auto-documentation
- **[Discoveries](https://rysweet.github.io/amplihack/DISCOVERIES/)** —
  Documented problems and solutions
- **[Knowledge Builder](/amplihack:knowledge-builder)** — Build knowledge base
  from codebase
- **[Goal-Seeking Agent Generator](https://rysweet.github.io/amplihack/GOAL_AGENT_GENERATOR_GUIDE/)**
  — Create agents from prompts

</details>

<details>
<summary>Integration & Compatibility (5 features)</summary>

- **[GitHub Copilot CLI](https://rysweet.github.io/amplihack/github-copilot-litellm-integration/)**
  — Full Copilot compatibility
- **[Microsoft Amplifier](https://github.com/microsoft/amplifier)** —
  Multi-model support
- **[Azure OpenAI Proxy](https://rysweet.github.io/amplihack/PROXY_CONFIG_GUIDE/)**
  — Use Azure models via Claude Code
- **[RustyClawd](#rustyclawd-integration)** — High-performance Rust launcher
  (5-10x faster startup)
- **[Remote Execution](~/.amplihack/.claude/tools/amplihack/remote/README.md)**
  — Distribute work across Azure VMs

</details>

<details>
<summary>Quality, Security & Customization (5 features)</summary>

- **[Security Analysis](/amplihack:xpia)** — Cross-prompt injection defense
- **[Socratic Questioning](/amplihack:socratic)** — Challenge claims and clarify
  requirements
- **[Benchmarking](https://rysweet.github.io/amplihack/BENCHMARKING/)** —
  Performance measurement
- **[Customization](/amplihack:customize)** — User preferences (verbosity,
  style, workflow)
- **[Statusline](https://rysweet.github.io/amplihack/reference/STATUSLINE/)** —
  Real-time session info

</details>

## Configuration

### Claude Code (Default)

Get your API key from
[platform.claude.com/account/keys](https://platform.claude.com/account/keys).
Claude API is pay-per-use; typical amplihack sessions cost $0.01–$2 depending on
task complexity.

Add to `~/.bashrc` or `~/.zshrc` for permanent setup:

```bash
export ANTHROPIC_API_KEY=your-key-here
```

Then verify and launch:

```bash
# Verify the key is set
echo $ANTHROPIC_API_KEY

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
- **[Goal-Seeking Agents](docs/GOAL_SEEKING_AGENTS.md)** - Multi-SDK agents with
  memory, eval, and self-improvement
- **[Agent Tutorial](docs/tutorials/GOAL_SEEKING_AGENT_TUTORIAL.md)** -
  Step-by-step guide to generating and evaluating agents
- **[Interactive Tutorial](/agent-generator-tutor)** - 14-lesson interactive
  tutor via `/agent-generator-tutor` skill
- **[Session-to-Agent](/session-to-agent)** - Convert interactive sessions into
  reusable agents
- **[Eval System](docs/EVAL_SYSTEM_ARCHITECTURE.md)** - L1-L12 progressive
  evaluation with long-horizon memory testing and self-improvement
- **[SDK Adapters Guide](docs/SDK_ADAPTERS_GUIDE.md)** - Deep dive into Copilot,
  Claude, Microsoft, and Mini SDK backends
- **[amplihack-agent-eval](https://github.com/rysweet/amplihack-agent-eval)** -
  Standalone eval framework package
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
