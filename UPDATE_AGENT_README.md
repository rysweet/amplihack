# Update Agent Command - Implementation Complete

## Overview

The `amplihack update-agent` command is now fully implemented! This command allows users to update existing goal agents with the latest improvements from amplihack while preserving custom code.

## Features Implemented

### Core Modules

1. **VersionDetector** (`src/amplihack/goal_agent_generator/update_agent/version_detector.py`)
   - Detects agent version from `.amplihack_version`, `agent_config.json`, or `metadata.json`
   - Identifies infrastructure phase (phase1, phase2, phase3, phase4)
   - Discovers installed skills
   - Identifies custom user files

2. **ChangesetGenerator** (`src/amplihack/goal_agent_generator/update_agent/changeset_generator.py`)
   - Generates update changesets comparing current and target versions
   - Identifies infrastructure updates
   - Finds new and updated skills
   - Classifies changes as safe, review-required, or breaking
   - Provides bug fixes and enhancements list

3. **BackupManager** (`src/amplihack/goal_agent_generator/update_agent/backup_manager.py`)
   - Creates timestamped backups in `.backups/` directory
   - Lists available backups
   - Restores from backups with rollback on failure
   - Cleans up old backups
   - Excludes cache and backup directories from backups

4. **SelectiveUpdater** (`src/amplihack/goal_agent_generator/update_agent/selective_updater.py`)
   - Applies selected infrastructure updates
   - Updates skills selectively
   - Validates agent after updates (syntax, JSON, required files)
   - Preserves custom code
   - Updates version file

### Data Models

Added to `src/amplihack/goal_agent_generator/models.py`:

- `AgentVersionInfo` - Information about installed agent
- `FileChange` - Single file change with safety classification
- `SkillUpdate` - Skill update information
- `UpdateChangeset` - Complete set of changes with metadata

### CLI Command

Command: `amplihack update-agent <agent_dir> [options]`

Options:
- `--check-only` - Check for updates without applying
- `--auto` - Auto-apply safe updates without prompting
- `--backup/--no-backup` - Control backup creation (default: yes)
- `--target-version VERSION` - Specify target version (default: latest)
- `--verbose/-v` - Enable verbose output

### Test Suite

Comprehensive tests in `src/amplihack/goal_agent_generator/tests/test_update_agent.py`:
- 22 tests covering all modules
- All tests passing
- Tests for version detection, changesets, backups, updates, and validation

## Usage Examples

### Check for updates
```bash
amplihack update-agent ./my-agent --check-only
```

### Update with prompts
```bash
amplihack update-agent ./my-agent
```

### Auto-update (safe changes only)
```bash
amplihack update-agent ./my-agent --auto
```

### Update without backup
```bash
amplihack update-agent ./my-agent --no-backup
```

### Verbose mode
```bash
amplihack update-agent ./my-agent --verbose
```

## Workflow

1. **Detect Version** - Analyzes agent directory to determine current state
2. **Check Updates** - Compares with latest amplihack version
3. **Show Diff** - Presents available updates with safety markers:
   - ✓ Safe to auto-apply
   - ⚠ Review recommended
   - ✗ Breaking change
4. **Get Approval** - Interactive confirmation (unless `--auto`)
5. **Create Backup** - Saves current state to `.backups/`
6. **Apply Updates** - Selectively updates infrastructure and skills
7. **Validate** - Verifies agent still works
8. **Report** - Shows what changed

## Safety Features

1. **Automatic Backups** - Always creates backup before updating (unless disabled)
2. **Rollback on Failure** - Restores backup if validation fails
3. **Custom Code Preservation** - Never overwrites user modifications
4. **Safety Classification** - Each change marked as safe/review/breaking
5. **Validation** - Checks Python syntax, JSON validity, required files

## Architecture

```
update_agent/
├── __init__.py              # Public interface
├── version_detector.py      # Detect agent version
├── changeset_generator.py   # Find available updates
├── backup_manager.py        # Create/restore backups
└── selective_updater.py     # Apply updates
```

## Integration

Integrated into main CLI (`src/amplihack/cli.py`):
- Added argparse subcommand
- Wired up to update_agent_cli module
- Available as `amplihack update-agent`

## Testing Results

All 22 tests pass:
- ✓ Version detection (6 tests)
- ✓ Changeset generation (3 tests)
- ✓ Backup management (5 tests)
- ✓ Selective updates (4 tests)
- ✓ Data models (4 tests)

## Success Criteria Met

✅ Command works: `amplihack update-agent ./my-agent`
✅ Detects agent version correctly
✅ Shows available updates
✅ Preserves custom code
✅ Creates backups
✅ Validates after update
✅ Tests pass (22/22)

## Future Enhancements

Potential improvements for future iterations:

1. **3-Way Merge** - Intelligent conflict resolution for modified infrastructure files
2. **GitHub Integration** - Query actual release notes and changelogs
3. **Diff Viewer** - Interactive diff viewer with syntax highlighting
4. **Selective Update UI** - Checkbox interface for selecting individual updates
5. **Update Notifications** - Check for updates automatically
6. **Version Pinning** - Update to specific versions
7. **Skill Deprecation** - Handle deprecated skills gracefully
8. **Migration Scripts** - Run custom migration scripts for complex updates

## Implementation Notes

The implementation follows the "Bricks & Studs" philosophy:
- Self-contained modules with clear interfaces
- Working code only - no stubs or placeholders
- Regeneratable from specifications
- Comprehensive test coverage
- Clear error messages and validation

All modules are production-ready and fully functional.
