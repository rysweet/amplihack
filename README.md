# amplihack

Development framework for Claude Code with specialized agents and automated
workflows.

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

Launches Claude Code with preconfigured agents. No installation needed.

## Quick Start

### Prerequisites

- Node.js 18+, npm, git
- uv ([astral.sh/uv](https://docs.astral.sh/uv/))

### Basic Usage

```sh
# Launch Claude Code with amplihack
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch

# With Azure OpenAI (requires azure.env configuration)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --with-proxy-config ./azure.env

# Work directly in a GitHub repository
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --checkout-repo owner/repo
```

### Commands in Claude Code

- `/ultrathink <task>` - Orchestrate agents for complex tasks
- `/analyze <path>` - Review code quality
- `/improve [target]` - Capture learnings
- `/fix [pattern]` - Fix common errors

## Core Concepts

### Agents

- **architect** - System design
- **builder** - Code generation
- **reviewer** - Code quality
- **tester** - Test generation
- **security** - Vulnerability checks
- **optimizer** - Performance

### Workflow

14-step development process:

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

Edit `.claude/workflow/DEFAULT_WORKFLOW.md` to customize. Changes apply
immediately.

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

## License

MIT. See [LICENSE](LICENSE).
