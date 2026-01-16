# Quick Start: Amplihack Hooks for GitHub Copilot CLI

Get the amplihack hooks working with GitHub Copilot CLI in 5 minutes.

## Prerequisites

```bash
# Install jq (required for JSON parsing)
# macOS
brew install jq

# Ubuntu/Debian
sudo apt install jq

# RHEL/Fedora
sudo dnf install jq
```

## Installation

### Option 1: Direct Usage (Recommended)

Use hooks directly from your project:

```bash
# Navigate to your project
cd /path/to/your/project

# Use Copilot CLI with amplihack hooks
copilot cli --hooks .github/hooks/amplihack-hooks.json
```

### Option 2: Global Configuration

Set as default for all projects:

```bash
# Copy hooks to Copilot config directory
mkdir -p ~/.config/copilot/hooks
cp -r .github/hooks/* ~/.config/copilot/hooks/

# Update Copilot config
cat >> ~/.config/copilot/config.json << 'EOF'
{
  "hooks": "~/.config/copilot/hooks/amplihack-hooks.json"
}
EOF
```

### Option 3: Project-Specific Config

Set for current project only:

```bash
# Create/update .copilot/config.json in project root
mkdir -p .copilot
cat > .copilot/config.json << 'EOF'
{
  "hooks": ".github/hooks/amplihack-hooks.json"
}
EOF
```

## Quick Test

Verify hooks are working:

```bash
# Test session-start hook
echo '{"prompt": "test"}' | bash .github/hooks/scripts/session-start.sh | jq .

# Test pre-tool-use validation (should block)
echo '{"toolUse":{"name":"Bash","input":{"command":"git commit --no-verify"}}}' | \
  bash .github/hooks/scripts/pre-tool-use.sh | jq .

# Test post-tool-use metrics
echo '{"toolUse":{"name":"Bash"},"result":{}}' | \
  bash .github/hooks/scripts/post-tool-use.sh | jq .
```

## Basic Usage

### Start a Session

```bash
# Session-start hook automatically:
# - Creates .claude/runtime/logs/{session_id}/
# - Injects user preferences
# - Loads project context
copilot cli
```

### Enable Lock Mode (Continuous Work)

```bash
# Enable autonomous operation
mkdir -p .claude/runtime/locks
touch .claude/runtime/locks/.lock_active

# Copilot will now continue working through TODOs without stopping

# Disable lock mode
rm .claude/runtime/locks/.lock_active
```

### View Logs

```bash
# Find latest session
ls -t .claude/runtime/logs/ | head -1

# View session logs
tail -f .claude/runtime/logs/{session_id}/*.log

# View metrics
cat .claude/runtime/metrics/*.jsonl | jq .
```

## Key Features

### 🔒 Lock Mode

Keep Copilot working autonomously until tasks complete:
- Create `.claude/runtime/locks/.lock_active`
- Session-end hook blocks stop and continues work
- Remove lock file to allow normal stop

### 🎯 User Preferences

Preferences automatically injected on every message:
- Stored in `.claude/context/USER_PREFERENCES.md`
- Includes communication style, verbosity, collaboration mode
- MANDATORY enforcement (cannot be optimized away)

### 🛡️ Safety Policies

Pre-tool-use hook blocks dangerous operations:
- `git commit --no-verify` (bypasses quality checks)
- Clear error messages explain why and what to do instead
- Cannot be disabled programmatically

### 📊 Metrics & Logging

All hooks log to `.claude/runtime/`:
- Per-session logs in `logs/{session_id}/`
- JSONL metrics in `metrics/`
- Structured error files in `errors/`

## Troubleshooting

### "jq: command not found"

Install jq (see Prerequisites section above)

### Hooks not running

Check Copilot configuration:
```bash
copilot cli config show
```

Verify hook script permissions:
```bash
chmod +x .github/hooks/scripts/*.sh
```

### Lock mode not working

Ensure lock flag exists:
```bash
ls -la .claude/runtime/locks/.lock_active
```

Check session-end.sh logs:
```bash
tail .claude/runtime/logs/*/session-end.log
```

## Next Steps

1. **Customize hooks**: Edit scripts in `.github/hooks/scripts/`
2. **Add preferences**: Edit `.claude/context/USER_PREFERENCES.md`
3. **View metrics**: Analyze `.claude/runtime/metrics/*.jsonl`
4. **Read docs**: See `.github/hooks/README.md` for details

## Examples

### Custom Continuation Prompt

```bash
# Set custom prompt for lock mode
mkdir -p .claude/runtime/locks
echo "Focus on test coverage and documentation" > \
  .claude/runtime/locks/.continuation_prompt

# Enable lock mode
touch .claude/runtime/locks/.lock_active
```

### Audit User Prompts

```bash
# View all prompts from latest session
cat .claude/runtime/logs/$(ls -t .claude/runtime/logs/ | head -1)/prompts_audit.jsonl | jq .
```

### Analyze Tool Usage

```bash
# Count tool usage by type
cat .claude/runtime/metrics/post_tool_use_metrics.jsonl | \
  jq -r '.tool' | sort | uniq -c | sort -rn
```

## Getting Help

- **Full documentation**: `.github/hooks/README.md`
- **Hook internals**: `.claude/tools/amplihack/hooks/README.md`
- **Issues**: https://github.com/rysweet/amplihack/issues
- **Converter**: `python src/amplihack/adapters/hooks_converter.py --help`

## Philosophy

These hooks align with amplihack's principles:

- ⚓ **Ruthless Simplicity**: Bash scripts do one thing well
- 🏴‍☠️ **Zero-BS**: Every function works or doesn't exist
- 🛡️ **Fail-Safe**: Hooks never break the CLI
- 📊 **Observable**: Comprehensive logging and metrics
- 🎯 **User Control**: Explicit and controllable behavior

Arrr, smooth sailing ahead! ⚓
