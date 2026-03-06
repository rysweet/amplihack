# CLI Reference

Complete reference for amplihack plugin command-line interface.

## Command Overview

| Command                           | Purpose                   | Common Use                    |
| --------------------------------- | ------------------------- | ----------------------------- |
| `amplihack plugin install`        | Install or upgrade plugin | First-time setup, updates     |
| `amplihack plugin uninstall`      | Remove plugin             | Cleanup, troubleshooting      |
| `amplihack plugin verify`         | Check installation        | Verify after install, debug   |
| `amplihack plugin link`           | Re-link plugin to IDE     | Fix broken links              |
| `amplihack mode to-plugin`        | Migrate project           | Convert per-project to plugin |
| `amplihack mode extract-settings` | Extract project settings  | Manual migration              |
| `amplihack agents list`           | List available agents     | Discovery                     |
| `amplihack commands list`         | List available commands   | Discovery                     |
| `amplihack skills list`           | List available skills     | Discovery                     |

## amplihack plugin install

Install or upgrade the amplihack plugin to `~/.amplihack/.claude/`.

### Syntax

```bash
amplihack plugin install [OPTIONS]
```

### Options

| Option            | Description                        | Default                 |
| ----------------- | ---------------------------------- | ----------------------- |
| `--upgrade`       | Upgrade existing installation      | false                   |
| `--force`         | Force reinstall even if up-to-date | false                   |
| `--path PATH`     | Install to custom path             | `~/.amplihack/.claude/` |
| `--from-git URL`  | Install from git repository        | Official repo           |
| `--branch BRANCH` | Git branch to install from         | main                    |
| `--verify`        | Verify after installation          | true                    |

### Examples

**Basic installation:**

```bash
amplihack plugin install
```

Output:

```
Installing amplihack plugin to ~/.amplihack/.claude/
✓ Created plugin directory structure
✓ Installed agents (42 agents)
✓ Installed commands (18 commands)
✓ Installed skills (12 skills)
✓ Installed workflows (5 workflows)
✓ Configured hooks
✓ Verification passed

Plugin installed successfully!
```

**Upgrade existing installation:**

```bash
amplihack plugin install --upgrade
```

Output:

```
Current version: 0.9.0
Latest version: 1.0.0

Upgrading amplihack plugin...
✓ Backed up current installation to ~/.amplihack/.claude.backup-20260119
✓ Downloaded version 1.0.0
✓ Installed new version
✓ Migrated settings
✓ Verification passed

Upgrade complete! (0.9.0 → 1.0.0)
```

**Force reinstall:**

```bash
amplihack plugin install --force
```

Output:

```
Warning: --force will remove and reinstall the plugin.
Continue? [y/N] y

Removing existing installation...
✓ Removed ~/.amplihack/.claude/

Installing fresh copy...
✓ Installed version 1.0.0
✓ Verification passed

Plugin reinstalled successfully!
```

**Install from custom git repository:**

```bash
amplihack plugin install --from-git https://github.com/myorg/amplihack-fork.git
```

**Install from development branch:**

```bash
amplihack plugin install --from-git https://github.com/rysweet/amplihack.git --branch develop
```

**Install to custom location:**

```bash
amplihack plugin install --path ~/custom/location/.claude/
```

### Exit Codes

| Code | Meaning             |
| ---- | ------------------- |
| 0    | Success             |
| 1    | General error       |
| 2    | Installation failed |
| 3    | Verification failed |
| 4    | Permission denied   |

### Notes

- Installation creates `~/.amplihack/.claude/` by default
- Existing installations are backed up before upgrade
- Verification runs automatically unless `--no-verify` specified
- Requires Python 3.8 or higher

---

## amplihack plugin uninstall

Remove the amplihack plugin from your system.

### Syntax

```bash
amplihack plugin uninstall [OPTIONS]
```

### Options

| Option           | Description                         | Default |
| ---------------- | ----------------------------------- | ------- |
| `--keep-runtime` | Preserve runtime data (logs, cache) | false   |
| `--force`        | Skip confirmation prompt            | false   |
| `--backup`       | Create backup before uninstall      | true    |

### Examples

**Basic uninstall:**

```bash
amplihack plugin uninstall
```

Output:

```
This will remove the amplihack plugin from ~/.amplihack/.claude/

Projects using plugin mode will stop working until you:
  - Reinstall the plugin, or
  - Migrate projects back to per-project mode

Uninstall plugin? [y/N] y

Creating backup...
✓ Backed up to ~/.amplihack/.claude.backup-20260119

Uninstalling plugin...
✓ Removed ~/.amplihack/.claude/
✓ Updated IDE configuration

Plugin uninstalled successfully!
Backup saved: ~/.amplihack/.claude.backup-20260119
```

**Uninstall and keep runtime data:**

```bash
amplihack plugin uninstall --keep-runtime
```

Output:

```
Uninstalling plugin (preserving runtime data)...
✓ Removed framework files
✓ Kept ~/.amplihack/runtime/

Runtime data preserved:
  - Logs: ~/.amplihack/runtime/logs/
  - Cache: ~/.amplihack/runtime/cache/
  - Discoveries: ~/.amplihack/runtime/discoveries/
```

**Force uninstall without confirmation:**

```bash
amplihack plugin uninstall --force
```

### Exit Codes

| Code | Meaning           |
| ---- | ----------------- |
| 0    | Success           |
| 1    | General error     |
| 2    | Uninstall failed  |
| 4    | Permission denied |

### Notes

- Creates backup by default (disable with `--no-backup`)
- Runtime data deleted unless `--keep-runtime` specified
- Projects in plugin mode will break until plugin reinstalled or migrated back

---

## amplihack plugin verify

Verify plugin installation integrity and configuration.

### Syntax

```bash
amplihack plugin verify [OPTIONS]
```

### Options

| Option               | Description                    | Default |
| -------------------- | ------------------------------ | ------- |
| `--check-signature`  | Verify cryptographic signature | false   |
| `--compare-upstream` | Compare with official release  | false   |
| `--verbose`          | Show detailed output           | false   |

### Examples

**Basic verification:**

```bash
amplihack plugin verify
```

Output:

```
Verifying amplihack plugin installation...

✓ Plugin directory exists: ~/.amplihack/.claude/
✓ Plugin manifest valid: .claude-plugin/plugin.json
✓ Agents directory: 42 agents found
✓ Commands directory: 18 commands found
✓ Skills directory: 12 skills found
✓ Workflows directory: 5 workflows found
✓ Hooks configured: 3 hooks with ${CLAUDE_PLUGIN_ROOT}
✓ LSP auto-detection: Enabled

All checks passed! Plugin is ready to use.
```

**Verify with signature check:**

```bash
amplihack plugin verify --check-signature
```

Output:

```
Verifying amplihack plugin installation...

✓ Plugin directory exists
✓ Plugin manifest valid
✓ All components present
✓ Signature valid (signed by: release@amplihack.dev)
✓ Signature matches official release

Installation verified and authentic!
```

**Compare with upstream:**

```bash
amplihack plugin verify --compare-upstream
```

Output:

```
Verifying amplihack plugin installation...

✓ Local version: 1.0.0
✓ Upstream version: 1.0.0
✓ File checksums match official release
✓ No modifications detected

Installation matches official release!
```

**Verbose verification:**

```bash
amplihack plugin verify --verbose
```

Output:

```
Verifying amplihack plugin installation...

Checking plugin directory...
  Path: /home/user/.amplihack/.claude/
  Exists: ✓
  Permissions: drwxr-xr-x
  Size: 5.2 MB

Checking plugin manifest...
  File: .claude-plugin/plugin.json
  Valid JSON: ✓
  Schema version: 1.0
  Plugin name: amplihack
  Plugin version: 1.0.0

Checking agents...
  Directory: agents/
  Total agents: 42
  Core agents: 18
  Specialized agents: 20
  Workflow agents: 4

Checking commands...
  Directory: commands/
  Total commands: 18
  All executable: ✓

[... detailed output continues ...]

All checks passed! Plugin is ready to use.
```

### Exit Codes

| Code | Meaning             |
| ---- | ------------------- |
| 0    | Verification passed |
| 1    | Verification failed |
| 2    | Plugin not found    |
| 3    | Signature invalid   |

### Notes

- Use after installation to confirm success
- Use `--check-signature` to verify authenticity
- Use `--compare-upstream` to detect modifications

---

## amplihack plugin link

Re-link plugin to IDE configuration.

### Syntax

```bash
amplihack plugin link [OPTIONS]
```

### Options

| Option      | Description                              | Default     |
| ----------- | ---------------------------------------- | ----------- |
| `--ide IDE` | Target IDE (claude-code, copilot, codex) | claude-code |
| `--force`   | Force relink even if already linked      | false       |

### Examples

**Link to Claude Code:**

```bash
amplihack plugin link
```

Output:

```
Linking amplihack plugin to Claude Code...

✓ Found plugin at ~/.amplihack/.claude/
✓ Updated ~/.config/claude-code/plugins.json
✓ Verified plugin configuration

Plugin linked successfully!
Restart Claude Code to activate.
```

**Link to GitHub Copilot:**

```bash
amplihack plugin link --ide copilot
```

Output:

```
Linking amplihack plugin to GitHub Copilot...

✓ Found plugin at ~/.amplihack/.claude/
✓ Updated ~/.config/github-copilot/extensions.json
✓ Verified extension configuration

Plugin linked successfully!
Restart VS Code to activate.
```

**Link to Codex:**

```bash
amplihack plugin link --ide codex
```

Output:

```
Linking amplihack plugin to Codex...

✓ Found plugin at ~/.amplihack/.claude/
✓ Updated ~/.config/codex/lsp-servers.json
✓ Verified LSP configuration

Plugin linked successfully!
Restart Codex to activate.
```

**Force relink:**

```bash
amplihack plugin link --force
```

### Exit Codes

| Code | Meaning              |
| ---- | -------------------- |
| 0    | Success              |
| 1    | Link failed          |
| 2    | Plugin not found     |
| 3    | IDE config not found |

### Notes

- Run after moving plugin directory
- Run if IDE doesn't detect plugin
- Restart IDE after linking

---

## amplihack mode to-plugin

Migrate project from per-project mode to plugin mode.

### Syntax

```bash
amplihack mode to-plugin [OPTIONS]
```

### Options

| Option          | Description                       | Default |
| --------------- | --------------------------------- | ------- |
| `--all`         | Migrate all projects in directory | false   |
| `--auto-commit` | Automatically commit changes      | false   |
| `--dry-run`     | Show what would be done           | false   |
| `--backup`      | Create backup before migration    | true    |

### Examples

**Migrate current project:**

```bash
cd /path/to/project
amplihack mode to-plugin
```

Output:

```
Migrating project to plugin mode: /home/user/projects/myapp

Analyzing current .claude/ directory...
✓ Found 127 framework files (will be removed)
✓ Found 3 custom agents (will be preserved)
✓ Found 1 custom command (will be preserved)
✓ Found project settings (will be extracted)

Creating migration plan:
  1. Extract settings to settings.json
  2. Move custom agents to .claude/agents/custom/
  3. Move custom commands to .claude/commands/custom/
  4. Remove framework files
  5. Update .gitignore

Execute migration? [y/N] y

Executing migration...
✓ Extracted settings.json (12 overrides)
✓ Moved 3 custom agents
✓ Moved 1 custom command
✓ Removed 127 framework files
✓ Updated .gitignore

Migration complete!

Project size before: 5.3 MB
Project size after: 23 KB
Savings: 5.27 MB (99.6%)

Next steps:
  1. Test: amplihack plugin verify
  2. Commit: git add .claude/ && git commit -m "Migrate to plugin mode"
  3. Push: git push
```

**Migrate all projects in directory:**

```bash
cd /path/to/projects
amplihack mode to-plugin --all
```

Output:

```
Scanning for projects with .claude/ directories...
Found 8 projects to migrate

Migrate all projects? [y/N] y

[1/8] Migrating api-server...
✓ Complete (saved 5.27 MB)

[2/8] Migrating frontend...
✓ Complete (saved 5.29 MB)

[3/8] Migrating ml-pipeline...
✓ Complete (saved 5.31 MB)

[... continues for all projects ...]

Migration complete!
Total savings: 41.2 MB across 8 projects
```

**Auto-commit changes:**

```bash
amplihack mode to-plugin --auto-commit
```

Output:

```
[... migration output ...]

Auto-committing changes...
✓ Staged .claude/ changes
✓ Staged .gitignore changes
✓ Committed: "Migrate to plugin mode"

Changes committed successfully!
Run 'git push' to push changes.
```

**Dry run (preview only):**

```bash
amplihack mode to-plugin --dry-run
```

Output:

```
DRY RUN - No changes will be made

Would migrate project: /home/user/projects/myapp

Would perform these actions:
  1. Extract settings.json
     - 12 settings would be extracted
  2. Move custom agents
     - domain-expert.md → .claude/agents/custom/
     - legacy-specialist.md → .claude/agents/custom/
     - api-analyzer.md → .claude/agents/custom/
  3. Move custom commands
     - analyze-api.py → .claude/commands/custom/
  4. Remove framework files
     - 127 files would be deleted
  5. Update .gitignore
     - 3 patterns would be removed
     - 3 patterns would be added

Estimated savings: 5.27 MB

Run without --dry-run to execute migration.
```

### Exit Codes

| Code | Meaning              |
| ---- | -------------------- |
| 0    | Success              |
| 1    | Migration failed     |
| 2    | No projects found    |
| 3    | Plugin not installed |

### Notes

- Creates backup by default
- Preserves custom agents, commands, workflows
- Removes only framework files
- Updates .gitignore automatically

---

## amplihack mode extract-settings

Extract project-specific settings from `~/.amplihack/.claude/` directory.

### Syntax

```bash
amplihack mode extract-settings [OPTIONS]
```

### Options

| Option            | Description                     | Default |
| ----------------- | ------------------------------- | ------- |
| `--output FILE`   | Write to file instead of stdout | stdout  |
| `--format FORMAT` | Output format (json, yaml)      | json    |

### Examples

**Extract to stdout:**

```bash
amplihack mode extract-settings
```

Output:

```json
{
  "agents": {
    "custom_agents": ["./agents/custom/domain-expert.md", "./agents/custom/legacy-specialist.md"]
  },
  "workflows": {
    "default": "INVESTIGATION_WORKFLOW"
  },
  "preferred_language": "python"
}
```

**Extract to file:**

```bash
amplihack mode extract-settings --output .claude/settings.json
```

Output:

```
Extracting project settings...
✓ Analyzed .claude/ directory
✓ Identified 12 project-specific settings
✓ Wrote settings to .claude/settings.json

Settings extracted successfully!
```

**Extract as YAML:**

```bash
amplihack mode extract-settings --format yaml
```

Output:

```yaml
agents:
  custom_agents:
    - ./agents/custom/domain-expert.md
    - ./agents/custom/legacy-specialist.md
workflows:
  default: INVESTIGATION_WORKFLOW
preferred_language: python
```

### Exit Codes

| Code | Meaning               |
| ---- | --------------------- |
| 0    | Success               |
| 1    | Extraction failed     |
| 2    | No .claude/ directory |

### Notes

- Identifies only non-default settings
- Excludes framework-provided values
- Useful for manual migration

---

## amplihack agents list

List all available agents (plugin + custom).

### Syntax

```bash
amplihack agents list [OPTIONS]
```

### Options

| Option            | Description                                          | Default |
| ----------------- | ---------------------------------------------------- | ------- |
| `--type TYPE`     | Filter by type (core, specialized, workflow, custom) | all     |
| `--format FORMAT` | Output format (table, json, simple)                  | table   |

### Examples

**List all agents:**

```bash
amplihack agents list
```

Output:

```
Available Agents (45 total)

Core Agents (18):
  architect              - System design and problem decomposition
  builder                - Code implementation from specifications
  reviewer               - Philosophy compliance and code review
  tester                 - Test generation and validation
  api-designer           - API contract definitions
  optimizer              - Performance bottleneck analysis
  [... 12 more ...]

Specialized Agents (20):
  security               - Vulnerability assessment
  database               - Schema and query optimization
  integration            - External service connections
  cleanup                - Code simplification
  [... 16 more ...]

Workflow Agents (4):
  pre-commit-diagnostic  - Pre-commit hook troubleshooting
  ci-diagnostic-workflow - CI failure diagnosis
  fix-agent              - Common error pattern resolution
  knowledge-archaeologist - Deep code investigation

Custom Agents (3):
  domain-expert          - Project-specific domain knowledge
  legacy-specialist      - Legacy system integration
  api-analyzer           - API usage pattern analysis
```

**List only custom agents:**

```bash
amplihack agents list --type custom
```

Output:

```
Custom Agents (3):
  domain-expert          - Project-specific domain knowledge
  legacy-specialist      - Legacy system integration
  api-analyzer           - API usage pattern analysis
```

**JSON output:**

```bash
amplihack agents list --format json
```

Output:

```json
{
  "core": [
    { "name": "architect", "description": "System design and problem decomposition" },
    { "name": "builder", "description": "Code implementation from specifications" }
  ],
  "specialized": [{ "name": "security", "description": "Vulnerability assessment" }],
  "workflow": [
    { "name": "pre-commit-diagnostic", "description": "Pre-commit hook troubleshooting" }
  ],
  "custom": [{ "name": "domain-expert", "description": "Project-specific domain knowledge" }]
}
```

### Exit Codes

| Code | Meaning          |
| ---- | ---------------- |
| 0    | Success          |
| 1    | Plugin not found |

---

## amplihack commands list

List all available slash commands.

### Syntax

```bash
amplihack commands list [OPTIONS]
```

### Options

| Option            | Description                         | Default |
| ----------------- | ----------------------------------- | ------- |
| `--format FORMAT` | Output format (table, json, simple) | table   |

### Examples

**List all commands:**

```bash
amplihack commands list
```

Output:

```
Available Commands (18 total)

Core Commands:
  /ultrathink              - Orchestrated multi-agent execution
  /analyze                 - Comprehensive code review
  /improve                 - Self-improvement and learning

Development Workflow:
  /fix                     - Intelligent fix workflow
  /amplihack:ddd:*         - Document-driven development phases

Fault Tolerance:
  /amplihack:n-version     - N-version programming
  /amplihack:debate        - Multi-agent debate
  /amplihack:cascade       - Fallback cascade

Customization:
  /amplihack:customize     - Manage user preferences

[... full list ...]
```

### Exit Codes

| Code | Meaning          |
| ---- | ---------------- |
| 0    | Success          |
| 1    | Plugin not found |

---

## amplihack skills list

List all available Claude Code skills.

### Syntax

```bash
amplihack skills list [OPTIONS]
```

### Options

| Option            | Description                         | Default |
| ----------------- | ----------------------------------- | ------- |
| `--format FORMAT` | Output format (table, json, simple) | table   |

### Examples

**List all skills:**

```bash
amplihack skills list
```

Output:

```
Available Skills (12 total)

Documentation:
  documentation-writing    - Eight Rules and Diataxis framework
  mermaid-diagram-generator - Architecture diagram generation

Code Analysis:
  code-smell-detector      - Anti-pattern detection
  code-visualizer          - Code flow diagram generation

Development:
  module-spec-generator    - Brick philosophy module specs
  test-gap-analyzer        - Test coverage analysis

[... full list ...]
```

### Exit Codes

| Code | Meaning          |
| ---- | ---------------- |
| 0    | Success          |
| 1    | Plugin not found |

---

## Environment Variables

| Variable                 | Description                       | Default                 |
| ------------------------ | --------------------------------- | ----------------------- |
| `AMPLIHACK_PLUGIN_PATH`  | Override plugin installation path | `~/.amplihack/.claude/` |
| `AMPLIHACK_RUNTIME_PATH` | Override runtime data path        | `~/.amplihack/runtime/` |
| `CLAUDE_PLUGIN_ROOT`     | Set by IDE, points to plugin root | Set by IDE              |

### Examples

**Install to custom path:**

```bash
export AMPLIHACK_PLUGIN_PATH=~/custom/.claude/
amplihack plugin install
```

**Use custom runtime path:**

```bash
export AMPLIHACK_RUNTIME_PATH=/var/lib/amplihack/
amplihack plugin verify
```

---

## Exit Code Summary

| Code | Meaning                         | Commands                              |
| ---- | ------------------------------- | ------------------------------------- |
| 0    | Success                         | All                                   |
| 1    | General error                   | All                                   |
| 2    | Not found / installation failed | install, uninstall, verify, to-plugin |
| 3    | Verification / signature failed | verify, to-plugin                     |
| 4    | Permission denied               | install, uninstall                    |

---

## Related Documentation

- [Installation Guide](./INSTALLATION.md) - Getting started with plugin installation
- [Architecture Overview](./ARCHITECTURE.md) - How the plugin system works
- [Migration Guide](./MIGRATION.md) - Migrate from per-project mode
- [Multi-IDE Setup](./MULTI_IDE.md) - Configure for different IDEs

---

**Last updated:** 2026-01-19
**Plugin version:** 1.0.0
