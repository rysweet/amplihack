# amplihack

Development framework for Claude Code with specialized agents and automated
workflows.

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

Launches Claude Code with preconfigured agents. No installation needed.

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
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch

# With Azure OpenAI (requires azure.env configuration)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --with-proxy-config ./azure.env

# Work directly in a GitHub repository
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --checkout-repo owner/repo
```

Not sure where to start? Use the command above to run from uvx, then tell Claude
Code to `cd /path/to/my/project` and
`/amplihack:ultrathink <my first prompt here>`.

### Commands in Claude Code

- `/amplihack:ultrathink <task>` - Orchestrate agents for complex tasks
- `/amplihack:analyze <path>` - Review code quality
- `/amplihack:improve [target]` - Capture learnings
- `/amplihack:fix [pattern]` - Fix common errors
- `/amplihack:auto-mode <command>` - Persistent analysis and autonomous
  progression

## Core Concepts

### Agents

- **architect** - System design
- **builder** - Code generation
- **reviewer** - Code quality
- **tester** - Test generation
- **security** - Vulnerability checks
- **optimizer** - Performance

### Workflow

14-step development process (customizeable via DEFAULT_WORKLOFW.md)

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

# Create `azure.env` with your credentials:

### Azure OpenAI Integration

Use Azure OpenAI models with Claude Code interface through automatic proxy
setup.

#### Quick Setup (< 5 minutes)

```bash
# 1. Copy and edit example configuration
cp examples/example.azure.env .azure.env
# Edit .azure.env with your Azure credentials

# 2. Launch with Azure integration
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --with-proxy-config ./.azure.env
```

#### Example Configuration

> > > > > > > origin/feat/issue-676-azure-openai-proxy

```env
# Required: Azure credentials and endpoint
OPENAI_API_KEY="your-azure-api-key"  # pragma: allowlist secret
OPENAI_BASE_URL="https://myai.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2025-01-01-preview"

# Model mapping to your Azure deployments
BIG_MODEL="gpt-4"
MIDDLE_MODEL="gpt-4"
SMALL_MODEL="gpt-4o-mini"

# Performance settings for large context
REQUEST_TIMEOUT="300"
MAX_TOKENS_LIMIT="512000"
MAX_RETRIES="2"
```

### Custom Workflows

The 14-step workflow is fully customizable. Edit
`.claude/workflow/DEFAULT_WORKFLOW.md` to modify the development process -
changes apply immediately to `/ultrathink` and other commands. See
[docs/WORKFLOW_CUSTOMIZATION.md](docs/WORKFLOW_CUSTOMIZATION.md) for detailed
customization instructions.

### Project Structure

```
.claude/
├── agents/     # Agent definitions
├── context/    # Philosophy and patterns
├── workflow/   # Development processes
└── commands/   # Slash commands
```

## Documentation

- [Prerequisites](docs/PREREQUISITES.md) - Platform setup
- [Agent Bundles](docs/agent-bundle-generator-guide.md) - Custom agents
- [Philosophy](.claude/context/PHILOSOPHY.md) - Core principles
- [Workflows](.claude/workflow/DEFAULT_WORKFLOW.md) - Process customization

## Development

### Contributing

Fork, submit PRs. Add agents to `.claude/agents/`, patterns to
`.claude/context/PATTERNS.md`.

### Local Development

```sh
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git
cd MicrosoftHackathon2025-AgenticCoding
uv pip install -e .
uvx amplihack launch
```

For complete setup instructions, troubleshooting, and advanced configuration,
see **[Azure Integration Guide](docs/AZURE_INTEGRATION.md)**

### Testing

```sh
pytest tests/
```

## Command Reference

| Task        | Command                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------- |
| Launch      | `uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch` |
| With Azure  | Add `--with-proxy-config ./azure.env`                                                             |
| With repo   | Add `--checkout-repo owner/repo`                                                                  |
| From branch | Use `@branch-name` after URL                                                                      |
| Uninstall   | `uvx [...] amplihack uninstall`                                                                   |

## Auto-Mode

Auto-Mode provides persistent conversation analysis and autonomous progression
through complex objectives using the Claude Agent SDK for real-time analysis.

### What is Auto-Mode?

Auto-Mode monitors your Claude Code sessions, analyzes progress toward user
objectives, and automatically generates next prompts to maintain momentum and
ensure completion of complex tasks. It uses real Claude AI (via the Claude Agent
SDK) to understand context, evaluate progress, and make informed
recommendations.

### CLI Usage

The `amplihack auto` command provides CLI access to auto-mode functionality:

```sh
# Start auto-mode session
amplihack auto start

# Start with specific configuration
amplihack auto start --config learning_mode

# Check current status
amplihack auto status

# Check detailed status
amplihack auto status --detailed

# Request immediate analysis
amplihack auto analyze --type comprehensive --output json

# Configure settings
amplihack auto configure analysis_frequency high

# Stop auto-mode
amplihack auto stop
```

### Slash Command Usage

Within Claude Code sessions, use the `/amplihack:auto-mode` slash command:

```
# Start an auto-mode session with an objective
/amplihack:auto-mode start "Build a REST API with authentication and user management"

# Process Claude's output and get next steps
/amplihack:auto-mode process "I've implemented the authentication system with JWT tokens"

# Check progress
/amplihack:auto-mode status

# Pause/resume session
/amplihack:auto-mode pause
/amplihack:auto-mode resume

# Stop session
/amplihack:auto-mode stop
```

### Common Examples

**CLI - Start and Monitor:**

```sh
# Start with aggressive analysis configuration
amplihack auto start --config aggressive_analysis

# Monitor progress
amplihack auto status --detailed

# Get comprehensive analysis as JSON
amplihack auto analyze --type comprehensive --output json
```

**Slash Command - Autonomous Development:**

```
# Start objective-driven development
/amplihack:auto-mode start "Implement user authentication with OAuth2 and JWT" --max-iterations 50

# Auto-mode will analyze each response and suggest next steps
# It maintains context and ensures objective completion
```

### Configuration Options

Auto-mode supports multiple configuration presets:

- `default` - Balanced analysis and intervention (threshold: 0.7)
- `aggressive_analysis` - High-frequency analysis (threshold: 0.5)
- `minimal_intervention` - Low-frequency, high-confidence only (threshold: 0.9)
- `learning_mode` - Educational focus with adaptive analysis (threshold: 0.6)
- `privacy_focused` - Strict privacy, no background mode (threshold: 0.8)

### Key Features

- **Real-Time Analysis** - Uses Claude Agent SDK for genuine AI understanding
- **Progress Evaluation** - Measures advancement toward objectives
- **Quality Assessment** - Reviews code quality and best practices
- **Next Prompt Generation** - Creates specific, actionable next steps
- **Session Management** - Persistent state that survives restarts
- **TDD Integration** - Monitors test implementation and coverage

For complete documentation, see
[.claude/commands/amplihack/auto_mode.md](.claude/commands/amplihack/auto_mode.md).

## License

MIT. See [LICENSE](LICENSE).

# Test change
