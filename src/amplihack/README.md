# Amplihack CLI

Enhanced command-line interface for Claude Code with Azure OpenAI integration support.

## Features

- **Agent Installation**: Install specialized AI agents to `~/.claude`
- **Smart Directory Detection**: Automatically finds `.claude` directories
- **System Prompt Enhancement**: Append custom prompts for specialized contexts
- **Cross-platform Support**: Works on Windows, macOS, and Linux

## Installation

```bash
# Clone the repository
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding
cd MicrosoftHackathon2025-AgenticCoding

# Install the package
pip install -e .
```

## Usage

### Quick Start with uvx (No Clone Required)

Run directly from GitHub without cloning:

```bash
# Install agents
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack install

# Launch Claude Code
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

### Local Usage

If you have the package installed locally:

```bash
# Install agents
amplihack install

# Launch Claude Code
amplihack launch
```

### Uninstall Agents

Remove all amplihack components from `~/.claude`:

```bash
amplihack uninstall
```

## How It Works

1. **Directory Detection**: Searches for `.claude` directory in current or parent directories
2. **Environment Configuration**: Sets up the appropriate environment for Claude
3. **Claude Launch**: Starts Claude with `--dangerously-skip-permissions` flag

## Module Structure

```
src/amplihack/
├── __init__.py         # Main module entry
├── cli.py              # Enhanced CLI implementation
├── launcher/           # Claude launcher
│   ├── core.py         # Launch logic
│   └── detector.py     # Directory detection
├── utils/              # Utilities
│   ├── process.py      # Process management
│   └── paths.py        # Path resolution
└── prompts/            # System prompts
    └── azure_persistence.md
```

## Requirements

- Python 3.8+
- Git
- Claude Code CLI installed

## Troubleshooting

### Claude Not Found

- Install Claude Code CLI using the recommended method for your platform:
  - macOS: `brew install --cask claude-code` or `curl -fsSL https://claude.ai/install.sh | bash`
  - Linux/WSL: `curl -fsSL https://claude.ai/install.sh | bash`
  - Windows: `winget install Anthropic.ClaudeCode` or `irm https://claude.ai/install.ps1 | iex`
- For more options, see: https://code.claude.com/docs/en/setup
- Ensure `claude` command is in your PATH

### Permission Issues

- The tool uses `--dangerously-skip-permissions` flag
- This bypasses Claude's normal permission prompts

## Contributing

See the main repository README for contribution guidelines.
