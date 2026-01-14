# Amplifier Command Reference

Launch Microsoft Amplifier with the amplihack bundle for enhanced AI-assisted development.

## Synopsis

```bash
amplihack amplifier [OPTIONS] [-- AMPLIFIER_ARGS]
```

## Description

The `amplihack amplifier` command launches Microsoft Amplifier with the amplihack bundle automatically loaded. Amplifier is a multi-model AI development assistant that supports Claude, GPT-4, and other models through a unified interface.

**Key features:**

- Automatically discovers and loads the amplihack bundle
- Auto-installs Amplifier via `uv` if not present
- Supports model and provider selection
- Session resume capability
- Integration with amplihack's auto mode

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **uv** | Required for auto-installation. Install from [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **Amplifier** | Auto-installed on first run via `uv tool install` |
| **API Keys** | Configure for your chosen provider (Anthropic, OpenAI, Azure) |

## Options

### Session Control

| Option | Description |
|--------|-------------|
| `--resume SESSION_ID` | Resume an existing Amplifier session |
| `--print` | Single response mode (no tool use, no conversation) |

### Model Selection

| Option | Description |
|--------|-------------|
| `--model MODEL` | Model to use (e.g., `claude-sonnet-4-20250514`, `gpt-4o`) |
| `--provider PROVIDER` | Provider to use: `anthropic`, `openai`, `azure` |

### Auto Mode

| Option | Description |
|--------|-------------|
| `--auto` | Run in autonomous mode with task loop |
| `--max-turns N` | Maximum turns for auto mode (default: 10) |

### Common Options

| Option | Description |
|--------|-------------|
| `--no-reflection` | Disable post-session reflection analysis |

## Usage Examples

### Interactive Session

Start an interactive Amplifier session with the amplihack bundle:

```bash
amplihack amplifier
```

**Output:**
```
Using amplihack bundle: /path/to/amplifier-bundle
[Amplifier starts in interactive mode]
```

### Non-Interactive with Prompt

Execute a single task:

```bash
amplihack amplifier -- -p "Explain the authentication flow in this codebase"
```

### Single Response Mode

Get a single response without tool use:

```bash
amplihack amplifier --print -- -p "What does this function do?"
```

### Model Selection

Use a specific model:

```bash
# Use GPT-4o
amplihack amplifier --model gpt-4o --provider openai

# Use Claude Sonnet
amplihack amplifier --model claude-sonnet-4-20250514 --provider anthropic
```

### Resume a Session

Continue a previous session:

```bash
amplihack amplifier --resume session_20250114_120000_abc123
```

### Auto Mode

Run autonomously with a task:

```bash
amplihack amplifier --auto -- -p "Implement user authentication with JWT tokens"

# With extended turns for complex tasks
amplihack amplifier --auto --max-turns 25 -- -p "Refactor the entire API layer"
```

## Bundle Discovery

The command automatically finds the amplihack bundle using this search order:

1. **Current directory**: `./amplifier-bundle/bundle.md`
2. **Package location**: Searches up to 5 parent directories from the installed package

If no bundle is found, Amplifier runs without it and displays a warning:

```
Warning: amplihack bundle not found. Running Amplifier without bundle.
  Expected location: ./amplifier-bundle/bundle.md
```

## Installation Behavior

On first run, if Amplifier is not installed:

```
Installing Amplifier from git+https://github.com/microsoft/amplifier...
This will install Amplifier as a uv tool.
Continue? [y/N] y
✓ Amplifier CLI installed
```

**Non-interactive mode** (CI/scripts): Installation proceeds automatically without prompting.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AMPLIHACK_DEBUG` | Set to `true` for debug output (shows full command) |
| `ANTHROPIC_API_KEY` | API key for Anthropic models |
| `OPENAI_API_KEY` | API key for OpenAI models |
| `AZURE_OPENAI_*` | Azure OpenAI configuration |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (installation failed, command not found, etc.) |

## Troubleshooting

### Amplifier not found after installation

**Problem**: Installation succeeds but `amplifier` command not found.

**Solution**: Ensure `~/.local/bin` (or uv's tool bin directory) is in your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

### Bundle not found

**Problem**: Warning about missing bundle appears.

**Solution**: 
1. Run from the amplihack repository root
2. Or ensure `amplifier-bundle/bundle.md` exists in your project

### uv not found

**Problem**: Error message about missing `uv`.

**Solution**: Install uv:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### API key errors

**Problem**: Authentication errors when running.

**Solution**: Set the appropriate API key for your provider:

```bash
# For Anthropic (Claude models)
export ANTHROPIC_API_KEY="your-key"

# For OpenAI (GPT models)
export OPENAI_API_KEY="your-key"
```

## Comparison with Other Commands

| Command | Use Case |
|---------|----------|
| `amplihack amplifier` | Multi-model support, Amplifier features |
| `amplihack claude` | Claude Code with amplihack hooks and power steering |
| `amplihack copilot` | GitHub Copilot CLI integration |
| `amplihack codex` | OpenAI Codex CLI integration |

Choose `amplifier` when you need:
- Multi-model flexibility (switch between Claude, GPT-4, etc.)
- Amplifier-specific features
- The amplihack bundle context without full Claude Code hooks

## Related Documentation

- [Command Selection Guide](../commands/COMMAND_SELECTION_GUIDE.md) - Choose the right command
- [Auto Mode Guide](../AUTO_MODE.md) - Autonomous execution details
- [Launcher Model Configuration](./LAUNCHER_MODEL_CONFIGURATION.md) - Model selection for Claude launcher
