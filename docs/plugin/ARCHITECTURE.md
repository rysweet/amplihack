# Plugin Architecture

Understanding how amplihack's centralized plugin architecture works.

## Overview

Amplihack uses a centralized plugin architecture where all framework code lives in `~/.amplihack/.claude/` and is shared across all projects. This eliminates per-project duplication and simplifies updates.

## Why Plugin Architecture?

### The Problem with Per-Project Deployment

Before the plugin architecture, amplihack deployed a complete `.claude/` directory into every project:

```
project1/.claude/  (5.2 MB)
project2/.claude/  (5.2 MB)
project3/.claude/  (5.2 MB)
```

**Issues:**

- 5.2 MB × N projects = significant disk waste
- Updates required running `amplihack upgrade` in every project
- Version drift when projects weren't updated
- Merge conflicts when multiple developers updated independently

### The Plugin Solution

With plugin architecture, framework code lives centrally:

```
~/.amplihack/.claude/          (5.2 MB - shared)
project1/.claude/settings.json (< 1 KB)
project2/.claude/settings.json (< 1 KB)
project3/.claude/settings.json (< 1 KB)
```

**Benefits:**

- Single installation for all projects
- One command updates all projects: `amplihack plugin install --upgrade`
- Consistent version across projects
- No merge conflicts (projects only store settings)

## System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code IDE                       │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Plugin System                         │ │
│  │  • Discovers plugins in ~/.config/claude-code/    │ │
│  │  • Resolves ${CLAUDE_PLUGIN_ROOT} variables       │ │
│  │  • Merges settings (base + project overrides)     │ │
│  │  • Auto-detects LSP servers                       │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │   ~/.amplihack/.claude/            │
         │   (Centralized Plugin)             │
         │                                    │
         │  ├── .claude-plugin/               │
         │  │   └── plugin.json  ◄───────────┼─── Plugin Manifest
         │  │                                 │
         │  ├── agents/           ◄───────────┼─── 42 Specialized Agents
         │  ├── commands/         ◄───────────┼─── 18 Slash Commands
         │  ├── skills/           ◄───────────┼─── 12 Claude Code Skills
         │  ├── workflow/         ◄───────────┼─── 5 Workflow Definitions
         │  ├── tools/            ◄───────────┼─── Hooks (PostInit, PreCommit, etc.)
         │  └── context/          ◄───────────┼─── Philosophy & Patterns
         └─────────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │   Project Working Directories       │
         │                                     │
         │  project1/.claude/                  │
         │    └── settings.json  ◄────────────┼─── Project Overrides
         │                                     │
         │  project2/.claude/                  │
         │    └── settings.json  ◄────────────┼─── Project Overrides
         │                                     │
         │  project3/.claude/                  │
         │    └── settings.json  ◄────────────┼─── Project Overrides
         └─────────────────────────────────────┘
```

### Data Flow

1. **IDE Startup**: Claude Code reads `~/.config/claude-code/plugins.json`, discovers amplihack plugin
2. **Plugin Loading**: IDE loads `~/.amplihack/.claude/.claude-plugin/plugin.json`
3. **Variable Substitution**: IDE replaces `${CLAUDE_PLUGIN_ROOT}` with `~/.amplihack/.claude/` in all paths
4. **Settings Merge**: IDE merges base settings with project-specific overrides
5. **LSP Detection**: IDE scans project files, auto-configures language servers
6. **Runtime**: Hooks, agents, commands, and skills execute from centralized location

## Key Components

### Plugin Manifest

Location: `~/.amplihack/.claude/.claude-plugin/plugin.json`

```json
{
  "name": "amplihack",
  "version": "1.0.0",
  "description": "AI-powered development framework for Claude Code",
  "author": "amplihack contributors",
  "repository": "github.com/rysweet/amplihack",

  "hooks": {
    "PostInit": "${CLAUDE_PLUGIN_ROOT}/tools/PostInit.sh",
    "PreCommit": "${CLAUDE_PLUGIN_ROOT}/tools/PreCommit.sh",
    "PreCompact": "${CLAUDE_PLUGIN_ROOT}/tools/PreCompact.sh"
  },

  "agents_directory": "${CLAUDE_PLUGIN_ROOT}/agents/",
  "commands_directory": "${CLAUDE_PLUGIN_ROOT}/commands/",
  "skills_directory": "${CLAUDE_PLUGIN_ROOT}/skills/",
  "workflow_directory": "${CLAUDE_PLUGIN_ROOT}/workflow/",

  "lsp": {
    "auto_detect": true,
    "supported_languages": [
      "python", "javascript", "typescript",
      "rust", "go", "java", "cpp"
    ]
  },

  "settings_merger": {
    "strategy": "deep_merge",
    "allow_project_overrides": true
  }
}
```

**Purpose:** Defines plugin structure and tells Claude Code how to integrate amplihack.

### Hook Variable Resolution

The `${CLAUDE_PLUGIN_ROOT}` variable enables portable hook paths.

**Before Resolution (in plugin.json):**

```json
{
  "hooks": {
    "PostInit": "${CLAUDE_PLUGIN_ROOT}/tools/PostInit.sh"
  }
}
```

**After Resolution (at runtime):**

```json
{
  "hooks": {
    "PostInit": "/home/username/.amplihack/.claude/tools/PostInit.sh"
  }
}
```

**Why This Matters:**

- Hooks work regardless of installation path
- Same manifest works on macOS (`/Users/...`), Linux (`/home/...`), and Windows (`C:\Users\...`)
- Migration tools can move installation without breaking paths

### Settings Merger

The settings merger combines base plugin settings with project-specific overrides using deep merge strategy.

**Base Settings** (`~/.amplihack/.claude/settings.json`):

```json
{
  "agents": {
    "enabled": ["architect", "builder", "reviewer", "tester"],
    "timeout_seconds": 120
  },
  "workflows": {
    "default": "DEFAULT_WORKFLOW"
  },
  "lsp": {
    "python": {
      "command": "pylsp",
      "enabled": true
    }
  }
}
```

**Project Override** (`project1/.claude/settings.json`):

```json
{
  "agents": {
    "enabled": ["architect", "builder", "security"],
    "custom_agents": ["./local-agents/domain-expert.md"]
  },
  "workflows": {
    "default": "INVESTIGATION_WORKFLOW"
  }
}
```

**Merged Result** (what Claude Code uses for project1):

```json
{
  "agents": {
    "enabled": ["architect", "builder", "security"],
    "custom_agents": ["./local-agents/domain-expert.md"],
    "timeout_seconds": 120
  },
  "workflows": {
    "default": "INVESTIGATION_WORKFLOW"
  },
  "lsp": {
    "python": {
      "command": "pylsp",
      "enabled": true
    }
  }
}
```

**Merge Rules:**

1. **Arrays**: Project overrides replace base (not append)
2. **Objects**: Deep merge, project settings take precedence
3. **Primitives**: Project value overrides base value
4. **New keys**: Project can add keys not in base

### LSP Auto-Detection

The plugin automatically detects project languages and configures appropriate Language Server Protocol servers.

**Detection Algorithm:**

1. Scan project root for language-specific files:
   - Python: `*.py`, `pyproject.toml`, `setup.py`
   - JavaScript: `*.js`, `package.json`
   - TypeScript: `*.ts`, `tsconfig.json`
   - Rust: `*.rs`, `Cargo.toml`
   - Go: `*.go`, `go.mod`

2. Check if LSP server is installed:
   ```bash
   # Python
   which pylsp

   # JavaScript/TypeScript
   which typescript-language-server

   # Rust
   which rust-analyzer
   ```

3. Generate LSP configuration:
   ```json
   {
     "lsp": {
       "python": {
         "command": "pylsp",
         "enabled": true,
         "root_markers": ["pyproject.toml", "setup.py"]
       }
     }
   }
   ```

4. Merge with project settings (project can override auto-detection)

**Example: Multi-Language Project**

For a project with Python and TypeScript:

```
project/
├── src/
│   ├── main.py
│   └── frontend/
│       └── app.ts
├── pyproject.toml
└── package.json
```

Auto-detected LSP configuration:

```json
{
  "lsp": {
    "python": {
      "command": "pylsp",
      "enabled": true,
      "root_markers": ["pyproject.toml"]
    },
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "enabled": true,
      "root_markers": ["package.json", "tsconfig.json"]
    }
  }
}
```

## Runtime Data Separation

Plugin architecture separates read-only framework code from writable runtime data.

### Read-Only Framework Code

Location: `~/.amplihack/.claude/`

```
~/.amplihack/.claude/
├── agents/              # Never modified at runtime
├── commands/            # Never modified at runtime
├── skills/              # Never modified at runtime
├── workflow/            # Never modified at runtime
└── context/             # Never modified at runtime
```

### Writable Runtime Data

Location: `~/.amplihack/runtime/` (separate from plugin)

```
~/.amplihack/runtime/
├── logs/                # Session logs
│   └── 20260119-143052/
│       ├── session.log
│       └── DECISIONS.md
├── cache/               # Downloaded resources
│   └── models/
└── discoveries/         # Learned patterns
    └── discoveries.json
```

### Project-Specific Runtime Data

Location: `<project>/.claude/runtime/`

```
project1/.claude/
├── settings.json        # Project overrides
└── runtime/             # Project-specific runtime
    ├── logs/
    └── cache/
```

**Separation Benefits:**

- Plugin updates never delete logs or cache
- Uninstall preserves runtime data
- Projects maintain independent runtime state
- Backup strategies can target runtime separately

## Claude Code Plugin Support

The plugin architecture is designed specifically for **Claude Code and compatible implementations** (RustyClawd/Rusty).

**Important**: GitHub Copilot and OpenAI Codex do NOT support Claude Code plugins. They use per-project `.claude/` staging via `amplihack copilot` and `amplihack codex` commands.

### Claude Code Plugin Registration

The plugin registers itself in Claude Code's configuration at:

**Location**: `~/.config/claude-code/plugins.json`

```json
{
  "plugins": [{
    "name": "amplihack",
    "path": "~/.amplihack/.claude/"
  }]
}
```

This tells Claude Code where to find the centralized plugin installation. All hooks, agents, skills, and workflows are loaded from this location.

## Security Considerations

### Plugin Isolation

The plugin runs with the same permissions as the IDE:

- Cannot access files outside project directory without explicit user action
- Subprocess calls require user confirmation (via IDE settings)
- Network requests logged and rate-limited

### Verification

Users can verify plugin integrity:

```bash
# Check plugin signature
amplihack plugin verify --check-signature

# Compare with official release
amplihack plugin verify --compare-upstream
```

### Updates

Plugin updates go through verification:

1. Download new version
2. Verify signature matches official release
3. Backup current version
4. Install update
5. Run verification tests
6. Rollback if verification fails

## Performance Characteristics

### Startup Time

Plugin loading adds minimal overhead to IDE startup:

- **Plugin discovery**: ~10ms (scan `~/.config/claude-code/plugins.json`)
- **Manifest parsing**: ~5ms (parse `plugin.json`)
- **Variable substitution**: ~2ms (replace `${CLAUDE_PLUGIN_ROOT}`)
- **Settings merge**: ~15ms (deep merge base + project settings)
- **LSP auto-detection**: ~50ms (scan project files, check installed servers)

**Total overhead**: ~82ms (negligible on modern hardware)

### Memory Footprint

- **Plugin manifest**: ~5 KB in memory
- **Merged settings**: ~10-50 KB depending on project overrides
- **Agents loaded on-demand**: No memory until invoked

### Disk Usage

- **Plugin installation**: ~5.2 MB (`~/.amplihack/.claude/`)
- **Per-project overhead**: < 1 KB (`.claude/settings.json`)
- **Runtime data**: Varies by usage (logs, cache, discoveries)

## Comparison with Per-Project Mode

| Aspect | Per-Project Mode | Plugin Mode |
|--------|------------------|-------------|
| **Installation Size** | 5.2 MB × N projects | 5.2 MB (shared) |
| **Updates** | Per project | Single command |
| **Version Consistency** | Drift possible | Always consistent |
| **Merge Conflicts** | Frequent | None (settings only) |
| **Disk Usage (10 projects)** | ~52 MB | ~5.2 MB |
| **Update Time** | N × 30 seconds | 30 seconds |
| **Configuration** | Duplicate settings | Override pattern |

## Extensibility

### Adding Custom Agents

Projects can add custom agents without modifying the plugin:

```json
// project/.claude/settings.json
{
  "agents": {
    "custom_agents": [
      "./local-agents/domain-expert.md",
      "./local-agents/legacy-system-specialist.md"
    ]
  }
}
```

Custom agents coexist with plugin agents:

```python
# Available agents in this project:
available = plugin_agents + custom_agents
# = [architect, builder, reviewer, ...] + [domain-expert, legacy-system-specialist]
```

### Adding Custom Commands

Projects can override or extend commands:

```json
// project/.claude/settings.json
{
  "commands": {
    "custom_commands": [
      "./local-commands/domain-analyze.py"
    ],
    "override_commands": {
      "/analyze": "./local-commands/custom-analyze.py"
    }
  }
}
```

### Adding Custom Workflows

Projects can define custom workflows:

```json
// project/.claude/settings.json
{
  "workflows": {
    "custom_workflows": [
      "./workflows/COMPLIANCE_WORKFLOW.md"
    ],
    "default": "COMPLIANCE_WORKFLOW"
  }
}
```

## Future Enhancements

### Planned Features

1. **Plugin Marketplace**: Discover and install third-party plugins
2. **Version Pinning**: Lock projects to specific plugin versions
3. **Plugin Composition**: Combine multiple plugins (amplihack + domain-specific)
4. **Remote Plugins**: Load plugins from git URLs without local installation

### Design Principles

All enhancements follow these principles:

- **Backward compatible**: Old projects continue working
- **Migration path**: Automated migration for breaking changes
- **Minimal overhead**: Preserve startup time and memory footprint
- **Security first**: Verify plugins before execution

## Related Documentation

- [Installation Guide](./INSTALLATION.md) - Install the plugin
- [Migration Guide](./MIGRATION.md) - Migrate from per-project mode
- [CLI Reference](./CLI_REFERENCE.md) - Command-line tools
- [Multi-IDE Setup](./MULTI_IDE.md) - Configure for different IDEs

---

**Last updated:** 2026-01-19
**Plugin version:** 1.0.0
