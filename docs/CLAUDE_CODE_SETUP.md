# Claude Code Setup Guide

How to get Claude Code running with amplihack.

## What is Claude Code?

Claude Code is Anthropic's official CLI for AI-assisted software development. It runs in your terminal, reads your codebase, and helps you write, debug, and refactor code. Amplihack extends Claude Code with structured workflows, specialized agents, and persistent memory.

## Getting an API Key

Claude Code requires an Anthropic API key OR a Claude Max/Pro subscription:

**Option A: Anthropic API (pay-per-use)**

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys and create a new key
4. Set in your shell: `export ANTHROPIC_API_KEY=sk-ant-...`

**Option B: Claude Max subscription (flat rate)**

If you have a Claude Max subscription ($100/month as of Feb 2026), Claude Code is included. Run `claude` and follow the OAuth login flow.

## Cost Expectations

Claude Code usage with amplihack varies by task complexity:

| Task Type             | Typical Cost (API) | Tokens Used |
| --------------------- | ------------------ | ----------- |
| Q&A / quick question  | $0.01-0.05         | 1K-5K       |
| Single bug fix        | $0.50-3.00         | 50K-300K    |
| Feature with workflow | $2.00-15.00        | 200K-1.5M   |
| Parallel workstreams  | $5.00-30.00        | 500K-3M     |

Claude Max subscription eliminates per-token costs for qualifying usage.

## Installation

```bash
# macOS
brew install --cask claude-code

# Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash

# Windows
winget install Anthropic.ClaudeCode
```

Verify: `claude --version`

## Permanent Setup

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
# API key (skip if using Claude Max subscription)
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: enable native trace logging for debugging
export AMPLIHACK_TRACE_LOGGING=true
```

Then install amplihack:

```bash
# Try without installing (temporary)
uvx amplihack install

# Or install permanently
uv tool install amplihack
```

## Verify Everything Works

```bash
# Check Claude Code
claude --version

# Check amplihack
amplihack

# Launch Claude Code with amplihack agents
amplihack claude
```

## Next Steps

- [Prerequisites](PREREQUISITES.md) for full tool setup
- [Tutorial](tutorials/amplihack-tutorial.md) for hands-on learning
- [README](../README.md) for project overview
