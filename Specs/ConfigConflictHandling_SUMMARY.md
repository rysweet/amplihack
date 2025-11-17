# Config Conflict Handling - Design Summary

**Issue**: #1279
**Status**: Design Complete - Ready for Implementation
**Architect**: Claude (Architect Agent)
**Date**: 2025-01-10

## The Problem

Amplihack's installation process currently may overwrite user's existing `.claude/` configuration files without consent. This destroys user work and prevents custom configuration.

## The Solution

**Namespaced Installation + Import-Based Integration**

Install all Amplihack files to `.claude/amplihack/` subdirectory and add a single import line to user's `CLAUDE.md`:

```markdown
@.claude/amplihack/CLAUDE.md
```

This gives users full control while maintaining simple UX.

## Key Benefits

1. **Zero Risk**: User files never overwritten without explicit consent
2. **User Control**: Clear separation between user and Amplihack config
3. **Easy Upgrades**: Amplihack can update its namespace without touching user files
4. **Reversible**: Remove one line to disable, delete directory to uninstall
5. **Simple Mental Model**: "Amplihack stays in its box"

## Architecture

Five composable modules implement the system:

```
1. ConfigConflictDetector   (detects existing files)
2. NamespaceInstaller       (copies to .claude/amplihack/)
3. ClaudeMdIntegrator       (adds/removes import line)
4. InstallationOrchestrator (coordinates workflow)
5. ConfigCLI                (user-facing commands)
```

Each module is specified in detail with clear contracts, test requirements, and implementation notes.

## File Structure

```
.claude/
├── CLAUDE.md              ← User's file (we add one line)
├── agents/                ← User's agents (untouched)
└── amplihack/             ← Amplihack namespace (we own this)
    ├── CLAUDE.md
    ├── agents/
    ├── context/
    └── commands/
```

## User Experience

### Fresh Install
```bash
$ amplihack install

✓ Amplihack installed successfully!
  Installation: .claude/amplihack/
  Integration: Created .claude/CLAUDE.md with import
```

### Install with Existing Config
```bash
$ amplihack install

Amplihack has been installed to .claude/amplihack/

To activate it, we can add an import to your .claude/CLAUDE.md:
  @.claude/amplihack/CLAUDE.md

Add import to CLAUDE.md? [Y/n]: y

✓ Amplihack installed and integrated!
  Backup: .claude/CLAUDE.md.backup.20250110_143022
```

### Manual Control
```bash
$ amplihack config show      # Check status
$ amplihack config integrate # Add integration
$ amplihack config remove    # Remove integration
$ amplihack config reset     # Reset to fresh state
```

## Implementation Plan

### Phase 1: Core Modules (2-3 hours)
Implement foundation modules with tests:
- ConfigConflictDetector
- NamespaceInstaller
- ClaudeMdIntegrator

### Phase 2: Orchestration (2-3 hours)
Coordinate workflow:
- InstallationOrchestrator
- Update existing install command

### Phase 3: CLI Commands (2-3 hours)
User-facing commands:
- Config CLI with all subcommands
- Help text and documentation

### Phase 4: Polish (1-2 hours)
- Integration tests
- Manual testing
- Documentation updates

**Total Estimate**: 8-11 hours for complete implementation

## Documentation Files

All specifications are complete and ready for implementation:

1. **Master Specification**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/ConfigConflictHandling.md`
   - Complete problem analysis
   - Solution architecture
   - User flows
   - Implementation plan
   - Testing strategy

2. **Implementation Guide**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/ConfigConflictHandling_ImplementationGuide.md`
   - Quick reference
   - Code snippets
   - Common pitfalls
   - Integration points
   - Checklist

3. **Architecture Diagrams**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/ConfigConflictHandling_Architecture.md`
   - Visual system overview
   - Data flow diagrams
   - State transitions
   - Error handling flows

4. **Module Specifications** (in `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/`):
   - ConfigConflictDetector.md
   - NamespaceInstaller.md
   - ClaudeMdIntegrator.md
   - InstallationOrchestrator.md
   - ConfigCLI.md

Each module spec includes:
- Purpose and responsibility
- Input/output contracts
- Side effects
- Dependencies
- Implementation notes
- Edge cases
- Test requirements

## Key Design Decisions

1. **Namespace Always**: Even in clean install, use namespace for consistency
2. **Import Over Merge**: Simple import line instead of complex file merging
3. **Explicit Consent**: Never modify user files without permission
4. **Backups Required**: Always backup before modifications
5. **Idempotent Operations**: Safe to run multiple times
6. **Mode-Aware**: Different behavior for install vs UVX modes

## Success Criteria

Implementation succeeds when:
- No user files overwritten without consent
- Installation works in both install and UVX modes
- Upgrades are safe and reversible
- Users can manage integration manually
- All operations create backups
- Error messages are clear
- Tests cover all critical paths

## Next Steps

1. Review this design with stakeholders
2. Get approval to proceed
3. Delegate to builder agent for Phase 1 implementation
4. Iterate through remaining phases
5. Test thoroughly
6. Deploy and monitor

## Questions?

The design is complete and all questions are answered in the specifications. If new questions arise during implementation:

1. Check the module specification first
2. Apply the decision framework (simplest solution)
3. Consult the architect if needed
4. Document the decision

---

**Ready for Implementation**: All specifications are complete, tested designs are provided, and the builder agent can begin implementation immediately.

The architecture follows the brick philosophy: simple, composable, regeneratable modules with clear contracts and responsibilities.
