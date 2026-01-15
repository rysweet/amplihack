# Copilot CLI Setup and Integration

This document explains the Copilot CLI integration that ensures agents are automatically synchronized between `.claude/agents/` and `.github/agents/`.

## Overview

The Copilot CLI integration provides:

1. **Startup Hook**: Automatically checks and syncs agents at session start
2. **Setup Command**: One-command setup for complete Copilot integration
3. **Configuration**: User-controlled auto-sync preferences
4. **Fast Performance**: < 500ms staleness check, < 2s full sync

## Quick Start

```bash
# Complete setup (recommended)
amplihack setup-copilot

# Setup without initial sync
amplihack setup-copilot --skip-sync
```

## What Gets Created

The `setup-copilot` command creates:

```
.github/
├── agents/                           # Mirrored agents from .claude/agents/
│   ├── REGISTRY.json                # Auto-generated agent catalog
│   └── amplihack/                   # Agent hierarchy preserved
│       ├── core/
│       │   ├── architect.md
│       │   ├── builder.md
│       │   └── ...
│       └── specialized/
│           └── ...
└── hooks/
    ├── pre-commit.json              # Sample pre-commit hook config
    └── amplihack-hooks.json         # Copilot sync preferences
```

## How It Works

### Startup Hook

The `copilot_session_start.py` hook runs automatically when Claude Code starts:

1. **Environment Detection**: Checks if running in Copilot CLI environment
2. **Staleness Check**: Compares timestamps between `.claude/agents/` and `.github/agents/`
3. **User Preference**: Respects `copilot_auto_sync_agents` setting
4. **Auto-Sync**: Syncs agents if missing or stale

**Performance**:
- Staleness check: < 500ms
- Full sync: < 2 seconds for 36-50 agents

### Sync Process

Agent synchronization:

1. Copies all `.md` files from `.claude/agents/` to `.github/agents/`
2. Preserves directory structure
3. Generates `REGISTRY.json` with agent metadata
4. Updates timestamps for staleness tracking

### Configuration

**Auto-sync preferences** (`.claude/config.json` or `.github/hooks/amplihack-hooks.json`):

```json
{
  "copilot_auto_sync_agents": "ask",  // "always", "never", or "ask"
  "copilot_sync_on_startup": true     // Enable/disable startup sync
}
```

**Setting preferences**:

```bash
# Via config file (manual)
echo '{"copilot_auto_sync_agents": "always"}' > .claude/config.json

# Via hook prompt (interactive)
# When prompted at session start, choose "always" or "never"
```

## Usage Examples

### Manual Sync

```bash
# Sync agents manually
python .claude/tools/amplihack/sync_agents.py .claude/agents .github/agents

# Or use the CLI (after installation)
amplihack sync-agents
```

### Using Synced Agents in Copilot CLI

```bash
# Reference agent in prompt
copilot -p "Design authentication system" \
  -f @.github/agents/amplihack/core/architect.md

# Multiple agents
copilot -p "Review security" \
  -f @.github/agents/amplihack/core/security.md \
  -f @.github/agents/amplihack/core/reviewer.md
```

### Agent Registry

The auto-generated `REGISTRY.json` provides agent discovery:

```json
{
  "version": "1.0",
  "generated": "auto",
  "agents": {
    "amplihack/core/architect": {
      "path": "amplihack/core/architect.md",
      "name": "Architect",
      "description": "System design and problem decomposition specialist...",
      "tags": ["design", "architecture"],
      "invocable_by": ["cli", "workflow"]
    }
  }
}
```

## Troubleshooting

### Sync Not Happening

**Check environment detection**:
```bash
# Verify Copilot environment indicators
echo $GITHUB_COPILOT_CLI
ls -la .github/copilot-instructions.md
```

**Check preferences**:
```bash
# View current preference
cat .claude/config.json | grep copilot_auto_sync_agents

# Reset to default (ask)
echo '{"copilot_auto_sync_agents": "ask"}' > .claude/config.json
```

### Sync Failing

**Check source directory**:
```bash
# Ensure .claude/agents/ exists
ls -la .claude/agents/

# Count agents
find .claude/agents/ -name "*.md" | wc -l
```

**Check permissions**:
```bash
# Verify write permissions
mkdir -p .github/agents
touch .github/agents/test.txt && rm .github/agents/test.txt
```

### Stale Agents Not Updating

**Force sync**:
```bash
# Remove .github/agents/ to force full sync
rm -rf .github/agents/
amplihack setup-copilot
```

**Manual timestamp check**:
```bash
# Compare modification times
find .claude/agents/ -name "*.md" -printf "%T@ %p\n" | sort -n | tail -1
find .github/agents/ -name "*.md" -printf "%T@ %p\n" | sort -n | tail -1
```

## Architecture

### Files Created

1. **`.claude/tools/amplihack/hooks/copilot_session_start.py`**
   - Session start hook for Copilot CLI
   - Environment detection
   - Staleness checking
   - User preference handling

2. **`.claude/tools/amplihack/sync_agents.py`**
   - Core synchronization logic
   - Registry generation
   - Metadata extraction

3. **`.claude/config.json`**
   - Global configuration
   - Auto-sync preferences

4. **Integration in `session_start.py`**
   - Calls Copilot hook if environment detected
   - Fail-safe error handling

### Design Principles

**Non-intrusive**:
- Runs only in Copilot environment
- < 500ms overhead for staleness check
- No impact on Claude Code performance

**User-controlled**:
- Three preference modes: always, never, ask
- Explicit setup command
- Clear user feedback

**Fail-safe**:
- Errors don't break session start
- Graceful degradation
- Clear error messages

**Fast**:
- Staleness check: < 500ms
- Full sync: < 2s for 50 agents
- Minimal file I/O

## Testing

**Test startup hook**:
```bash
# Simulate Copilot environment
export GITHUB_COPILOT_CLI=1
python .claude/tools/amplihack/hooks/copilot_session_start.py
```

**Test sync script**:
```bash
# Direct execution
python .claude/tools/amplihack/sync_agents.py .claude/agents .github/agents

# Via CLI
amplihack sync-agents --verbose
```

**Test setup command**:
```bash
# Full setup
amplihack setup-copilot

# Dry run (setup without sync)
amplihack setup-copilot --skip-sync
```

## Integration with Existing Workflows

The Copilot integration is designed to work seamlessly with:

- **Claude Code workflows**: No impact on Claude Code usage
- **Git workflows**: .github/ directory is committed to repository
- **CI/CD**: Registry.json can be used for agent validation
- **Team collaboration**: Shared agent mirror in .github/

## Future Enhancements

Potential improvements (not yet implemented):

1. **Bidirectional sync**: Sync changes from .github/ back to .claude/
2. **Selective sync**: Sync only specific agent categories
3. **Conflict resolution**: Handle concurrent modifications
4. **Webhook integration**: Auto-sync on git push
5. **Agent versioning**: Track agent changes over time

## See Also

- `COPILOT_CLI.md` - Complete Copilot CLI guide
- `docs/architecture/COPILOT_VS_CLAUDE.md` - Architecture comparison
- `.github/agents/REGISTRY.json` - Agent catalog
