# Migration Guide

Migrate your projects from per-project `.claude/` directories to the centralized plugin architecture.

## Who Should Migrate?

You should migrate if:

- You have projects with `.claude/` directories containing amplihack framework code
- You installed amplihack before version 1.0.0
- You run `amplihack upgrade` in each project individually
- You see merge conflicts in `.claude/` directories

## Migration Overview

Migration moves framework code from `project/.claude/` to `~/.amplihack/.claude/` while preserving your project-specific settings.

**What gets migrated:**

- Your project-specific settings → `project/.claude/settings.json`
- Your custom agents → `project/.claude/agents/custom/`
- Your custom commands → `project/.claude/commands/custom/`
- Your custom workflows → `project/.claude/workflow/custom/`

**What gets removed:**

- Framework agents (replaced by plugin)
- Framework commands (replaced by plugin)
- Framework skills (replaced by plugin)
- Framework workflows (replaced by plugin)
- Framework hooks (replaced by plugin)
- Framework context (replaced by plugin)

## Step 1: Backup Your Projects

Before migration, create a backup of your `.claude/` directories.

```bash
# Backup a single project
cd /path/to/project
tar -czf claude-backup-$(date +%Y%m%d).tar.gz .claude/

# Backup all projects (if they're in a parent directory)
cd /path/to/projects
for dir in */; do
  if [ -d "$dir/.claude" ]; then
    echo "Backing up $dir"
    tar -czf "${dir%/}-claude-backup-$(date +%Y%m%d).tar.gz" "$dir/.claude/"
  fi
done
```

**Verify backups:**

```bash
# List backup contents
tar -tzf claude-backup-20260119.tar.gz | head -20
```

## Step 2: Install Plugin

If you haven't already, install the centralized plugin.

```bash
# Install or upgrade amplihack
pip install --upgrade amplihack

# Install plugin
amplihack plugin install
```

**Expected output:**

```
Installing amplihack plugin to ~/.amplihack/.claude/
✓ Created plugin directory structure
✓ Installed 42 agents
✓ Installed 18 commands
✓ Installed 12 skills
✓ Installed 5 workflows
✓ Configured hooks

Plugin installed successfully!
```

## Step 3: Migrate Projects

### Automatic Migration (Recommended)

Use the migration command to migrate all projects automatically:

```bash
# Migrate a single project
cd /path/to/project
amplihack mode to-plugin

# Migrate multiple projects
cd /path/to/projects
amplihack mode to-plugin --all
```

**Example output:**

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
  1. Test your project: amplihack plugin verify
  2. Commit changes: git add .claude/ && git commit -m "Migrate to plugin mode"
  3. Push changes: git push
```

### Manual Migration (If Needed)

If automatic migration fails or you want more control:

#### 3.1: Identify Custom Files

List files that are yours (not framework):

```bash
cd /path/to/project

# List custom agents
ls .claude/agents/custom/ 2>/dev/null

# List custom commands
ls .claude/commands/custom/ 2>/dev/null

# List custom workflows
ls .claude/workflow/custom/ 2>/dev/null

# Check for project settings
cat .claude/settings.json 2>/dev/null
```

#### 3.2: Extract Project Settings

If `.claude/settings.json` exists, identify project-specific overrides:

```bash
# View current settings
cat .claude/settings.json
```

Create a new minimal `settings.json` with only your overrides:

```json
{
  "agents": {
    "custom_agents": [
      "./agents/custom/domain-expert.md",
      "./agents/custom/legacy-specialist.md"
    ]
  },
  "workflows": {
    "default": "INVESTIGATION_WORKFLOW"
  },
  "preferred_language": "python"
}
```

Save to `.claude/settings.json`.

#### 3.3: Preserve Custom Components

Move custom components to designated directories:

```bash
# If you have custom agents
mkdir -p .claude/agents/custom/
mv .claude/agents/amplihack/specialized/my-*.md .claude/agents/custom/

# If you have custom commands
mkdir -p .claude/commands/custom/
mv .claude/commands/my-*.py .claude/commands/custom/

# If you have custom workflows
mkdir -p .claude/workflow/custom/
mv .claude/workflow/MY_*.md .claude/workflow/custom/
```

#### 3.4: Remove Framework Files

Remove framework directories (now provided by plugin):

```bash
cd /path/to/project

# Remove framework directories
rm -rf .claude/agents/amplihack/core/
rm -rf .claude/agents/amplihack/specialized/
rm -rf .claude/agents/amplihack/workflow/
rm -rf .claude/commands/*.py  # Keep custom/ subdirectory
rm -rf .claude/skills/
rm -rf .claude/workflow/DEFAULT_*.md
rm -rf .claude/workflow/INVESTIGATION_*.md
rm -rf .claude/tools/
rm -rf .claude/context/
```

Keep only:
- `.claude/settings.json`
- `.claude/agents/custom/` (if exists)
- `.claude/commands/custom/` (if exists)
- `.claude/workflow/custom/` (if exists)
- `.claude/runtime/` (logs, cache)

#### 3.5: Update .gitignore

Update `.gitignore` to ignore runtime data only:

```bash
cat >> .gitignore << 'EOF'

# Amplihack runtime (plugin mode)
.claude/runtime/logs/
.claude/runtime/cache/
.claude/runtime/discoveries/
EOF
```

**Remove old patterns** (these are now in the plugin):

```bash
# Edit .gitignore and remove:
# .claude/agents/
# .claude/commands/
# .claude/skills/
```

## Step 4: Verify Migration

Test that the project works with the plugin:

```bash
cd /path/to/project

# Verify plugin integration
amplihack plugin verify

# Test a command
claude-code
# Then type: /ultrathink analyze this codebase
```

**Expected verification output:**

```
Verifying amplihack plugin for project: /home/user/projects/myapp

✓ Plugin found: ~/.amplihack/.claude/
✓ Project settings valid: .claude/settings.json
✓ Custom agents loaded: 3 agents
✓ Custom commands loaded: 1 command
✓ Settings merged successfully
✓ All agents available: 45 total (42 plugin + 3 custom)

Project is ready to use!
```

## Step 5: Commit Changes

Commit the migrated configuration:

```bash
cd /path/to/project

# Stage changes
git add .claude/
git add .gitignore

# Review changes
git status

# Commit
git commit -m "Migrate to amplihack plugin mode

- Moved to centralized plugin at ~/.amplihack/.claude/
- Extracted project settings to .claude/settings.json
- Preserved custom agents and commands
- Reduced .claude/ from 5.3 MB to 23 KB
"

# Push
git push
```

## Step 6: Migrate Remaining Projects

Repeat steps 3-5 for each project, or use batch migration:

```bash
# Migrate all projects in a directory
cd /path/to/projects
amplihack mode to-plugin --all --auto-commit
```

**Expected output:**

```
Scanning for projects with .claude/ directories...
Found 8 projects to migrate:
  1. /home/user/projects/api-server
  2. /home/user/projects/frontend
  3. /home/user/projects/ml-pipeline
  4. /home/user/projects/data-ingestion
  5. /home/user/projects/analytics
  6. /home/user/projects/auth-service
  7. /home/user/projects/notification-service
  8. /home/user/projects/batch-processor

Migrate all projects? [y/N] y

Migrating project 1/8: api-server
✓ Extracted settings (5 overrides)
✓ Preserved 2 custom agents
✓ Removed 127 framework files
✓ Committed changes

Migrating project 2/8: frontend
✓ Extracted settings (3 overrides)
✓ No custom components
✓ Removed 127 framework files
✓ Committed changes

[... continues for all projects ...]

Migration complete!
Total disk savings: 41.2 MB across 8 projects
```

## Troubleshooting Migration

### Custom files detected as framework

**Problem:** Migration wants to remove your custom files.

**Solution:**

```bash
# Move custom files to designated directories first
mkdir -p .claude/agents/custom/
mv .claude/agents/amplihack/specialized/my-custom-agent.md .claude/agents/custom/

# Then re-run migration
amplihack mode to-plugin
```

### Settings not preserved

**Problem:** Your project settings are lost after migration.

**Solution:**

```bash
# Restore from backup
tar -xzf claude-backup-20260119.tar.gz .claude/settings.json

# Extract settings manually
amplihack mode extract-settings > .claude/settings.json

# Verify settings
cat .claude/settings.json
```

### Commands still reference old paths

**Problem:** Scripts reference `.claude/agents/amplihack/...` paths.

**Solution:**

```bash
# Find references to old paths
grep -r "\.claude/agents/amplihack" .

# Update to use plugin (paths are now automatic)
# Old: python .claude/agents/amplihack/core/architect.md
# New: /ultrathink (command invokes plugin agents automatically)
```

### Git merge conflicts after migration

**Problem:** Other developers haven't migrated yet, causing conflicts.

**Solution:**

Coordinate migration across team:

```bash
# Create migration branch
git checkout -b migrate-to-plugin

# Migrate
amplihack mode to-plugin

# Commit
git commit -am "Migrate to plugin mode"

# Push and create PR
git push -u origin migrate-to-plugin
gh pr create --title "Migrate to amplihack plugin mode"

# Team reviews, then merges
# Other developers pull and install plugin:
# git pull
# amplihack plugin install
```

### Plugin not found after migration

**Problem:** IDE reports plugin not found.

**Solution:**

```bash
# Verify plugin installation
amplihack plugin verify

# Re-link plugin if needed
amplihack plugin link

# Restart IDE
```

## Rollback Procedure

If migration fails, you can rollback using your backup.

```bash
cd /path/to/project

# Remove migrated .claude/ directory
rm -rf .claude/

# Restore from backup
tar -xzf claude-backup-20260119.tar.gz

# Verify restoration
ls -la .claude/
```

To rollback the plugin installation:

```bash
# Uninstall plugin
amplihack plugin uninstall

# Projects revert to per-project mode
# (Framework code must be present in each project)
```

## Post-Migration Benefits

After migration, you'll experience:

### Disk Savings

Before:
```
project1/.claude/  5.3 MB
project2/.claude/  5.3 MB
project3/.claude/  5.3 MB
Total: 15.9 MB
```

After:
```
~/.amplihack/.claude/  5.3 MB (shared)
project1/.claude/      23 KB
project2/.claude/      18 KB
project3/.claude/      31 KB
Total: 5.37 MB (savings: 66%)
```

### Simplified Updates

Before:
```bash
cd project1 && amplihack upgrade  # 30s
cd project2 && amplihack upgrade  # 30s
cd project3 && amplihack upgrade  # 30s
Total: 90 seconds
```

After:
```bash
amplihack plugin install --upgrade  # 30s
# All projects updated instantly
Total: 30 seconds (3× faster)
```

### No More Merge Conflicts

Before migration:
```
CONFLICT (content): Merge conflict in .claude/agents/amplihack/core/architect.md
CONFLICT (content): Merge conflict in .claude/context/PATTERNS.md
CONFLICT (content): Merge conflict in .claude/tools/PostInit.sh
```

After migration:
```
# No conflicts - projects only contain settings.json
# Framework code in plugin (never touched)
```

## Team Migration Strategy

For teams migrating together:

### Strategy 1: Big Bang (Fast, Coordinated)

1. **Schedule migration**: Pick a date when all developers are available
2. **Install plugin**: Everyone runs `amplihack plugin install`
3. **Migrate one project**: One developer migrates, creates PR
4. **Review and merge**: Team reviews, approves
5. **Everyone pulls**: All developers pull, test
6. **Migrate remaining**: Repeat for all projects

**Timeline:** 1-2 hours for team of 5 with 10 projects

### Strategy 2: Gradual (Safe, Staggered)

1. **Install plugin**: Everyone runs `amplihack plugin install`
2. **New projects use plugin**: New projects created in plugin mode
3. **Migrate on touch**: Migrate projects as developers work on them
4. **Complete over time**: All projects migrated within 2-4 weeks

**Timeline:** 2-4 weeks for team of 5 with 10 projects

### Strategy 3: Hybrid (Balanced)

1. **Core team installs**: 1-2 developers install plugin
2. **Migrate critical projects**: Migrate high-traffic projects first
3. **Validate**: Run for 1 week, verify stability
4. **Roll out to team**: Everyone installs, migrates remaining projects

**Timeline:** 1 week for team of 5 with 10 projects

## FAQ

### Q: Can I use both modes simultaneously?

A: Yes, plugin mode and per-project mode can coexist. Projects with full `.claude/` directories use per-project mode. Projects with minimal `.claude/settings.json` use plugin mode.

### Q: What happens to my runtime data (logs, cache)?

A: Runtime data is preserved in `.claude/runtime/` in each project. Migration doesn't touch runtime directories.

### Q: Do I need to migrate all projects at once?

A: No, you can migrate incrementally. Install the plugin once, then migrate projects individually or in batches.

### Q: Will this break my CI/CD pipelines?

A: No, as long as CI environments have the plugin installed. Add to your CI setup:

```yaml
# .github/workflows/test.yml
- name: Install amplihack plugin
  run: |
    pip install amplihack
    amplihack plugin install
```

### Q: What if I have multiple versions of amplihack across projects?

A: Plugin mode enforces consistent versions. If you need different versions per project, consider using virtual environments or separate plugin installations.

### Q: Can I customize the plugin for specific projects?

A: Yes, use `.claude/settings.json` to override plugin defaults. See [ARCHITECTURE.md](./ARCHITECTURE.md) for settings merger details.

## Related Documentation

- [Installation Guide](./INSTALLATION.md) - Install the plugin from scratch
- [Architecture Overview](./ARCHITECTURE.md) - Understand how the plugin works
- [CLI Reference](./CLI_REFERENCE.md) - Complete migration command documentation
- [Multi-IDE Setup](./MULTI_IDE.md) - Configure plugin for different IDEs

---

**Last updated:** 2026-01-19
**Plugin version:** 1.0.0
