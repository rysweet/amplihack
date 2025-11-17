# Specification: Configuration File Conflict Handling

**Issue**: #1279
**Status**: Design Complete, Ready for Implementation
**Version**: 1.0
**Date**: 2025-01-10

## Executive Summary

This specification solves the problem of Amplihack configuration files potentially overwriting user's existing `.claude/` configuration. The solution uses **namespaced installation** with **opt-in integration**, giving users full control while maintaining simple UX.

## Problem Statement

Currently, `copytree_manifest()` may overwrite:
- User's existing `.claude/CLAUDE.md`
- User's custom agents in `.claude/agents/`
- Other user configuration files

This is unacceptable because:
1. Destroys user work without consent
2. Prevents users from having custom configuration
3. Makes upgrades risky
4. Violates principle of least surprise

## Solution Architecture

### Core Strategy: Namespace + Import

```
.claude/
├── CLAUDE.md              ← User's file (we add one line)
├── agents/                ← User's agents (untouched)
│   └── custom.md
└── amplihack/             ← Amplihack namespace (we own this)
    ├── CLAUDE.md          ← Amplihack config
    ├── agents/            ← Amplihack agents
    │   ├── architect.md
    │   ├── builder.md
    │   └── fixer.md
    ├── context/           ← Amplihack context
    └── commands/          ← Amplihack commands
```

**Integration**: Single import line in user's CLAUDE.md:
```markdown
@.claude/amplihack/CLAUDE.md
```

### Design Principles

1. **Namespace Everything**: All Amplihack files go in `.claude/amplihack/`
2. **Explicit Consent**: Never modify user files without permission
3. **Reversible**: All operations can be undone
4. **Safe by Default**: No overwrites without confirmation
5. **Simple Mental Model**: "Amplihack stays in its box"

## Module Architecture

The system consists of 5 modules that compose cleanly:

```
InstallationOrchestrator
├─→ ConfigConflictDetector (detect existing files)
├─→ NamespaceInstaller (copy files to namespace)
└─→ ClaudeMdIntegrator (add import line)

ConfigCLI
├─→ ConfigConflictDetector (show status)
├─→ NamespaceInstaller (reset/reinstall)
└─→ ClaudeMdIntegrator (integrate/remove)
```

### Module Specifications

Detailed specifications for each module:

1. **ConfigConflictDetector**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/ConfigConflictDetector.md`
   - Detects existing files
   - Reports conflicts
   - Read-only operation

2. **NamespaceInstaller**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/NamespaceInstaller.md`
   - Installs to `.claude/amplihack/`
   - Handles upgrades
   - Never touches user files

3. **ClaudeMdIntegrator**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/ClaudeMdIntegrator.md`
   - Adds import statement
   - Creates backups
   - Idempotent operation

4. **ConfigCLI**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/ConfigCLI.md`
   - User-facing commands
   - Status reporting
   - Manual control

5. **InstallationOrchestrator**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/InstallationOrchestrator.md`
   - Coordinates workflow
   - Handles user interaction
   - Mode-aware (install vs UVX)

## User Experience Flows

### Flow 1: Fresh Installation (No Existing Config)

```bash
$ amplihack install
```

**System Behavior**:
1. Detects no conflicts
2. Installs to `.claude/amplihack/`
3. Creates minimal `.claude/CLAUDE.md` with import
4. Shows success message

**Result**:
```
✓ Amplihack installed successfully!

  Installation: .claude/amplihack/
  Integration: Created .claude/CLAUDE.md with import

Ready to use! Try @architect to start.
```

### Flow 2: Installation with Existing Config

```bash
$ amplihack install
```

**System Behavior**:
1. Detects existing `.claude/CLAUDE.md`
2. Installs to `.claude/amplihack/`
3. Prompts to add import:

```
Amplihack has been installed to .claude/amplihack/

To activate it, we can add an import to your .claude/CLAUDE.md:

  @.claude/amplihack/CLAUDE.md

This allows Claude to use Amplihack's agents and tools.
Your existing content will be preserved.
A backup will be created.

Add import to CLAUDE.md? [Y/n]:
```

4. If yes: adds import, creates backup
5. If no: shows manual instructions

**Result (if yes)**:
```
✓ Amplihack installed and integrated!

  Installation: .claude/amplihack/
  Integration: Added to .claude/CLAUDE.md
  Backup: .claude/CLAUDE.md.backup.20250110_143022

Ready to use!
```

**Result (if no)**:
```
✓ Amplihack installed successfully!

  Installation: .claude/amplihack/

To activate, add this line to your .claude/CLAUDE.md:
  @.claude/amplihack/CLAUDE.md

Or run: amplihack config integrate
```

### Flow 3: Upgrade Existing Installation

```bash
$ amplihack install
```

**System Behavior**:
1. Detects existing `.claude/amplihack/`
2. Prompts for upgrade confirmation
3. Backs up existing amplihack directory
4. Installs new version
5. Import already present (no change needed)

```
Amplihack is already installed at .claude/amplihack/

This will upgrade your installation to version 0.2.1.
Your existing configuration will be backed up.

Continue? [Y/n]:
```

### Flow 4: Manual Configuration Management

```bash
# Check status
$ amplihack config show
Amplihack Configuration Status

Installation:
  Namespace: .claude/amplihack/
  Status: Installed
  Version: 0.2.1
  Files: 15

Integration:
  CLAUDE.md import: Present
  Import statement: @.claude/amplihack/CLAUDE.md
  User config: .claude/CLAUDE.md (125 lines)

# Add integration manually
$ amplihack config integrate
This will add Amplihack configuration to your .claude/CLAUDE.md:

  Preview:
  + @.claude/amplihack/CLAUDE.md

Continue? [y/N]: y

✓ Integration added successfully!
  Backup: .claude/CLAUDE.md.backup.20250110_143022

# Remove integration
$ amplihack config remove
This will remove Amplihack integration from .claude/CLAUDE.md

  The .claude/amplihack/ directory will be kept.
  A backup will be created.

Continue? [y/N]: y

✓ Integration removed successfully!
  Backup: .claude/CLAUDE.md.backup.20250110_143022

# Reset to clean state
$ amplihack config reset --force
✓ Amplihack configuration reset successfully!

  Removed: .claude/amplihack/
  Reinstalled: Fresh configuration
  Import: Updated in CLAUDE.md
```

### Flow 5: UVX Mode (Ephemeral)

```bash
$ uvx amplihack
```

**System Behavior**:
1. Installs to `.claude/amplihack/` (needed for imports)
2. Skips CLAUDE.md integration (temporary session)
3. Shows UVX-specific message

```
✓ Amplihack ready for this session!

  Installation: .claude/amplihack/ (temporary)

Note: In UVX mode, changes won't persist between sessions.
For persistent installation, use: pip install amplihack
```

## Implementation Plan

### Phase 1: Core Modules (MVP)
**Priority**: Critical
**Estimate**: 2-3 hours

Implement in order:
1. `ConfigConflictDetector` - Foundation for all other modules
2. `NamespaceInstaller` - Core installation logic
3. `ClaudeMdIntegrator` - Config file modification

**Acceptance Criteria**:
- Can detect conflicts accurately
- Can install to namespace without overwrites
- Can add/remove import statement safely
- All modules have unit tests
- Backup creation works correctly

### Phase 2: Orchestration
**Priority**: Critical
**Estimate**: 2-3 hours

Implement:
4. `InstallationOrchestrator` - Workflow coordination
5. Integration with existing `amplihack install` command

**Acceptance Criteria**:
- Install command uses new orchestrator
- User prompts work correctly
- Both install and UVX modes work
- Upgrade scenario handled properly
- Error messages are clear

### Phase 3: CLI Commands
**Priority**: High
**Estimate**: 2-3 hours

Implement:
6. `ConfigCLI` - User-facing commands
7. Command registration in main CLI

**Acceptance Criteria**:
- All config commands work
- Status reporting is accurate
- Integration/removal works
- Reset command is safe
- Help text is clear

### Phase 4: Polish & Testing
**Priority**: Medium
**Estimate**: 1-2 hours

- Integration tests for complete flows
- Error handling improvements
- Documentation updates
- Edge case coverage

## Testing Strategy

### Unit Tests

Each module needs comprehensive unit tests:

```python
# test_config_conflict_detector.py
def test_detect_no_conflicts_empty_dir()
def test_detect_existing_claude_md()
def test_detect_conflicting_agents()
def test_detect_upgrade_scenario()
def test_handle_permission_errors()

# test_namespace_installer.py
def test_install_to_empty_namespace()
def test_install_fails_without_force()
def test_install_with_force_overwrites()
def test_install_preserves_structure()
def test_install_handles_permission_errors()

# test_claude_md_integrator.py
def test_add_import_to_existing_file()
def test_create_new_file_with_import()
def test_detect_existing_import()
def test_remove_import()
def test_backup_creation()
def test_dry_run_no_changes()

# test_config_cli.py
def test_show_command_displays_status()
def test_integrate_prompts_user()
def test_remove_prompts_user()
def test_reset_requires_force()

# test_installation_orchestrator.py
def test_fresh_install_flow()
def test_upgrade_flow()
def test_conflict_resolution_flow()
def test_uvx_mode_flow()
```

### Integration Tests

Test complete user flows:

```python
def test_install_to_clean_project()
def test_install_with_existing_config()
def test_upgrade_existing_installation()
def test_config_integrate_and_remove()
def test_config_reset()
def test_uvx_mode_installation()
```

### Manual Testing Checklist

- [ ] Fresh install on empty project
- [ ] Install with existing CLAUDE.md
- [ ] Install with existing custom agents
- [ ] Upgrade from previous version
- [ ] Config show command accuracy
- [ ] Config integrate with confirmation
- [ ] Config integrate with --force
- [ ] Config remove with cleanup
- [ ] Config reset with --force
- [ ] UVX mode installation
- [ ] Permission error handling
- [ ] Disk full error handling
- [ ] Backup restoration
- [ ] Multiple concurrent installations
- [ ] Symlinked .claude directory

## Migration Path

### For Existing Amplihack Installations

If user already has Amplihack installed (old style, no namespace):

```bash
$ amplihack install
```

**Detection Logic**:
1. Check if `.claude/agents/architect.md` has Amplihack signature
2. Check if `.claude/CLAUDE.md` has Amplihack content
3. If detected: offer migration

**Migration Prompt**:
```
Detected Amplihack installation in legacy format.

We can migrate to the new namespaced format:
  - Move Amplihack files to .claude/amplihack/
  - Update your CLAUDE.md to use imports
  - Preserve your custom modifications

This is recommended for easier upgrades.

Migrate to namespaced installation? [Y/n]:
```

**Migration Process**:
1. Detect which files are Amplihack's (by signature/hash)
2. Move Amplihack files to namespace
3. Leave user files in place
4. Update CLAUDE.md with import
5. Report what was moved

**Note**: This is a nice-to-have feature, not MVP. Include in Phase 4 or later.

## File Locations

### Source Code Structure

```
src/amplihack/
├── config/                    # Bundled config files
│   ├── CLAUDE.md
│   ├── agents/
│   ├── context/
│   └── commands/
└── installation/              # Installation logic
    ├── __init__.py
    ├── conflict_detector.py   # Module 1
    ├── namespace_installer.py # Module 2
    ├── claude_md_integrator.py # Module 3
    ├── config_cli.py          # Module 4
    └── orchestrator.py        # Module 5
```

### Installed Structure

```
.claude/
├── CLAUDE.md                  # User's file (+ import)
├── agents/                    # User's agents
│   └── *.md
└── amplihack/                 # Amplihack namespace
    ├── CLAUDE.md              # Amplihack's config
    ├── agents/
    │   ├── architect.md
    │   ├── builder.md
    │   └── fixer.md
    ├── context/
    │   ├── AGENT_INPUT_VALIDATION.md
    │   ├── TRUST.md
    │   └── *.md
    └── commands/
        └── *.md
```

## Security Considerations

1. **Backup Creation**: Always backup before modifying user files
2. **Permission Validation**: Check write permissions before attempting operations
3. **Path Validation**: Prevent directory traversal attacks
4. **Atomic Operations**: Use temp files and rename for atomic writes
5. **Rollback Support**: Keep backups for rollback on error

## Performance Considerations

1. **Lazy Loading**: Don't read files until needed
2. **Batch Operations**: Copy files in bulk with shutil.copytree
3. **Cache Status**: Cache conflict detection results within single command
4. **Minimal Disk I/O**: Only read files when necessary

## Error Handling

### Error Types

1. **Permission Errors**: Clear message + suggested fix
2. **Disk Space Errors**: Report space needed + suggest cleanup
3. **Corrupted Files**: Offer reset option
4. **Concurrent Operations**: Detect and prevent conflicts
5. **Network Errors**: Graceful degradation (if downloading files)

### Error Messages

Should be:
- **Clear**: Explain what went wrong
- **Actionable**: Tell user how to fix it
- **Specific**: Don't say "error", say which operation failed

**Good Error Message**:
```
Error: Cannot write to .claude/CLAUDE.md

Permission denied. This usually means the file is owned by another user.

Try:
  sudo chown $USER .claude/CLAUDE.md

Or run with sudo:
  sudo amplihack install
```

**Bad Error Message**:
```
Error: Operation failed
```

## Open Questions

None. Design is complete and ready for implementation.

## Success Criteria

This implementation is successful when:

1. ✓ No user files are overwritten without explicit consent
2. ✓ Installation works in both install and UVX modes
3. ✓ Upgrades are safe and reversible
4. ✓ Users can manage integration manually
5. ✓ All operations create backups
6. ✓ Error messages are clear and actionable
7. ✓ Tests cover all critical paths
8. ✓ Documentation is complete

## Next Steps

1. **Review this specification** with team/stakeholders
2. **Get approval** to proceed with implementation
3. **Delegate to builder agent** with Phase 1 modules
4. **Iterate** through phases 2-4
5. **Test thoroughly** with manual checklist
6. **Deploy** and monitor for issues

---

## Appendix: Design Decisions

### Why Namespace Instead of Merge?

**Considered**: Smart merging of config files
**Rejected**: Too complex, fragile, hard to test

**Rationale**:
- Merging is complex (what if user modified our content?)
- Merge conflicts are confusing for users
- Namespace is simple: "Amplihack stays in its box"
- Import is one line, easy to understand
- Reversible without risk

### Why Import Instead of Symlink?

**Considered**: Symlink user's CLAUDE.md to ours
**Rejected**: Overwrites user file, not reversible

**Rationale**:
- Import preserves user's file
- User keeps control
- Easy to remove (delete one line)
- Works everywhere (symlinks have permission issues)

### Why Backups?

**Rationale**:
- User files are precious
- Mistakes happen
- Easy to implement
- Low cost (disk space)
- High value (peace of mind)

### Why Two-Step Install?

**Considered**: Automatic integration without prompting
**Rejected**: Violates consent principle

**Rationale**:
- User should know we're modifying their files
- Preview builds trust
- Some users may want manual control
- Explicit is better than implicit

### Why UVX Mode Differs?

**Rationale**:
- UVX is temporary (files cleaned up after)
- No point integrating if session is ephemeral
- Still need namespace for imports to work in session
- Different user expectations for temporary tools

---

**End of Specification**

This specification is complete and ready for implementation. All module contracts are defined, user flows are documented, and test requirements are clear.

The builder agent can now implement this design module by module, following the specifications in `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/`.
