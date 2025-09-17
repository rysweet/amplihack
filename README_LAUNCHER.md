# Agentic Claude Launcher

Launch Claude Code with the Agentic Coding Framework from any project directory.

## Quick Start

From your target project directory:

```bash
npx @agentic/claude-launcher
```

Or if you have the repository locally:

```bash
npx /path/to/MicrosoftHackathon2025-AgenticCoding
```

## What It Does

This launcher:
1. Adds the framework directory (with .claude/ configs, agents, commands) to Claude's accessible directories
2. Adds your target project directory to Claude's accessible directories
3. Launches Claude with instructions to change its working directory to your project
4. Makes all framework capabilities available while working on your project

## Installation Options

### Option 1: Direct from GitHub (Recommended for now)
```bash
# Clone the framework
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding ~/agentic-framework

# From any project, use npx with the path
cd ~/my-project
npx ~/agentic-framework
```

### Option 2: Global Installation
```bash
# Install globally from the repository
cd ~/agentic-framework
npm link

# Now use from anywhere
cd ~/my-project
agentic-claude
```

### Option 3: NPX from npm (Once Published)
```bash
# Will work after publishing to npm
npx @agentic/claude-launcher
```

## How It Works

The launcher:
1. Detects your current working directory as the target project
2. Locates the framework directory (containing .claude/ configurations)
3. Launches Claude with both directories accessible via `--add-dir`
4. Provides Claude with instructions to change its working directory

## What Claude Sees

When launched, Claude receives:
- Access to the framework's `.claude/` directory with all agents, commands, and patterns
- Access to your target project directory
- Instructions to change working directory to your project
- Context about where the framework files are located

## Example Session

```bash
# In your web app project
cd ~/projects/my-web-app

# Launch Claude with the framework
npx ~/agentic-framework

# Claude starts with:
# - Framework agents and commands available
# - Your project files accessible
# - Instructions to work in your project directory
```

Inside Claude, you'll then have access to:
- All framework commands like `/ultrathink`, `/analyze`, `/improve`
- All specialized agents (architect, builder, reviewer, etc.)
- Framework patterns and philosophy
- Your project files for editing and analysis

## Troubleshooting

### "Claude CLI not found"
Install Claude Code from https://claude.ai/download

### "Framework .claude directory not found"
Ensure you're running from the correct framework location or set the path correctly.

### Need to use a different framework location
```bash
# Clone your own fork
git clone https://github.com/yourusername/agentic-framework ~/my-framework

# Use it with any project
cd ~/my-project
npx ~/my-framework
```

## Development

To modify the launcher:
1. Edit `bin/launch.js`
2. Test locally with `npm link`
3. Run from a test project directory

## How This Differs from Amplifier

Unlike the previous "amplifier" approach that required:
1. Starting Claude from within the framework directory
2. Using `--add-dir` to add your project
3. Manually telling Claude to change directories

This launcher:
- Can be run directly from your project directory
- Automatically sets up both directories
- Provides Claude with clear context and instructions
- Works via `npx` for easy invocation