# Migration Guide: Per-Project t' Plugin

Guide fer migratin' from per-project `~/.amplihack/.claude/` installations t' the global plugin architecture.

## Overview

This guide helps ye transition from copyin' `~/.amplihack/.claude/` into each project t' usin' the global plugin at `~/.amplihack/.claude/`.

**Migration Path:**

```
Before (Per-Project)              After (Plugin)
─────────────────────             ──────────────
~/project1/.claude/    ────┐
~/project2/.claude/    ────┼────▶  ~/.amplihack/.claude/
~/project3/.claude/    ────┘          (single installation)
```

## Benefits o' Plugin Mode

### Automatic Updates
- Plugin updates affect all projects instantly
- No need t' copy `~/.amplihack/.claude/` to each project
- Always use latest agents and commands

### Consistent Behavior
- Same workflow across all projects
- Standardized agent responses
- Predictable hook behavior

### Simplified Management
- One location fer all customizations
- Easier t' track changes
- Simpler backup and version control

### Disk Space Savings
- One `~/.amplihack/.claude/` directory instead o' N copies
- 50MB saved per project (typical)
- Example: 10 projects = 500MB saved

## When t' Migrate

### Recommended Cases

**✅ Migrate t' Plugin When:**
- Ye work on multiple projects
- Ye want automatic updates across all projects
- Ye use standard amplihack without customizations
- Ye want zero-configuration setup

**Example Workflow:**
```bash
# Install plugin once
amplihack plugin install

# All projects use plugin automatically
cd ~/project1 && amplihack launch  # Uses plugin
cd ~/project2 && amplihack launch  # Uses same plugin
cd ~/project3 && amplihack launch  # Still uses plugin
```

### Keep Per-Project Mode

**🏴‍☠️ Stay Per-Project When:**
- Ye need project-specific agent customizations
- Ye want t' pin amplihack version fer stability
- Ye be experimentin' with custom workflows
- Ye need different configurations per project

**Example Workflow:**
```bash
# Each project has own .claude/
cd ~/project1 && amplihack launch  # Uses project1/.claude/
cd ~/project2 && amplihack launch  # Uses project2/.claude/
```

## Migration Methods

### Method 1: Clean Migration (Recommended)

Complete migration t' plugin with cleanup o' old installations.

**Steps:**

1. **Verify No Custom Modifications**

```bash
cd ~/project
amplihack mode status
```

Check fer custom files in `~/.amplihack/.claude/` (agents, commands, skills ye added).

2. **Install Plugin**

```bash
amplihack plugin install https://github.com/rysweet/amplihack
```

Output:
```
✅ Plugin installed: amplihack
   Location: /home/user/.amplihack/.claude/
   Plugin be ready fer use!
```

3. **Migrate Project**

```bash
cd ~/project
amplihack mode migrate-to-plugin
```

Output:
```
Removing local .claude/ from /home/user/project
Migration complete. Project now uses plugin.
```

4. **Verify Migration**

```bash
amplihack mode status
```

Output:
```
Current mode: plugin
  Using: /home/user/.amplihack/.claude
```

5. **Repeat fer Each Project**

```bash
cd ~/project2
amplihack mode migrate-to-plugin

cd ~/project3
amplihack mode migrate-to-plugin
```

### Method 2: Gradual Migration

Migrate projects one at a time, testin' each before proceedin'.

**Steps:**

1. **Install Plugin**

```bash
amplihack plugin install
```

2. **Test with New Project First**

```bash
cd ~/new-test-project
# No .claude/ directory here
amplihack launch
```

Plugin be used automatically (no local `~/.amplihack/.claude/` exists).

3. **Migrate Low-Risk Project**

```bash
cd ~/simple-project
amplihack mode migrate-to-plugin
```

4. **Test Thoroughly**

```bash
# Run typical workflow
amplihack launch -- -p "implement simple feature"

# Verify agents work
# Verify commands work
# Verify hooks execute
```

5. **Migrate Remainin' Projects**

Once satisfied, migrate others:

```bash
cd ~/important-project
amplihack mode migrate-to-plugin
```

### Method 3: Hybrid Mode

Keep plugin fer most projects, local `~/.amplihack/.claude/` fer specific ones.

**Use Case**: 90% o' projects use plugin, but one project needs custom agents.

**Steps:**

1. **Install Plugin**

```bash
amplihack plugin install
```

2. **Migrate Standard Projects**

```bash
cd ~/standard-project1
amplihack mode migrate-to-plugin

cd ~/standard-project2
amplihack mode migrate-to-plugin
```

3. **Keep Custom Project Unchanged**

```bash
cd ~/custom-project
# Leave .claude/ directory intact
amplihack launch  # Uses local .claude/ (precedence)
```

**Mode Detection:**
- Projects without `~/.amplihack/.claude/` → Use plugin
- Projects with `~/.amplihack/.claude/` → Use local (override)

## Preservin' Customizations

If ye have custom agents, commands, or skills in `~/.amplihack/.claude/`, preserve 'em before migratin'.

### Backup Custom Files

```bash
cd ~/project

# List custom files
find .claude -type f -name "*.md" -o -name "*.py" | grep -E "(agents|commands|skills)"

# Create backup
mkdir -p ~/amplihack-customizations/$(basename $(pwd))
cp -r .claude/agents/custom-agent.md ~/amplihack-customizations/$(basename $(pwd))/
cp -r .claude/commands/custom-command/ ~/amplihack-customizations/$(basename $(pwd))/
```

### Move Customizations t' Plugin

After installin' plugin, add yer custom content:

```bash
# Copy custom agent to plugin
cp ~/amplihack-customizations/project1/custom-agent.md \
   ~/.amplihack/.claude/agents/amplihack/specialized/

# Copy custom command to plugin
cp -r ~/amplihack-customizations/project1/custom-command \
      ~/.amplihack/.claude/commands/amplihack/

# Now available in ALL projects
```

### Alternative: Keep Project-Specific Customizations

If customizations be specific t' one project:

```bash
# Don't migrate this project
cd ~/custom-project
# Keep .claude/ directory

# Plugin used for other projects
cd ~/standard-project
amplihack mode migrate-to-plugin
```

## Revertin' Migration

T' go back t' per-project mode:

```bash
cd ~/project
amplihack mode migrate-to-local
```

Output:
```
Creating local .claude/ from plugin
Migration complete. Project now uses local .claude/
You can now customize .claude/ for this project.
```

**Result**: Project has own `~/.amplihack/.claude/` copy (local precedence).

## Verification Steps

After migration, verify everythin' works:

### 1. Check Mode

```bash
amplihack mode status
```

Expected output:
```
Current mode: plugin
  Using: /home/user/.amplihack/.claude
```

### 2. Verify Plugin Verification

```bash
amplihack plugin verify amplihack
```

Expected output:
```
Plugin: amplihack
  Installed: ✅
  Discoverable: ✅
  Hooks loaded: ✅
```

### 3. Test Workflow

```bash
cd ~/project
amplihack launch -- -p "analyze src/file.py"
```

Verify:
- [ ] Commands available (`/amplihack:ultrathink`, `/analyze`)
- [ ] Agents load correctly
- [ ] Hooks execute (session start, prompt wrap)
- [ ] Workflow runs as expected

### 4. Test Across Multiple Projects

```bash
cd ~/project1
amplihack launch -- -p "quick test"

cd ~/project2
amplihack launch -- -p "quick test"
```

Both should use same plugin.

## Troubleshootin'

### Migration Fails with Custom Files

**Symptom**:
```
Warning: Local .claude/ has custom files:
  - agents/my-custom-agent.md
  - commands/my-command/

These will be lost. Backup first or use --preserve-custom
```

**Solution**:
1. Backup custom files (see "Preservin' Customizations")
2. Migrate: `amplihack mode migrate-to-plugin`
3. Add custom files t' plugin manually

### Plugin Not Found After Migration

**Symptom**:
```
Current mode: none
  No .claude installation found
```

**Diagnosis**:
```bash
amplihack plugin verify amplihack
```

**Solution**:
```bash
# Reinstall plugin
amplihack plugin install https://github.com/rysweet/amplihack

# Verify
amplihack plugin verify amplihack
```

### Local .claude/ Still Used After Migration

**Symptom**: Project still uses local `~/.amplihack/.claude/` after migration.

**Diagnosis**:
```bash
ls -la .claude/  # Directory still exists
```

**Solution**:
```bash
# Migration didn't complete - try again
amplihack mode migrate-to-plugin --force
```

### Want t' Undo Migration

**Symptom**: Migrated but want per-project mode back.

**Solution**:
```bash
# Revert to local mode
amplihack mode migrate-to-local

# Verify
amplihack mode status
# Output: Current mode: local
```

## Best Practices

### 1. Test Before Full Migration

```bash
# Install plugin
amplihack plugin install

# Test with one low-risk project
cd ~/test-project
amplihack mode migrate-to-plugin

# Verify everything works
# Then migrate others
```

### 2. Backup Custom Content

```bash
# Before migration
tar -czf ~/amplihack-backup-$(date +%Y%m%d).tar.gz \
  ~/.claude/ \
  ~/project1/.claude/ \
  ~/project2/.claude/
```

### 3. Document Project-Specific Needs

Create `PROJECT.md` in each project:

```markdown
## Amplihack Mode

This project uses: **plugin mode**

Reason: Standard workflow, no custom agents

Migration date: 2025-01-17
```

### 4. Update .gitignore

If ye previously committed `~/.amplihack/.claude/` t' git:

```bash
# Add to .gitignore
echo ".claude/" >> .gitignore

# Remove from git
git rm -r --cached .claude/
git commit -m "Remove .claude/ (now using plugin)"
```

## Migration Checklist

Use this checklist fer each project:

```markdown
## Project: [NAME]

- [ ] Verify no custom content in .claude/
- [ ] Backup .claude/ if customs exist
- [ ] Install plugin: `amplihack plugin install`
- [ ] Migrate: `amplihack mode migrate-to-plugin`
- [ ] Verify: `amplihack mode status`
- [ ] Test workflow: Basic command execution
- [ ] Test agents: Run typical tasks
- [ ] Update .gitignore (if needed)
- [ ] Document in PROJECT.md
```

## FAQs

**Q: Can I use both plugin and local .claude/ simultaneously?**

A: Aye, local `~/.amplihack/.claude/` takes precedence. Plugin be used as fallback when no local installation exists.

**Q: What happens t' my customizations?**

A: They be lost unless backed up. See "Preservin' Customizations" section.

**Q: Can I migrate back t' per-project mode?**

A: Aye, run `amplihack mode migrate-to-local` in any project.

**Q: How do I update the plugin?**

A: Reinstall: `amplihack plugin install --force https://github.com/rysweet/amplihack`

**Q: Does migration affect git history?**

A: No, unless ye committed `~/.amplihack/.claude/` t' git. If so, remove it from git after migration.

**Q: What if migration fails?**

A: Run `amplihack mode migrate-to-plugin --force` or reinstall plugin first.

## Next Steps

After successful migration:

1. **Customize Plugin** (optional): Add project-agnostic custom agents t' `~/.amplihack/.claude/agents/`
2. **Update Documentation**: Note migration in project README
3. **Monitor Performance**: Verify plugin works across all projects
4. **Report Issues**: File issues at https://github.com/rysweet/amplihack/issues

## References

- [Plugin Architecture](./PLUGIN_ARCHITECTURE.md)
- [README Plugin Section](../README.md#plugin-installation)
- [Backward Compatibility Spec](../Specs/BACKWARD_COMPATIBILITY.md)
