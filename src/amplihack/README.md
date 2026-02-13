# Amplihack CLI

Enhanced command-line interface for Claude Code with Azure OpenAI integration support.

## Features

- **Agent Installation**: Install specialized AI agents to `~/.claude`
- **Proxy Integration**: Launch Claude with Azure OpenAI proxy for persistence
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

# Launch with Azure OpenAI proxy (includes persistence prompt automatically)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --with-proxy-config ./azure.env
```

### Local Usage

If you have the package installed locally:

```bash
# Install agents
amplihack install

# Basic launch (no proxy)
amplihack launch

# Launch with proxy configuration (auto-includes Azure persistence prompt)
amplihack launch --with-proxy-config /path/to/.env
```

### Uninstall Agents

Remove all amplihack components from `~/.claude`:

```bash
amplihack uninstall
```

## Proxy Configuration

Create a `.env` file for proxy configuration:

```env
# Required
ANTHROPIC_API_KEY=your-api-key

# Optional Azure configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-key
```

See `examples/proxy-config.env.example` for a complete template.

## How It Works

1. **Directory Detection**: Searches for `.claude` directory in current or parent directories
2. **Proxy Setup**:
   - Clones `claude-code-proxy` if not present
   - Copies your `.env` configuration
   - Starts proxy server on localhost:8080
3. **Environment Configuration**: Sets `ANTHROPIC_BASE_URL` to point to local proxy
4. **Claude Launch**: Starts Claude with `--dangerously-skip-permissions` flag
5. **Cleanup**: Automatically stops proxy when Claude exits

## Module Structure

```
src/amplihack/
├── __init__.py         # Main module entry
├── cli.py              # Enhanced CLI implementation
├── proxy/              # Proxy management
│   ├── manager.py      # Proxy lifecycle
│   ├── config.py       # Configuration parsing
│   └── env.py          # Environment setup
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
- Node.js and npm (for proxy)
- Claude Code CLI installed

## Troubleshooting

### Proxy Won't Start

- Ensure Node.js and npm are installed
- Check that port 8080 is available
- Verify `.env` file has valid `ANTHROPIC_API_KEY`

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
- Only use with trusted proxy configurations

## Contributing

See the main repository README for contribution guidelines.
