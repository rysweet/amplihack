# amplihack

Development framework for Claude Code with specialized agents and automated
workflows.

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

Launches Claude Code with preconfigured agents. No installation needed.

## Quick Setup

### Create Alias for Easy Access

Instead of typing the full uvx command, create an alias:

```sh
# Add to your ~/.bashrc or ~/.zshrc
alias amplihack='uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack'

# Reload your shell
source ~/.bashrc  # or source ~/.zshrc
```

Now you can simply run:

```sh
amplihack launch
amplihack launch --with-proxy-config ./azure.env
amplihack launch --checkout-repo owner/repo
```

## Quick Start

### Prerequisites

- Python 3.8+, Node.js 18+, npm, git
- GitHub CLI (`gh`) for PR/issue management
- uv ([astral.sh/uv](https://docs.astral.sh/uv/))

For detailed installation instructions, see
[docs/PREREQUISITES.md](docs/PREREQUISITES.md).

### Basic Usage

```sh
# Launch Claude Code with amplihack
amplihack launch

# With Azure OpenAI (requires azure.env configuration)
amplihack launch --with-proxy-config ./azure.env

# Work directly in a GitHub repository
amplihack launch --checkout-repo owner/repo
```

Not sure where to start? Use the command above to run from uvx, then tell Claude
Code to `cd /path/to/my/project` and provide your prompt. All prompts are
automatically wrapped with `/amplihack:ultrathink` for workflow orchestration
(use `--no-ultrathink` flag to opt-out for simple tasks).

## Model Configuration

### Anthropic (Default)

amplihack works with Claude Code and Anthropic models out of the box. No
additional configuration needed.

### Azure OpenAI

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

### GitHub Copilot CLI

amplihack also supports GitHub Copilot CLI integration. See
[docs/github-copilot-litellm-integration.md](docs/github-copilot-litellm-integration.md)
for setup instructions.

## Features

### Remote Execution (Beta)

Distribute agentic work across Azure VMs:

```sh
amplihack remote auto "implement feature" --region westus3 --vm-size s
```

Documentation:
[.claude/tools/amplihack/remote/README.md](.claude/tools/amplihack/remote/README.md)

### Workflow Orchestration by Default (NEW!)

All prompts are automatically wrapped with `/amplihack:ultrathink` for maximum
effectiveness. This enables:

- Multi-agent workflow orchestration
- 13-step development workflow
- Automated architecture, building, and testing
- Philosophy compliance checking

**Benchmark results:** Amplihack without orchestration = vanilla Claude. The
orchestration IS the value!

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

### Goal-Seeking Agent Generator (NEW!)

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

**Learn more:** [Goal Agent Generator Guide](docs/GOAL_AGENT_GENERATOR_GUIDE.md)

---

## Quick Reference - Commands

| Command                        | Description                                             |
| ------------------------------ | ------------------------------------------------------- |
| `amplihack new`                | **NEW!** Generate goal-seeking agents from prompts      |
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

### Core Agents (6)

| Agent            | Purpose                                  |
| ---------------- | ---------------------------------------- |
| **api-designer** | API design and endpoint structure        |
| **architect**    | System design and architecture decisions |
| **builder**      | Code generation and implementation       |
| **optimizer**    | Performance optimization and efficiency  |
| **reviewer**     | Code quality and best practices review   |
| **tester**       | Test generation and validation           |

### Specialized Agents (23)

| Agent                       | Purpose                                         |
| --------------------------- | ----------------------------------------------- |
| **ambiguity**               | Clarify ambiguous requirements                  |
| **amplifier-cli-architect** | CLI tool design and architecture                |
| **analyzer**                | Deep code analysis                              |
| **azure-kubernetes-expert** | Azure Kubernetes Service expertise              |
| **ci-diagnostic-workflow**  | CI/CD pipeline diagnostics                      |
| **cleanup**                 | Remove artifacts and enforce philosophy         |
| **database**                | Database design and optimization                |
| **fallback-cascade**        | Resilient fallback strategies                   |
| **fix-agent**               | Automated error fixing                          |
| **integration**             | System integration patterns                     |
| **knowledge-archaeologist** | Extract and preserve knowledge                  |
| **memory-manager**          | Context and state management                    |
| **multi-agent-debate**      | Facilitate multi-perspective debates            |
| **n-version-validator**     | Validate N-version implementations              |
| **patterns**                | Design pattern recommendations                  |
| **pre-commit-diagnostic**   | Pre-commit hook diagnostics                     |
| **preference-reviewer**     | User preference validation                      |
| **prompt-writer**           | Effective prompt engineering                    |
| **rust-programming-expert** | Rust language expertise                         |
| **security**                | Security analysis and vulnerability detection   |
| **visualization-architect** | Data visualization design                       |
| **xpia-defense**            | Advanced threat detection                       |
| **philosophy-guardian**     | Philosophy compliance and simplicity validation |

## Core Concepts

### Workflow

Iterative multi-step development process (customizeable via DEFAULT_WORKFLOW.md)

1. Clarify requirements
2. Create issue
3. Setup branch
4. Design tests
5. Implement
6. Simplify
7. Test
8. Commit
9. Create PR
10. Review
11. Integrate feedback
12. Check philosophy
13. Prepare merge
14. Cleanup

### Philosophy

- **Simplicity** - Start simple, add only justified complexity
- **Modular** - Self-contained modules with clear interfaces
- **Working code** - No stubs or dead code
- **Test-driven** - Tests before implementation

## Configuration

amplihack works with Claude Code and Anthropic models by default. For additional
capabilities, you can configure Azure OpenAI integration.

### Azure OpenAI

Create `azure.env` with your credentials:

```env
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
```

**Security Warning**: Never commit API keys to version control. Use environment
variables or secure key management systems.

### Custom Workflows

The iterative-step workflow is fully customizable. Edit
`.claude/workflow/DEFAULT_WORKFLOW.md` to modify the development process -
changes apply immediately to `/ultrathink` and other commands. See
[docs/WORKFLOW_COMPLETION.md](docs/WORKFLOW_COMPLETION.md) for detailed
customization instructions.

### Project Structure

```
.claude/
├── agents/     # Agent definitions (core + specialized)
├── context/    # Philosophy and patterns
├── workflow/   # Development processes
└── commands/   # Slash commands
```

## Documentation

### Getting Started

- [Prerequisites](docs/PREREQUISITES.md) - Platform setup and dependencies
- [Proxy Configuration](docs/PROXY_CONFIG_GUIDE.md) - Azure OpenAI proxy setup

### Features

- [Auto Mode](docs/AUTO_MODE.md) - Autonomous agentic loop
- [Agent Bundles](docs/agent-bundle-generator-guide.md) - Custom agent creation
- [GitHub Copilot Integration](docs/github-copilot-litellm-integration.md) -
  Copilot CLI support
- [Office Skills](.claude/skills/README.md) - PDF, Excel, Word, and PowerPoint
  document processing
  - [PDF Skill](.claude/skills/pdf/README.md) - Comprehensive PDF manipulation
  - [XLSX Skill](.claude/skills/xlsx/README.md) - Spreadsheet creation with
    formulas and financial modeling

### Patterns

- [Workspace Pattern](docs/WORKSPACE_PATTERN.md) - Multi-project organization
  with git submodules

### Configuration

- [Hook Configuration](docs/HOOK_CONFIGURATION_GUIDE.md) - Session hooks
- [Workflow Customization](docs/WORKFLOW_COMPLETION.md) - Process customization

### Development

- [Developing amplihack](docs/DEVELOPING_AMPLIHACK.md) - Contributing guide
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md) - Architecture
  overview

### Methodology

- [Document-Driven Development](docs/document_driven_development/README.md) -
  Systematic approach for large features
- [DDD Overview](docs/document_driven_development/overview.md) - Comprehensive
  guide to DDD principles
- [Core Concepts](docs/document_driven_development/core_concepts/README.md) -
  Context poisoning, file crawling, retcon writing
- [DDD Phases](docs/document_driven_development/phases/README.md) - Step-by-step
  implementation guide

### Security

- [Security Recommendations](docs/SECURITY_RECOMMENDATIONS.md) - Best practices
- [Security Context Preservation](docs/SECURITY_CONTEXT_PRESERVATION.md) -
  Context handling

### Patterns

- [The Amplihack Way](docs/THIS_IS_THE_WAY.md) - Effective strategies for
  AI-agent development
- [Discoveries](docs/DISCOVERIES.md) - Documented problems, solutions, and
  learnings
- [Creating Tools](docs/CREATE_YOUR_OWN_TOOLS.md) - Build custom AI-powered
  tools

### Core Principles

- [Philosophy](.claude/context/PHILOSOPHY.md) - Core principles and patterns
- [Workflows](.claude/workflow/DEFAULT_WORKFLOW.md) - Development process

## Development

### Contributing

Fork, submit PRs. Add agents to `.claude/agents/`, patterns to
`.claude/context/PATTERNS.md`.

### Local Development

```sh
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git
cd MicrosoftHackathon2025-AgenticCoding
uv pip install -e .
amplihack launch
```

### Testing

```sh
pytest tests/
```

## Command Reference

| Task        | Command                               |
| ----------- | ------------------------------------- |
| Launch      | `amplihack launch`                    |
| With Azure  | Add `--with-proxy-config ./azure.env` |
| With repo   | Add `--checkout-repo owner/repo`      |
| From branch | Use `@branch-name` after URL          |
| Uninstall   | `amplihack uninstall`                 |

## License

MIT. See [LICENSE](LICENSE).
