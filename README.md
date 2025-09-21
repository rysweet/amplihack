# Microsoft Hackathon 2025 - Agentic Coding Framework

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

**No installation needed.** Launch Claude Code with AI-powered agents that
accelerate software development through automation, code generation, and
collaborative problem-solving.

---

## Quick Start

### Basic Usage

Launch Claude Code with the amplihack framework from any directory:

```sh
# Launch with latest version (recommended)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

That's it! The command automatically:

- Downloads the latest framework
- Sets up the environment
- Launches Claude Code with all agents configured
- No local installation required

### Advanced Usage

**With Azure OpenAI Integration:**

For using claude code and the amplihack frameowrk with Azure OpenAI models:

- Copy `example.azure.env` to `.azure.env` and then edit it with your Azure
  OpenAI endpoint settings
- Launch amplichack with the proxy to Azure OpenAI:
-

```sh
# Launch with Azure OpenAI proxy (includes persistence prompt)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --with-proxy-config ./azure.env
```

The Azure integration provides:

- Dynamicaly loaded proxy
- Azure OpenAI model access through Claude Code interface
- Automatic persistence prompt for autonomous operation

**From a Specific Branch:**

For testing features or specific versions:

```sh
# Launch from a development branch
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding@branch-name amplihack launch
```

---

## Installation (For Developers Only)

> **Note:** Installation is NOT required for using amplihack. The `uvx` commands
> above work without any installation. This section is only for developers who
> want to modify the framework itself.

### Development Setup

If you're contributing to the framework:

```sh
# Clone and install in development mode
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git
cd MicrosoftHackathon2025-AgenticCoding
uv pip install -e .

# Run locally installed version
uvx amplihack launch
```

### Requirements for Development

- Python 3.x
- git
- [uv/uvx](https://github.com/astral-sh/uv) - Modern Python package manager

### Uninstall

Remove amplihack configuration (does not affect Claude Code):

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack uninstall
```

---

## Features

### AI-Powered Development Agents

The framework includes specialized agents for every aspect of development:

- **Architect Agent**: System design and specifications
- **Builder Agent**: Code generation from specs
- **Reviewer Agent**: Philosophy compliance and code review
- **Tester Agent**: Test generation and validation
- **Security Agent**: Vulnerability assessment
- **Optimizer Agent**: Performance bottleneck analysis
- **Cleanup Agent**: Code simplification
- And many more specialized agents

### Default Coding Workflow

A standardized 13-step workflow ensures consistency and quality:

1. **Requirements Clarification**: Understand the task completely
2. **Issue Creation**: Track work in GitHub
3. **Branch Setup**: Isolated development environment
4. **TDD Design**: Tests before implementation
5. **Implementation**: Build with philosophy compliance
6. **Simplification**: Remove unnecessary complexity
7. **Testing**: Comprehensive validation
8. **Committing**: Clear, atomic commits
9. **PR Creation**: Detailed pull requests
10. **Review**: Code and philosophy checks
11. **Feedback**: Implement review suggestions
12. **Philosophy Check**: Final compliance validation
13. **Merge Ready**: Clean, tested, documented code

The workflow is customizable via `.claude/workflow/DEFAULT_WORKFLOW.md`.

### Development Philosophy

The framework enforces key principles:

- **Ruthless Simplicity**: Start simple, add complexity only when justified
- **Modular Design**: Self-contained "bricks" with clear "studs" (interfaces)
- **Zero-BS Implementation**: No stubs, placeholders, or dead code
- **Test-Driven Development**: Tests define contracts before implementation
- **Continuous Learning**: Document discoveries and patterns

### Project Structure

```
.claude/
├── agents/           # Specialized AI agents
├── context/          # Philosophy and patterns
├── workflow/         # Development workflows
├── commands/         # Slash commands (/ultrathink, /analyze, /improve)
└── runtime/          # Logs and metrics

src/amplihack/        # CLI implementation
Specs/                # Module specifications
```

### Key Commands

**Within Claude Code:**

- `/ultrathink <task>` - Deep analysis using multiple agents
- `/analyze <path>` - Comprehensive code review
- `/improve [target]` - Self-improvement and learning capture

**CLI Commands:**

- `amplihack launch` - Start Claude Code with agents
- `amplihack launch --with-proxy-config` - Use Azure OpenAI
- `amplihack uninstall` - Remove configuration

---

## Configuration

### Azure OpenAI Setup

Create an `azure.env` file with your Azure OpenAI credentials:

```env
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
```

Then launch with:

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --with-proxy-config ./azure.env
```

### Customizing Workflows

Edit `.claude/workflow/DEFAULT_WORKFLOW.md` to customize the development
workflow:

```sh
# Open workflow in your editor
$EDITOR .claude/workflow/DEFAULT_WORKFLOW.md
```

Changes take effect immediately - no restart needed.

---

## Contributing

We welcome contributions! The framework is designed to be extended:

1. **Create new agents** in `.claude/agents/`
2. **Document patterns** in `.claude/context/PATTERNS.md`
3. **Share discoveries** in `DISCOVERIES.md`
4. **Improve workflows** in `.claude/workflow/`

Fork the repository and submit pull requests with your improvements.

---

## License

This project is licensed under the MIT License.

---

## Quick Command Reference

| Task               | Command                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| Launch Claude Code | `uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch` |
| With Azure OpenAI  | Add `--with-proxy-config ./azure.env`                                                             |
| From branch        | Use `@branch-name` after repo URL                                                                 |
| Developer setup    | Clone repo and `uv pip install -e .`                                                              |

---

Built with ❤️ for Microsoft Hackathon 2025
