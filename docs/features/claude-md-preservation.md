# CLAUDE.md Preservation During Installation

**Protects your custom CLAUDE.md file when installing amplihack via uvx.**

## What This Feature Does

When ye install amplihack via `uvx`, the system automatically preserves any custom CLAUDE.md file ye've already created in yer project. Instead of overwritin' yer careful customizations, amplihack:

1. **Detects** existing CLAUDE.md customizations
2. **Backs up** yer custom content to safe locations
3. **Merges** amplihack's default CLAUDE.md with clear section markers
4. **Preserves** original backups fer recovery

This means ye can safely reinstall or upgrade amplihack without losin' yer project-specific configuration.

## Quick Start

**For most users**: Just install amplihack as normal. The preservation happens automatically.

```bash
uvx --from amplihack amplihack
```

If ye already have a CLAUDE.md file with custom content, it'll be preserved automatically on first run.

## How It Works

### Installation Flow

When amplihack initializes in yer project:

```
1. Check if CLAUDE.md exists
2. Analyze content (stock vs. customized)
3. If customized:
   → Create backup in .claude/context/PROJECT.md
   → Create additional backup in .claude/context/CLAUDE.md.preserved
   → Install amplihack's CLAUDE.md with section markers
4. Continue normal initialization
```

### When Preservation Happens

**Timing: Post-Installation Hook (BEFORE amplihack touches anything)**

The preservation system runs as a **post-installation hook** during package installation, protectin' yer custom CLAUDE.md BEFORE amplihack's initialization modifies any files.

**UVX Installation Flow**:

```
1. User runs: uvx --from amplihack amplihack
2. UVX downloads amplihack package
3. UVX installs package dependencies
4. **POST-INSTALL HOOK EXECUTES** ← Preservation happens here
   → Detects existing CLAUDE.md
   → Creates backups if custom content found
   → Marks preservation complete
5. amplihack launcher starts
6. Normal initialization proceeds (CLAUDE.md already protected)
```

**Key Point**: Protection happens BEFORE amplihack touches anything. By the time the launcher starts, yer custom content is already safely backed up.

### State Detection

The system identifies three states:

| State         | Description                             | Action             |
| ------------- | --------------------------------------- | ------------------ |
| **Stock**     | No CLAUDE.md or only amplihack defaults | Install normally   |
| **Preserved** | Custom content already backed up        | Skip (idempotent)  |
| **Hybrid**    | Custom CLAUDE.md not yet backed up      | Preserve and merge |

## Backup Locations

Yer custom content is preserved in **two places** fer safety:

### Primary Backup: PROJECT.md

```
.claude/context/PROJECT.md
```

Yer custom CLAUDE.md content is merged into PROJECT.md with clear section markers:

```markdown
## Project: [Your Project Name]

## Overview

[Your custom content here]

## Architecture

[Your custom content here]

---

<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT 2025-11-30T14:23:45.123456 -->

Preserved from original CLAUDE.md

[Your full original CLAUDE.md content]

## <!-- END AMPLIHACK-PRESERVED-CONTENT -->
```

**Marker Format**:

- `BEGIN AMPLIHACK-PRESERVED-CONTENT` - Start marker with ISO 8601 timestamp
- `END AMPLIHACK-PRESERVED-CONTENT` - End marker
- HTML comment style (`<!-- -->`) to avoid rendering in markdown viewers
- Timestamp format: `YYYY-MM-DDTHH:MM:SS.microseconds` (local timezone)

**Why PROJECT.md?** This file is automatically read by all amplihack agents at session start, so yer project context remains accessible.

### Secondary Backup: CLAUDE.md.preserved

```
.claude/context/CLAUDE.md.preserved
```

A complete, unmodified copy of yer original CLAUDE.md file with a timestamp header:

```markdown
# Preserved CLAUDE.md Content

# Original file preserved on: 2025-11-30T14:23:45.123456

# This file contains your original CLAUDE.md before amplihack installation

[Your complete original CLAUDE.md]
```

**Timestamp Format**: ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.microseconds`) in local timezone, providin' precise preservation time fer audit trails and recovery purposes.

**Why two backups?** Redundancy ensures ye never lose yer custom configuration, even if one backup is accidentally modified.

## Common Scenarios

### Scenario 1: First Installation

Ye have an existing CLAUDE.md with project-specific configuration:

```bash
$ ls CLAUDE.md
CLAUDE.md  # Your custom file exists

$ uvx --from amplihack amplihack
🔍 Detected custom CLAUDE.md content
💾 Preserving to .claude/context/PROJECT.md
💾 Creating backup at .claude/context/CLAUDE.md.preserved
✅ Your custom content is preserved
```

**Result**:

- Yer original content → `~/.amplihack/.claude/context/PROJECT.md` (primary)
- Complete backup → `~/.amplihack/.claude/context/CLAUDE.md.preserved`
- New amplihack CLAUDE.md installed

### Scenario 2: Reinstallation

Ye're reinstallin' or upgradin' amplihack:

```bash
$ uvx --from amplihack amplihack
✅ Custom CLAUDE.md already preserved
→ Found backup at .claude/context/CLAUDE.md.preserved
```

**Result**: No changes. Idempotent - safe to run multiple times.

### Scenario 3: Clean Project

Ye're installin' amplihack in a new project with no CLAUDE.md:

```bash
$ uvx --from amplihack amplihack
✅ Installing amplihack CLAUDE.md
```

**Result**: Standard amplihack CLAUDE.md installed, no preservation needed.

## Idempotency

**Safe to reinstall**: The preservation system is idempotent, meanin' ye can run installation multiple times without risk:

- **First run**: Preserves yer custom content
- **Subsequent runs**: Detects existing backups, skips preservation
- **Never overwrites**: Backups are created only once

```bash
# Safe - run as many times as needed
uvx --from amplihack amplihack
uvx --from amplihack amplihack  # No changes
uvx --from amplihack amplihack  # Still no changes
```

## Checking Preservation Status

To verify yer content was preserved:

```bash
# Check primary backup in PROJECT.md
cat .claude/context/PROJECT.md | grep "AMPLIHACK-PRESERVED-CONTENT"

# Check secondary backup
ls -la .claude/context/CLAUDE.md.preserved
```

If both files exist, yer content is safe.

## Manual Recovery

If ye need to restore yer original CLAUDE.md manually:

```bash
# From the preserved backup
cp .claude/context/CLAUDE.md.preserved CLAUDE.md

# Or extract from PROJECT.md
# Look for the AMPLIHACK-PRESERVED-CONTENT section
```

## Troubleshooting

### Backup Not Created

**Symptom**: Installed amplihack but don't see `~/.amplihack/.claude/context/CLAUDE.md.preserved`

**Possible causes**:

1. Yer CLAUDE.md was identical to amplihack's default (no custom content)
2. Installation was interrupted before preservation completed

**Solution**: Check `~/.amplihack/.claude/context/PROJECT.md` fer the AMPLIHACK-PRESERVED-CONTENT section. If present, yer content was preserved there.

### Content Appears Lost

**Symptom**: Can't find yer custom configuration after installation

**Solution**: Check both backup locations:

```bash
# Primary backup
grep -A 50 "AMPLIHACK-PRESERVED-CONTENT" .claude/context/PROJECT.md

# Secondary backup
cat .claude/context/CLAUDE.md.preserved
```

If neither exists, the system determined yer CLAUDE.md was stock (unmodified amplihack content).

### Want to Keep Custom CLAUDE.md

**Symptom**: Ye want to keep usin' yer own CLAUDE.md instead of amplihack's

**Solution**: After installation, restore yer backup and don't commit amplihack's CLAUDE.md:

```bash
# Restore original
cp .claude/context/CLAUDE.md.preserved CLAUDE.md

# Add to .gitignore if desired
echo "CLAUDE.md" >> .gitignore
```

Amplihack will still function - it only reads from `~/.amplihack/.claude/context/` files, not CLAUDE.md itself.

## Integration with Agents

Yer preserved content in PROJECT.md is automatically available to all amplihack agents because:

1. **Auto-imported**: PROJECT.md is listed in CLAUDE.md's "Important Files to Import"
2. **Session start**: Loaded automatically when any amplihack session begins
3. **Agent context**: All agents receive PROJECT.md content as part of their initial context

This means yer project-specific information (domain knowledge, architecture, conventions) remains accessible without manual intervention.

## Technical Details

### Detection Logic

The system identifies custom content through a multi-stage analysis:

1. **Existence check**: Does CLAUDE.md exist in the project root?

2. **Content analysis** - What qualifies as "custom":
   - **Content hash comparison**: Compute SHA-256 hash of file and compare with known amplihack versions
   - **Line-by-line diff**: If hashes don't match, analyze differences
   - **Whitespace handling**: Ignore whitespace-only changes (trailing spaces, blank lines)
   - **Qualification**: Any non-whitespace content difference = custom content
   - **Version marker check**: Missing version marker = assumed custom

3. **Backup check**: Is `~/.amplihack/.claude/context/CLAUDE.md.preserved` already present?
   - If yes → preservation already complete (idempotent)
   - If no → preservation needed

4. **Marker check**: Does PROJECT.md contain AMPLIHACK-PRESERVED-CONTENT section?
   - If yes → preservation already complete (idempotent)
   - If no → preservation needed

**Detection Decision Tree**:

```
CLAUDE.md exists?
  ├─ No → Install stock CLAUDE.md (state: MISSING)
  └─ Yes → Content analysis
       ├─ Hash matches amplihack → Install stock CLAUDE.md (state: STOCK)
       ├─ Backup exists OR marker found → Skip (state: PRESERVED, idempotent)
       └─ Hash differs AND no backup → Preserve and install (state: HYBRID)
```

### Preservation Process

```python
# Simplified preservation flow
if claude_md_exists():
    if has_custom_content():
        if not already_preserved():
            backup_to_project_md()
            backup_to_preserved_file()
            install_amplihack_claude_md()
        else:
            skip_preservation()  # Idempotent
    else:
        install_amplihack_claude_md()
```

### File Operations

All file operations are:

- **Atomic**: Create backups before modifying originals
- **Timestamped**: Each backup includes creation timestamp
- **Validated**: Verify content written successfully before proceeding

## Best Practices

### For New Projects

Start with amplihack's CLAUDE.md and customize PROJECT.md:

```bash
# 1. Install amplihack
uvx --from amplihack amplihack

# 2. Customize .claude/context/PROJECT.md
vim .claude/context/PROJECT.md

# 3. Commit both files
git add CLAUDE.md .claude/context/PROJECT.md
git commit -m "Configure amplihack for project"
```

### For Existing Projects

Let preservation handle yer existing CLAUDE.md:

```bash
# 1. Ensure CLAUDE.md is committed
git add CLAUDE.md
git commit -m "Save custom CLAUDE.md before amplihack"

# 2. Install amplihack (preservation automatic)
uvx --from amplihack amplihack

# 3. Verify preservation
cat .claude/context/CLAUDE.md.preserved

# 4. Commit amplihack files
git add CLAUDE.md .claude/
git commit -m "Add amplihack with preserved config"
```

### For Teams

Coordinate CLAUDE.md vs. PROJECT.md usage:

- **CLAUDE.md**: Team-wide amplihack configuration (commit)
- **PROJECT.md**: Project-specific context (commit)
- **CLAUDE.md.preserved**: Local backup (add to .gitignore)

```bash
# .gitignore
.claude/context/CLAUDE.md.preserved
```

## Scope and Limitations

### What's Preserved

✅ Custom project configuration in CLAUDE.md
✅ Project-specific agent instructions
✅ Team workflow customizations
✅ Domain-specific terminology and context

### What's Not Preserved

❌ Experimental or temporary changes
❌ Commented-out sections (still backed up, but not merged)
❌ Changes made after preservation (manual merge needed)

### MVP Scope

This feature currently handles:

- **UVX installations only** (pip installations not yet supported)
- **CLAUDE.md file only** (other .claude/ customizations preserved separately)
- **Single preservation event** (subsequent customizations require manual merge)

## Future Enhancements

Planned improvements fer future versions:

- **Merge strategies**: Intelligent merging of updated custom content
- **Pip support**: Preservation during pip package installations
- **Multi-file preservation**: Handle all .claude/ directory customizations
- **Version tracking**: Track which amplihack version created each backup

## Related Documentation

- [Installation Prerequisites](../PREREQUISITES.md) - System requirements
- [Interactive Installation](../INTERACTIVE_INSTALLATION.md) - Step-by-step setup
- [Project Context](../../.claude/context/PROJECT.md) - Customize project information
- [Philosophy](../../.claude/context/PHILOSOPHY.md) - Understanding amplihack principles

## Summary

The CLAUDE.md preservation feature ensures yer custom project configuration survives amplihack installation by:

1. **Automatic detection** of custom content
2. **Dual backup strategy** (PROJECT.md + preserved file)
3. **Idempotent operations** (safe to reinstall)
4. **Seamless integration** with amplihack agents

Install with confidence - yer custom configuration is protected.

---

**Last updated**: 2025-11-30
**Feature status**: Implemented in amplihack v1.7.0+
**Applies to**: UVX installations
