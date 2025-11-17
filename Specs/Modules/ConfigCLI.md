# Module: ConfigCLI

## Purpose

Provide CLI commands for managing Amplihack configuration integration.

## Contract

### Commands

#### `amplihack config show`
Display current configuration status and integration state.

**Inputs**: None (uses current directory)
**Outputs**: Status report to stdout

```
Amplihack Configuration Status

Installation:
  Namespace: .claude/amplihack/
  Status: Installed
  Version: 0.2.0
  Files: 15

Integration:
  CLAUDE.md import: Present
  Import statement: @.claude/amplihack/CLAUDE.md
  User config: .claude/CLAUDE.md (125 lines)

Custom Agents:
  amplihack/agents/architect.md ✓
  amplihack/agents/builder.md ✓
  amplihack/agents/fixer.md ✓
```

#### `amplihack config integrate`
Add Amplihack import to user's CLAUDE.md (interactive).

**Inputs**:
- `--force` flag (skip confirmation)
- `--dry-run` flag (preview only)

**Outputs**: Success/failure message

**Behavior**:
1. Check current integration status
2. Show preview of changes
3. Ask for confirmation (unless --force)
4. Create backup
5. Apply changes
6. Report result

#### `amplihack config remove`
Remove Amplihack import from CLAUDE.md.

**Inputs**:
- `--keep-files` flag (remove import but keep .claude/amplihack/)

**Outputs**: Success/failure message

**Behavior**:
1. Find and remove import statement
2. Create backup before modification
3. Optionally delete .claude/amplihack/ directory
4. Report what was removed

#### `amplihack config reset`
Reset to fresh Amplihack config (destructive).

**Inputs**:
- `--force` flag (required, confirms destructive action)

**Outputs**: Success/failure message

**Behavior**:
1. Require --force flag (this is destructive)
2. Remove .claude/amplihack/ entirely
3. Reinstall from bundled files
4. Update import if present
5. Report what was reset

### Side Effects
- Reads .claude/ directory
- May modify .claude/CLAUDE.md
- May delete/create .claude/amplihack/
- Creates backup files

## Dependencies

- `ConfigConflictDetector` module
- `NamespaceInstaller` module
- `ClaudeMdIntegrator` module
- `rich` for formatted output (optional, graceful fallback)
- `click` for CLI framework

## Implementation Notes

### User Interaction Flow

For `integrate`:
```
This will add Amplihack configuration to your .claude/CLAUDE.md:

  Preview:
  + @.claude/amplihack/CLAUDE.md

  Your existing content will be preserved.
  A backup will be created at: .claude/CLAUDE.md.backup.20250110_143022

Continue? [y/N]:
```

For `remove`:
```
This will remove Amplihack integration from .claude/CLAUDE.md

  The .claude/amplihack/ directory will be DELETED.
  A backup will be created at: .claude/CLAUDE.md.backup.20250110_143022

Continue? [y/N]:
```

### Error Handling

- Not in Claude project: "Error: Not in a Claude project. No .claude/ directory found."
- Amplihack not installed: "Error: Amplihack not installed. Run 'amplihack install' first."
- Permission errors: Show clear message with suggested fix
- Already integrated: "Already integrated. Use 'amplihack config show' to see status."

## Key Design Decisions

- All commands are read-only except with explicit user confirmation
- Status command is always safe (no modifications)
- Backups created before any destructive action
- Clear preview before applying changes
- Graceful degradation without rich library

## Edge Cases

- Commands run outside Claude project
- Amplihack not installed
- Partial installation
- Corrupted config files
- Permission errors
- Multiple concurrent operations

## Test Requirements

- Show status correctly (installed, not installed, partially installed)
- Preview changes accurately
- Require confirmation for destructive operations
- Create backups before modifications
- Handle missing directories gracefully
- Work without rich library
- Handle permission errors
- Detect concurrent operations
