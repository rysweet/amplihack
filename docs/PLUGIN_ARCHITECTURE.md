# Plugin Architecture

Complete technical architecture fer amplihack's Claude Code plugin system.

## Overview

Amplihack uses Claude Code's plugin architecture t' provide global installation and cross-project access t' agents, commands, skills, and hooks. The plugin installs at `~/.amplihack/.claude/` and be discoverable by all Claude Code sessions.

## Architecture

```
Plugin Architecture
┌─────────────────────────────────────────────────────────────┐
│                 Claude Code Plugin System                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ~/.claude/settings.json                             │  │
│  │  {                                                    │  │
│  │    "enabledPlugins": ["amplihack"],                  │  │
│  │    "extraKnownMarketplaces": [{                      │  │
│  │      "name": "amplihack",                            │  │
│  │      "url": "https://github.com/rysweet/amplihack"  │  │
│  │    }]                                                │  │
│  │  }                                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ~/.amplihack/.claude-plugin/                        │  │
│  │  ├── plugin.json      # Plugin manifest              │  │
│  │  └── config.yaml      # Plugin configuration         │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ~/.amplihack/.claude/  (Plugin Content)             │  │
│  │  ├── agents/          # Specialized AI agents        │  │
│  │  ├── commands/        # Slash commands               │  │
│  │  ├── skills/          # Reusable capabilities        │  │
│  │  ├── tools/                                          │  │
│  │  │   └── amplihack/                                  │  │
│  │  │       └── hooks/   # Lifecycle hooks              │  │
│  │  │           ├── hooks.json                          │  │
│  │  │           ├── session_start.py                    │  │
│  │  │           ├── stop.py                             │  │
│  │  │           ├── pre_tool_use.py                     │  │
│  │  │           ├── post_tool_use.py                    │  │
│  │  │           ├── user_prompt_submit.py               │  │
│  │  │           └── pre_compact.py                      │  │
│  │  ├── workflow/       # DEFAULT_WORKFLOW.md           │  │
│  │  └── context/        # PHILOSOPHY.md, PATTERNS.md    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Plugin Manifest

The plugin manifest (`~/.amplihack/.claude-plugin/plugin.json`) defines the plugin structure:

```json
{
  "name": "amplihack",
  "version": "0.9.0",
  "description": "AI-powered development framework with specialized agents and automated workflows for Claude Code",
  "author": {
    "name": "Microsoft Amplihack Team",
    "url": "https://github.com/rysweet/amplihack"
  },
  "homepage": "https://github.com/rysweet/amplihack",
  "repository": "https://github.com/rysweet/amplihack",
  "license": "MIT",
  "keywords": ["claude-code", "ai", "agents", "workflows", "automation", "development"],
  "commands": ["./.claude/commands/"],
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/",
  "hooks": "./.claude/tools/amplihack/hooks/hooks.json",
  "marketplace": {
    "name": "amplihack",
    "url": "https://github.com/rysweet/amplihack",
    "type": "github",
    "description": "Official amplihack plugin marketplace"
  }
}
```

## Hook Registration

All hooks use `${CLAUDE_PLUGIN_ROOT}` variable substitution t' reference the plugin installation directory. This ensures hooks work from any project directory.

**Hook Configuration (`hooks.json`):**

```json
{
  "SessionStart": {
    "script": "${CLAUDE_PLUGIN_ROOT}/.claude/tools/amplihack/hooks/session_start.py",
    "description": "Initialize amplihack session with environment setup"
  },
  "Stop": {
    "script": "${CLAUDE_PLUGIN_ROOT}/.claude/tools/amplihack/hooks/stop.py",
    "description": "Cleanup and save session state"
  },
  "PreToolUse": {
    "script": "${CLAUDE_PLUGIN_ROOT}/.claude/tools/amplihack/hooks/pre_tool_use.py",
    "description": "Intercept tool calls for validation and routing"
  },
  "PostToolUse": {
    "script": "${CLAUDE_PLUGIN_ROOT}/.claude/tools/amplihack/hooks/post_tool_use.py",
    "description": "Process tool results and capture metrics"
  },
  "UserPromptSubmit": {
    "script": "${CLAUDE_PLUGIN_ROOT}/.claude/tools/amplihack/hooks/user_prompt_submit.py",
    "description": "Wrap user prompts with workflow orchestration"
  },
  "PreCompact": {
    "script": "${CLAUDE_PLUGIN_ROOT}/.claude/tools/amplihack/hooks/pre_compact.py",
    "description": "Context preservation before compaction"
  }
}
```

**Key Points:**
- All hooks use `${CLAUDE_PLUGIN_ROOT}` fer absolute paths
- Hooks be loaded once when plugin initializes
- Changes t' hooks require plugin reinstall or Claude Code restart

## Plugin Installation

The `PluginManager` class handles plugin installation from git repositories or local directories.

**Installation Flow:**

```
User executes: amplihack plugin install <source>
                      │
                      ▼
         ┌────────────────────────┐
         │  PluginManager.install │
         └────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
    Git Clone              Copy Local Directory
    to temp dir            to temp dir
         │                         │
         └────────────┬────────────┘
                      ▼
         ┌────────────────────────┐
         │ Validate plugin.json   │
         └────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │ Copy to ~/.amplihack/  │
         └────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │ Update settings.json   │
         │ - enabledPlugins       │
         │ - extraKnownMarketplaces│
         └────────────────────────┘
                      │
                      ▼
              ✅ Installation Complete
```

**Install Methods:**

```python
# From Git URL
amplihack plugin install https://github.com/rysweet/amplihack

# From local directory
amplihack plugin install /path/to/amplihack

# Force overwrite existing
amplihack plugin install --force https://github.com/rysweet/amplihack
```

## Settings Integration

Plugin installation updates `~/.claude/settings.json`:

```json
{
  "enabledPlugins": ["amplihack"],
  "extraKnownMarketplaces": [
    {
      "name": "amplihack",
      "url": "https://github.com/rysweet/amplihack"
    }
  ],
  "hooks": {
    "SessionStart": {
      "script": "${CLAUDE_PLUGIN_ROOT}/.claude/tools/amplihack/hooks/session_start.py"
    }
    // ... other hooks ...
  }
}
```

**Key Properties:**
- `enabledPlugins`: Array o' plugin names t' load
- `extraKnownMarketplaces`: Plugin discovery sources
- `hooks`: Lifecycle hook registrations with `${CLAUDE_PLUGIN_ROOT}` paths

## Backward Compatibility

The plugin system maintains backward compatibility with per-project `~/.amplihack/.claude/` installations:

**Mode Detection Precedence:**
1. **LOCAL**: Project has `~/.amplihack/.claude/` directory → Use project-local
2. **PLUGIN**: Plugin installed at `~/.amplihack/.claude/` → Use plugin
3. **NONE**: No installation found → Prompt user t' install

**Migration Commands:**

```bash
# Check current mode
amplihack mode status

# Migrate project to plugin (removes local .claude/)
amplihack mode migrate-to-plugin

# Create local .claude/ from plugin (for customization)
amplihack mode migrate-to-local

# Force plugin mode for one session
AMPLIHACK_MODE=plugin amplihack launch
```

## Cross-Tool Compatibility

### Claude Code ✅
- **Status**: Fully supported
- **Installation**: `amplihack plugin install`
- **Features**: Hooks, agents, commands, skills, marketplace

### GitHub Copilot ⚠️
- **Status**: Partial compatibility
- **Installation**: Manual copy t' project `~/.amplihack/.claude/` directory
- **Limitations**: No plugin system (yet), hooks may not work
- **Workaround**: Use per-project installation mode

### Codex ⚠️
- **Status**: Unknown - requires research
- **Installation**: Test with per-project mode first
- **Limitations**: Plugin support unknown
- **Workaround**: Use per-project installation mode

## Plugin Commands

```bash
# Install plugin from git URL
amplihack plugin install https://github.com/rysweet/amplihack

# Install from local directory
amplihack plugin install /path/to/amplihack

# Uninstall plugin
amplihack plugin uninstall amplihack

# Verify installation
amplihack plugin verify amplihack

# Show current mode
amplihack mode status

# Migration
amplihack mode migrate-to-plugin
amplihack mode migrate-to-local
```

## Plugin Verification

The `plugin verify` command checks three levels:

```
Plugin Verification Checklist
├─ ✅ Installed: Plugin directory exists at ~/.amplihack/.claude/
├─ ✅ Discoverable: Plugin listed in ~/.claude/settings.json
└─ ✅ Hooks loaded: hooks.json exists and be valid
```

**Example Output:**

```
$ amplihack plugin verify amplihack
Plugin: amplihack
  Installed: ✅
  Discoverable: ✅
  Hooks loaded: ✅

Plugin be fully functional!
```

## Security Considerations

- **Plugin Source Validation**: Only install plugins from trusted sources
- **Hook Execution**: All hooks run with same permissions as Claude Code
- **Path Traversal**: `${CLAUDE_PLUGIN_ROOT}` be validated before resolution
- **Settings Backup**: Settings.json be backed up before modification

## Performance

- **One-Time Load**: Plugin content loaded once per Claude Code session
- **Hook Overhead**: Minimal (<10ms per hook invocation)
- **Shared Memory**: Single plugin instance serves all projects
- **Disk Space**: Plugin requires ~50MB (agents, commands, skills)

## Troubleshooting

### Plugin Not Discovered

**Symptom**: Commands and agents not available

**Diagnosis**:
```bash
amplihack plugin verify amplihack
```

**Solutions**:
1. Check `~/.claude/settings.json` contains plugin name
2. Verify plugin directory exists at `~/.amplihack/.claude/`
3. Restart Claude Code t' reload plugin

### Hooks Not Loading

**Symptom**: Session start/stop hooks not executing

**Diagnosis**:
```bash
cat ~/.amplihack/.claude/tools/amplihack/hooks/hooks.json
```

**Solutions**:
1. Verify `hooks.json` be valid JSON
2. Check all hook scripts exist at specified paths
3. Verify `${CLAUDE_PLUGIN_ROOT}` variable be set
4. Reinstall plugin: `amplihack plugin install --force`

### Mode Conflicts

**Symptom**: Plugin and local `~/.amplihack/.claude/` both present

**Diagnosis**:
```bash
amplihack mode status
```

**Solutions**:
- Local takes precedence by design (expected behavior)
- T' use plugin, migrate: `amplihack mode migrate-to-plugin`
- T' use local, keep both (local overrides plugin)

## References

- Plugin Manifest: `~/.amplihack/.claude-plugin/plugin.json`
- Hook Configuration: `~/.amplihack/.claude/tools/amplihack/hooks/hooks.json`
- Settings Generator: `src/amplihack/settings_generator/generator.py`
- Plugin Manager: `src/amplihack/plugin_manager/manager.py`
- Mode Detector: `src/amplihack/mode_detector/detector.py`

## Next Steps

- **Install Plugin**: See [README.md Plugin Section](../README.md#plugin-installation)
- **Migrate Project**: See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
- **Customize**: Create local `~/.amplihack/.claude/` fer project-specific agents
