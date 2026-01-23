# amplihack

Development framework for popular coding agent systems (Claude Code, Github Copilot CLI, Microsoft Amplifier, codex) that provides structured dev workflows, memory, a package of useful skills and agents, goal-seeking agent generator, auto mode, self-improvement with reflection, and commands for getting the most out of agentic coding. Unlikely to work on Windows without WSL. 

**📚 [View Full Documentation](https://rysweet.github.io/amplihack/)**

```sh
# Launch amplihack with Claude Code
uvx --from git+https://github.com/rysweet/amplihack amplihack claude
```

```sh
# Launch amplihack with Microsoft Amplifier (https://github.com/microsoft/amplifier)
uvx --from git+https://github.com/rysweet/amplihack amplihack amplifier
```

```sh
Launch AMplihack with Github Copilot CLI
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot
```

Try asking the **amplihack-guide** agent for help.

## Table of Contents

- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Basic Usage](#basic-usage)
  - [Create Alias for Easy Access](#create-alias-for-easy-access)
- [Core Concepts](#core-concepts)
  - [Workflow](#workflow)
  - [Philosophy](#philosophy)
- [Configuration](#configuration)
  - [Anthropic (Default)](#anthropic-default)
  - [Azure OpenAI](#azure-openai)
  - [GitHub Copilot CLI](#github-copilot-cli)
  - [Custom Workflows](#custom-workflows)
- [Commands Reference](#commands-reference)
- [Agents Reference](#agents-reference)
  - [Core Agents](#core-agents-6)
  - [Specialized Agents](#specialized-agents-23)
- [Features](#features)
  - [Workflow Orchestration by Default](#workflow-orchestration-by-default)
  - [Goal-Seeking Agent Generator](#goal-seeking-agent-generator)
  - [Profile Management](#profile-management)
  - [GitHub Pages Documentation Generation](#github-pages-documentation-generation)
  - [Additional Features](#additional-features)
  - [Statusline](#statusline)
- [Documentation](#documentation)
  - [Getting Started](#getting-started)
  - [Features](#features-1)
  - [Patterns](#patterns)
  - [Configuration](#configuration-1)
  - [Development](#development-1)
  - [Methodology](#methodology)
  - [Security](#security)
  - [Core Principles](#core-principles)
- [Development](#development)
  - [Contributing](#contributing)
  - [Local Development](#local-development)
  - [Testing](#testing)
- [License](#license)

## Quick Start

### Prerequisites
- MacOS, WSL, or Linux
- Python 3.2+, Node.js 18+, npm, git
- GitHub CLI (`gh`) for PR/issue management
- az cli for AzDO and Azure skills
- uv ([astral.sh/uv](https://docs.astral.sh/uv/))

For detailed installation instructions, see
[docs/PREREQUISITES.md](https://rysweet.github.io/amplihack/PREREQUISITES/).

You may find that its useful to use amplihack with [azlin](https://github.com/rysweet/azlin) which makes it easy to start linux based agentic coding vms in the azure cloud. 

### Basic Usage

```sh
# Launch Claude Code with amplihack
amplihack launch

# With Azure OpenAI (requires azure.env configuration)
amplihack launch --with-proxy-config ./azure.env

# Work directly in a GitHub repository
amplihack launch --checkout-repo owner/repo
```

**New to amplihack?** After launching, try the interactive tutorial:

```
Task(subagent_type='guide', prompt='I am new to amplihack. Teach me the basics.')
```

The guide agent will walk you through workflows, prompting strategies, and hands-on
exercises. Takes 60-90 minutes to complete.

**Already familiar?** Tell Claude Code to `cd /path/to/my/project` and provide
your prompt. All prompts are automatically wrapped with `/amplihack:ultrathink`
for workflow orchestration (use `--no-ultrathink` flag to opt-out for simple
tasks).

### Create Alias for Easy Access

Instead of typing the full uvx command, create an alias:

```sh
# Add to your ~/.bashrc or ~/.zshrc
alias amplihack='uvx --from git+https://github.com/rysweet/amplihack amplihack'

# Reload your shell
source ~/.bashrc  # or source ~/.zshrc
```

Now you can simply run:

```sh
amplihack launch
amplihack launch --with-proxy-config ./azure.env
amplihack launch --checkout-repo owner/repo
```

## Core Concepts

### Philosophy

- **Simplicity** - Start simple, add only justified complexity
- **Modular** - Self-contained modules with clear interfaces
- **Test-driven** - Tests before implementation
- **Zero BS Principle** - continually reinforcing zero tolerance of stubs, TODOs, faked apis or data, etc

### Workflows

The system tries to direct all work to one of a few customizeable [structured workflows](~/.amplihack/.claude/workflow/) which attempt to detect the user intent and guide the agent through a structured set of steps. The workflows try to put solid gaurdrails and multiagent points of view around the work. See the [DEFAULT_WORKFLOW.md](~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md) for an example.

## Configuration

amplihack works with [Claude Code](https://claude.com/product/claude-code?utm_source=google&utm_medium=paid_search_coder&utm_campaign=acq_code_us_q3&utm_content=getstarted_text_v1) and Anthropic models by default. You can, however also use it with [Microsoft Amplifier](https://github.com/microsoft/amplifier) and [Github Copilot CLI](https://github.com/features/copilot/cli). 

### Anthropic (Default)

Set your $ANTHROPIC_API_KEY prior to launching amplihack. 

### Other models with GH Copilot CLI

Github Copilot CLI supports all the models supported by GH Copilot - though most of the framework is only tested with Anthropic. 

```sh
amplihack copilot
```

and then use **/model**

### Other models with Microosft Amplifier

Amplifier wil walk you through model configuration on first startup:

```sh
amplihack amplfier
```

### Azure OpenAI in Claude via proxy

To use Azure OpenAI models, create an `azure.env` file with the following
minimum configuration:

```env
# Required: Your Azure OpenAI API key
AZURE_OPENAI_API_KEY=your-api-key

# Required: Azure OpenAI endpoint (base URL without path)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com

# Required: Model deployment name (use either BIG_MODEL or AZURE_OPENAI_DEPLOYMENT_NAME)
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1

# Optional: API version (defaults to 2025-04-01-preview)
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

Launch with Azure configuration:

```sh
amplihack launch --with-proxy-config ./azure.env
```

**Note:** The endpoint should be just the base URL (e.g.,
`https://your-resource.openai.azure.com`) without `/openai` or other path
suffixes. The proxy will automatically construct the correct API paths.

**Security Warning**: Never commit API keys to version control. Use environment
variables or secure key management systems.

### GitHub Copilot CLI

amplihack fully supports GitHub Copilot CLI with adaptive hooks that enable
preference injection and context loading. All 38 agents, 73 skills, and 24 commands
work seamlessly with Copilot.

```bash
# Default mode (no agent)
amplihack copilot -- -p "Your task here"

# With specific agent
amplihack copilot -- --agent architect -p "Design a REST API"
amplihack copilot -- --agent builder -p "Implement the spec"

# List available agents
ls .github/agents/*.md
```

**Note**: Copilot shows "No custom agents configured" until you select one with `--agent <name>`.
All 38 amplihack agents are available in `.github/agents/`.

See [COPILOT_CLI.md](COPILOT_CLI.md) for complete integration guide and
[docs/HOOKS_COMPARISON.md](docs/HOOKS_COMPARISON.md) for adaptive hook system details.

### Custom Workflows

The iterative-step workflow is fully customizable. Edit
`~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` to modify the development process -
changes apply immediately to `/ultrathink` and other commands. See
[docs/WORKFLOW_COMPLETION.md](https://rysweet.github.io/amplihack/WORKFLOW_COMPLETION/)
for detailed customization instructions.

## Commands Reference

| Command                        | Description                                             |
| ------------------------------ | ------------------------------------------------------- |
| `amplihack new`                | Generate goal-seeking agents from prompts               |
| `/amplihack:ultrathink`        | Deep multi-agent analysis (now DEFAULT for all prompts) |
| `/amplihack:analyze`           | Code analysis and philosophy compliance review          |
| `/amplihack:auto`              | Autonomous agentic loop (clarify → plan → execute)      |
| `/amplihack:cascade`           | Fallback cascade for resilient operations               |
| `/amplihack:debate`            | Multi-agent debate for complex decisions                |
| `/amplihack:expert-panel`      | Multi-expert review with voting                         |
| `/amplihack:n-version`         | N-version programming for critical code                 |
| `/amplihack:socratic`          | Generate Socratic questions to challenge claims         |
| `/amplihack:reflect`           | Session reflection and improvement analysis             |
| `/amplihack:improve`           | Capture learnings and implement improvements            |
| `/amplihack:fix`               | Fix common errors and code issues                       |
| `/amplihack:modular-build`     | Build self-contained modules with clear contracts       |
| `/amplihack:knowledge-builder` | Build comprehensive knowledge base                      |
| `/amplihack:transcripts`       | Conversation transcript management                      |
| `/amplihack:xpia`              | Security analysis and threat detection                  |
| `/amplihack:customize`         | Manage user-specific preferences                        |
| `/amplihack:ddd:0-help`        | Document-Driven Development help and guidance           |
| `/amplihack:ddd:1-plan`        | Phase 0: Planning & Alignment                           |
| `/amplihack:ddd:2-docs`        | Phase 1: Documentation Retcon                           |
| `/amplihack:ddd:3-code-plan`   | Phase 3: Implementation Planning                        |
| `/amplihack:ddd:4-code`        | Phase 4: Code Implementation                            |
| `/amplihack:ddd:5-finish`      | Phase 5: Testing & Phase 6: Cleanup                     |
| `/amplihack:ddd:prime`         | Prime context with DDD overview                         |
| `/amplihack:ddd:status`        | Check current DDD phase and progress                    |
| `/amplihack:lock`              | Enable continuous work mode                             |
| `/amplihack:unlock`            | Disable continuous work mode                            |
| `/amplihack:install`           | Install amplihack tools                                 |
| `/amplihack:uninstall`         | Uninstall amplihack tools                               |

## Agents Reference

### Core Agents (7)

| Agent                                                             | Purpose                                  |
| ----------------------------------------------------------------- | ---------------------------------------- |
| [**api-designer**](~/.amplihack/.claude/agents/amplihack/core/api-designer.md) | API design and endpoint structure        |
| [**architect**](~/.amplihack/.claude/agents/amplihack/core/architect.md)       | System design and architecture decisions |
| [**builder**](~/.amplihack/.claude/agents/amplihack/core/builder.md)           | Code generation and implementation       |
| [**guide**](~/.amplihack/.claude/agents/amplihack/core/guide.md)               | Feature guide and onboarding specialist  |
| [**optimizer**](~/.amplihack/.claude/agents/amplihack/core/optimizer.md)       | Performance optimization and efficiency  |
| [**reviewer**](~/.amplihack/.claude/agents/amplihack/core/reviewer.md)         | Code quality and best practices review   |
| [**tester**](~/.amplihack/.claude/agents/amplihack/core/tester.md)             | Test generation and validation           |

### Specialized Agents (27)

| Agent                                                                                          | Purpose                                         |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [**ambiguity**](~/.amplihack/.claude/agents/amplihack/specialized/ambiguity.md)                             | Clarify ambiguous requirements                  |
| [**amplifier-cli-architect**](~/.amplihack/.claude/agents/amplihack/specialized/amplifier-cli-architect.md) | CLI tool design and architecture                |
| [**analyzer**](~/.amplihack/.claude/agents/amplihack/specialized/analyzer.md)                               | Deep code analysis                              |
| [**azure-kubernetes-expert**](~/.amplihack/.claude/agents/amplihack/specialized/azure-kubernetes-expert.md) | Azure Kubernetes Service expertise              |
| [**ci-diagnostic-workflow**](~/.amplihack/.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md)   | CI/CD pipeline diagnostics                      |
| [**cleanup**](~/.amplihack/.claude/agents/amplihack/specialized/cleanup.md)                                 | Remove artifacts and enforce philosophy         |
| [**database**](~/.amplihack/.claude/agents/amplihack/specialized/database.md)                               | Database design and optimization                |
| [**fallback-cascade**](~/.amplihack/.claude/agents/amplihack/specialized/fallback-cascade.md)               | Resilient fallback strategies                   |
| [**fix-agent**](~/.amplihack/.claude/agents/amplihack/specialized/fix-agent.md)                             | Automated error fixing                          |
| [**integration**](~/.amplihack/.claude/agents/amplihack/specialized/integration.md)                         | System integration patterns                     |
| [**knowledge-archaeologist**](~/.amplihack/.claude/agents/amplihack/specialized/knowledge-archaeologist.md) | Extract and preserve knowledge                  |
| [**multi-agent-debate**](~/.amplihack/.claude/agents/amplihack/specialized/multi-agent-debate.md)           | Facilitate multi-perspective debates            |
| [**n-version-validator**](~/.amplihack/.claude/agents/amplihack/specialized/n-version-validator.md)         | Validate N-version implementations              |
| [**patterns**](~/.amplihack/.claude/agents/amplihack/specialized/patterns.md)                               | Design pattern recommendations                  |
| [**pre-commit-diagnostic**](~/.amplihack/.claude/agents/amplihack/specialized/pre-commit-diagnostic.md)     | Pre-commit hook diagnostics                     |
| [**preference-reviewer**](~/.amplihack/.claude/agents/amplihack/specialized/preference-reviewer.md)         | User preference validation                      |
| [**prompt-writer**](~/.amplihack/.claude/agents/amplihack/specialized/prompt-writer.md)                     | Effective prompt engineering                    |
| [**rust-programming-expert**](~/.amplihack/.claude/agents/amplihack/specialized/rust-programming-expert.md) | Rust language expertise                         |
| [**security**](~/.amplihack/.claude/agents/amplihack/specialized/security.md)                               | Security analysis and vulnerability detection   |
| [**visualization-architect**](~/.amplihack/.claude/agents/amplihack/specialized/visualization-architect.md) | Data visualization design                       |
| [**xpia-defense**](~/.amplihack/.claude/agents/amplihack/specialized/xpia-defense.md)                       | Advanced threat detection                       |
| [**philosophy-guardian**](~/.amplihack/.claude/agents/amplihack/specialized/philosophy-guardian.md)         | Philosophy compliance and simplicity validation |

## Features

### Remote Execution (Beta)

Distribute agentic work across Azure VMs:

```sh
amplihack remote auto "implement feature" --region westus3 --vm-size s
```

Documentation:
[.claude/tools/amplihack/remote/README.md](~/.amplihack/.claude/tools/amplihack/remote/README.md)

### Workflow Orchestration by Default (NEW!)

All prompts are automatically wrapped with `/amplihack:ultrathink` for maximum
effectiveness. This enables:

- Multi-agent workflow orchestration
- Multi-step development workflow
- Automated architecture, building, and testing
- Philosophy compliance checking

**Benchmark results:** Amplihack without orchestration = vanilla Claude. The
orchestration IS the value! See
[benchmarking guide](https://rysweet.github.io/amplihack/BENCHMARKING/) for
measuring performance.

**Opt-out for simple tasks:**

```sh
# Skip orchestration with --no-ultrathink flag
amplihack launch --no-ultrathink -- -p "simple prompt"

# Or use slash commands directly
amplihack launch -- -p "/analyze src/file.py"
```

**How it works:**

```sh
# Before: Manual orchestration required
amplihack launch -- -p "/amplihack:ultrathink implement feature"

# Now: Automatic orchestration (same result)
amplihack launch -- -p "implement feature"
```

### Goal-Seeking Agent Generator

**Create autonomous agents from simple prompts:**

```bash
# Write your goal
cat > my_goal.md <<'EOF'
# Goal: Automated Code Review
Review Python code and suggest improvements.
EOF

# Generate agent
amplihack new --file my_goal.md

# Run agent
cd goal_agents/automated-code-review-agent
python main.py
```

**Features:**

- Generate agents in < 0.1 seconds
- Automatic skill matching
- Multi-phase execution planning
- Standalone, distributable agents

**Learn more:**
[Goal Agent Generator Guide](https://rysweet.github.io/amplihack/GOAL_AGENT_GENERATOR_GUIDE/)

### Profile Management

**Reduce token usage by 72% with profile-based component filtering:**

```sh
# Install with filtering
amplihack install

# Result: Only 9/32 agents staged (72% reduction)

# Launch with filtering
amplihack launch

# Result: Focused environment for coding tasks
```

**Built-in Profiles:**

- `all`: Full environment (32 agents, default)
- `coding`: Development-focused (9 agents)
- `research`: Investigation-focused (7 agents)

**Learn more:**
[Profile Management Guide](https://rysweet.github.io/amplihack/PROFILE_MANAGEMENT/)

### GitHub Pages Documentation Generation

**Generate professional documentation sites automatically:**

- Auto-discovers content from `docs/`, `README.md`, and `~/.amplihack/.claude/commands/`
- Three-pass validation ensures quality documentation
- Safe gh-pages deployment with rollback support
- Local preview server for testing
- MkDocs + Material theme integration

**Learn more:**

- [Tutorial: Your First Documentation Site](https://rysweet.github.io/amplihack/tutorials/first-docs-site/)
- [How-To: Generate GitHub Pages Sites](https://rysweet.github.io/amplihack/howto/github-pages-generation/)
- [API Reference: GitHub Pages Module](https://rysweet.github.io/amplihack/reference/github-pages-api/)

### Additional Features

- **[Power-Steering](https://rysweet.github.io/amplihack/reference/STATUSLINE/#power-steering)** -
  AI-powered session guidance with intelligent redirect detection (🚦 indicator)
- **[Auto Mode](https://rysweet.github.io/amplihack/AUTO_MODE/)** - Autonomous
  agentic loops for multi-turn workflows (`/amplihack:auto`)
- **[Lock Mode](https://rysweet.github.io/amplihack/reference/STATUSLINE/#lock-mode)** -
  Continuous work mode without stopping (`/amplihack:lock`, `/amplihack:unlock`)
  (🔒 indicator)
- **[Document-Driven Development](https://rysweet.github.io/amplihack/document_driven_development/README/)** -
  Systematic methodology for large features with documentation-first approach
- **[Fault-Tolerant Workflows](CLAUDE.md#fault-tolerance-patterns)** - N-version
  programming, multi-agent debate, and cascade fallback patterns
- **[Security Analysis](CLAUDE.md#key-commands)** - XPIA cross-prompt injection
  defense (`/amplihack:xpia`)
- **[Kuzu Memory System](https://rysweet.github.io/amplihack/AGENT_MEMORY_QUICKSTART/)** -
  Persistent memory and knowledge graphs across sessions with code-aware context
- **[Investigation Workflow](CLAUDE.md#investigation-workflow)** - Deep
  knowledge excavation with historical context
- **[Skills System](~/.amplihack/.claude/skills/README.md)** - 85+ skills including PDF,
  XLSX, DOCX, PPTX, analysts, and workflow patterns
- **[Fix Workflow](CLAUDE.md#key-commands)** - Rapid resolution of common error
  patterns (`/amplihack:fix`)
- **[Reflection & Improvement](CLAUDE.md#key-commands)** - Session analysis and
  learning capture (`/amplihack:reflect`, `/amplihack:improve`)
- **[Socratic Questioning](CLAUDE.md#key-commands)** - Challenge claims and
  clarify requirements (`/amplihack:socratic`)
- **[Expert Panel](CLAUDE.md#key-commands)** - Multi-expert review with voting
  (`/amplihack:expert-panel`)
- **[Knowledge Builder](CLAUDE.md#key-commands)** - Build comprehensive
  knowledge base (`/amplihack:knowledge-builder`)
- **[Transcripts Management](CLAUDE.md#key-commands)** - Conversation transcript
  tracking (`/amplihack:transcripts`)
- **[Modular Build](CLAUDE.md#key-commands)** - Self-contained modules with
  clear contracts (`/amplihack:modular-build`)
- **[Pre-commit Diagnostics](CLAUDE.md#development-workflow-agents)** - Fix
  formatting, linting, type checking before push
- **[CI Diagnostics](CLAUDE.md#development-workflow-agents)** - Monitor CI,
  diagnose failures, iterate until mergeable
- **[Worktree Management](~/.amplihack/.claude/agents/amplihack/specialized/worktree-manager.md)** -
  Git worktree automation for parallel development
- **[Session Logs](CLAUDE.md#working-philosophy)** - Comprehensive logging and
  decision records
- **[Customization System](CLAUDE.md#key-commands)** - Manage user preferences
  (`/amplihack:customize`)

### Statusline

Real-time session information displayed at the bottom of Claude Code showing:

- Current directory and git status (branch, clean/dirty)
- Active model (Opus/Sonnet/Haiku)
- Token usage 🎫, Cost 💰, and Duration ⏱
- Feature indicators: Power-Steering 🚦, Lock Mode 🔒

**Example:**

```
~/src/amplihack (main → origin) Sonnet 🎫 234K 💰$1.23 ⏱12m
```

**Full documentation:**
[docs/reference/STATUSLINE.md](https://rysweet.github.io/amplihack/reference/STATUSLINE/)

## Documentation

### Getting Started

- [Prerequisites](https://rysweet.github.io/amplihack/PREREQUISITES/) - Platform
  setup and dependencies
- [Proxy Configuration](https://rysweet.github.io/amplihack/PROXY_CONFIG_GUIDE/) -
  Azure OpenAI proxy setup

### Features

- [Auto Mode](https://rysweet.github.io/amplihack/AUTO_MODE/) - Autonomous
  agentic loop
- [Agent Bundles](https://rysweet.github.io/amplihack/agent-bundle-generator-guide/) -
  Custom agent creation
- [GitHub Copilot Integration](https://rysweet.github.io/amplihack/github-copilot-litellm-integration/) -
  Copilot CLI support
- [Office Skills](~/.amplihack/.claude/skills/README.md) - PDF, Excel, Word, and PowerPoint
  document processing
  - [PDF Skill](~/.amplihack/.claude/skills/pdf/README.md) - Comprehensive PDF manipulation
  - [XLSX Skill](~/.amplihack/.claude/skills/xlsx/README.md) - Spreadsheet creation with
    formulas and financial modeling
- [Azure Admin Skill](~/.amplihack/.claude/skills/azure-admin/README.md) - Azure
  administration, identity management, RBAC, and resource orchestration
- [Azure DevOps CLI Skill](~/.amplihack/.claude/skills/azure-devops-cli/README.md) - Azure
  DevOps automation, pipelines, repos, and artifacts
- **[Azure DevOps Boards Tools](docs/azure-devops/README.md) - Work item
  management with CLI tools**
- [Benchmarking with eval-recipes](https://rysweet.github.io/amplihack/BENCHMARKING/) -
  Performance measurement and comparison
- [Profile Management](https://rysweet.github.io/amplihack/PROFILE_MANAGEMENT/) -
  Token optimization and environment customization

### Patterns

- [Workspace Pattern](https://rysweet.github.io/amplihack/WORKSPACE_PATTERN/) -
  Multi-project organization with git submodules

### Configuration

- [Hook Configuration](https://rysweet.github.io/amplihack/HOOK_CONFIGURATION_GUIDE/) -
  Session hooks
- [Workflow Customization](https://rysweet.github.io/amplihack/WORKFLOW_COMPLETION/) -
  Process customization

### Development

- [Developing amplihack](https://rysweet.github.io/amplihack/DEVELOPING_AMPLIHACK/) -
  Contributing guide
- [Implementation Summary](https://rysweet.github.io/amplihack/IMPLEMENTATION_SUMMARY/) -
  Architecture overview

### Methodology

- [Document-Driven Development](https://rysweet.github.io/amplihack/document_driven_development/README/) -
  Systematic approach for large features
- [DDD Overview](https://rysweet.github.io/amplihack/document_driven_development/overview/) -
  Comprehensive guide to DDD principles
- [Core Concepts](https://rysweet.github.io/amplihack/document_driven_development/core_concepts/README/) -
  Context poisoning, file crawling, retcon writing
- [DDD Phases](https://rysweet.github.io/amplihack/document_driven_development/phases/README/) -
  Step-by-step implementation guide

### Security

- [Security Recommendations](https://rysweet.github.io/amplihack/SECURITY_RECOMMENDATIONS/) -
  Best practices
- [Security Context Preservation](https://rysweet.github.io/amplihack/SECURITY_CONTEXT_PRESERVATION/) -
  Context handling

### Core Principles

- [The Amplihack Way](https://rysweet.github.io/amplihack/THIS_IS_THE_WAY/) -
  Effective strategies for AI-agent development
- [Discoveries](https://rysweet.github.io/amplihack/DISCOVERIES/) - Documented
  problems, solutions, and learnings
- [Creating Tools](https://rysweet.github.io/amplihack/CREATE_YOUR_OWN_TOOLS/) -
  Build custom AI-powered tools
- [Philosophy](~/.amplihack/.claude/context/PHILOSOPHY.md) - Core principles and patterns
- [Workflows](~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md) - Development process

## Development

### Contributing

Fork, submit PRs. Add agents to `~/.amplihack/.claude/agents/`, patterns to
`~/.amplihack/.claude/context/PATTERNS.md`.

### Local Development

```sh
git clone https://github.com/rysweet/amplihack.git
cd amplihack
uv pip install -e .
amplihack launch
```

### Testing

```sh
pytest tests/
```

## RustyClawd Integration

Amplihack supports RustyClawd, a high-performance Rust implementation of Claude
Code.

### Quick Start

```bash
# Force RustyClawd usage explicitly
amplihack RustyClawd -- -p "your prompt"

# Or set environment variable
export AMPLIHACK_USE_RUSTYCLAWD=1
amplihack launch -- -p "your prompt"
```

### Benefits

- **5-10x faster startup** compared to Node.js Claude Code
- **7x less memory** usage
- **Rust safety guarantees** - no runtime errors
- **Same features** - drop-in compatible

### Installation

RustyClawd must be available in your system PATH:

**Option 1: Install via cargo**

```bash
cargo install --git https://github.com/rysweet/RustyClawd rusty
```

**Option 2: Build from source**

```bash
git clone https://github.com/rysweet/RustyClawd
cd RustyClawd
cargo build --release
# Add to PATH or use RUSTYCLAWD_PATH environment variable
export RUSTYCLAWD_PATH=$PWD/target/release/rusty
```

**Option 3: Custom binary location**

```bash
# Point to your custom RustyClawd build
export RUSTYCLAWD_PATH=/path/to/your/rusty
```

### Configuration

- **AMPLIHACK_USE_RUSTYCLAWD**: Force RustyClawd usage (1/true/yes)
- **RUSTYCLAWD_PATH**: Custom path to RustyClawd binary (optional)

## License

MIT. See [LICENSE](LICENSE).
