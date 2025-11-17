# Module: InstallationOrchestrator

## Purpose

Coordinate the complete installation workflow with conflict handling and user interaction.

## Contract

### Inputs
- `mode: InstallMode` - "install" or "uvx"
- `target_dir: Path` - Project root containing .claude/
- `force: bool = False` - Skip prompts, force overwrite
- `auto_integrate: bool = True` - Automatically add import to CLAUDE.md

```python
class InstallMode(Enum):
    INSTALL = "install"  # Persistent installation
    UVX = "uvx"          # Ephemeral installation
```

### Outputs
- `OrchestrationResult` - Complete report of installation

```python
@dataclass
class OrchestrationResult:
    success: bool
    mode: InstallMode
    conflicts_detected: bool
    conflicts_resolved: bool
    installation_result: InstallResult
    integration_result: Optional[IntegrationResult]
    user_actions_required: List[str]
    errors: List[str]
```

### Side Effects
- Detects conflicts (reads filesystem)
- Installs files to namespace
- May prompt user for decisions
- May modify CLAUDE.md
- Creates backups

## Dependencies

- `ConfigConflictDetector`
- `NamespaceInstaller`
- `ClaudeMdIntegrator`
- `rich.prompt` for user interaction (optional)

## Implementation Notes

### Installation Flow

```
┌─────────────────────────────────────┐
│ 1. Detect Conflicts                 │
│    - Check existing files           │
│    - Identify upgrade scenario      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Namespace Installation           │
│    - Install to .claude/amplihack/  │
│    - Handle upgrade if needed       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Integration Decision             │
│    - Skip if UVX mode               │
│    - Prompt user in install mode    │
│    - Auto-integrate if force=True   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Apply Integration                │
│    - Preview changes                │
│    - Create backup                  │
│    - Add import statement           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. Report Results                   │
│    - Summarize what happened        │
│    - List any manual actions needed │
└─────────────────────────────────────┘
```

### Mode-Specific Behavior

#### Install Mode (Persistent)
- Install files to namespace
- Offer to integrate with CLAUDE.md
- Show post-install instructions
- Create all necessary directories

#### UVX Mode (Ephemeral)
- Install files to namespace (needed for imports)
- Skip CLAUDE.md integration (temporary session)
- Assume files will be cleaned up
- Show different post-install message

### User Prompts

#### Upgrade Scenario
```
Amplihack is already installed at .claude/amplihack/

This will upgrade your installation to version 0.2.0.
Your existing configuration will be backed up.

Continue? [Y/n]:
```

#### Integration Offer
```
Amplihack has been installed to .claude/amplihack/

To activate it, we can add an import to your .claude/CLAUDE.md:

  @.claude/amplihack/CLAUDE.md

This allows Claude to use Amplihack's agents and tools.

Add import to CLAUDE.md? [Y/n]:
```

#### Conflict Resolution
```
The following conflicts were detected:

  - .claude/agents/architect.md (user file exists)
  - .claude/agents/builder.md (user file exists)

Installing to .claude/amplihack/ will avoid these conflicts.
Your existing agents will not be modified.

Continue with namespaced installation? [Y/n]:
```

### Post-Install Messages

#### Success (Install Mode, Integrated)
```
✓ Amplihack installed successfully!

  Installation: .claude/amplihack/
  Integration: Added to .claude/CLAUDE.md
  Backup: .claude/CLAUDE.md.backup.20250110_143022

Ready to use! Try:
  - @architect to start the architect agent
  - /amplihack:knowledge-builder to build knowledge base
  - amplihack config show to see configuration
```

#### Success (Install Mode, Not Integrated)
```
✓ Amplihack installed successfully!

  Installation: .claude/amplihack/

To activate, add this line to your .claude/CLAUDE.md:
  @.claude/amplihack/CLAUDE.md

Or run:
  amplihack config integrate
```

#### Success (UVX Mode)
```
✓ Amplihack ready for this session!

  Installation: .claude/amplihack/ (temporary)

Note: In UVX mode, changes won't persist between sessions.
For persistent installation, use: pip install amplihack
```

## Key Design Decisions

1. **Namespace Always**: Even in clean install, use namespace for consistency
2. **Separate Integration**: Installing files ≠ integrating config (two steps)
3. **Explicit Consent**: Never modify user files without permission (except force mode)
4. **Graceful Degradation**: Work without rich library, fall back to basic prompts
5. **Idempotent**: Safe to run multiple times

## Error Scenarios

1. **Permission Denied**: Clear message with sudo suggestion
2. **Disk Full**: Report error, suggest cleanup
3. **Corrupted Install**: Offer reset option
4. **Git Conflicts**: Detect and warn about uncommitted changes

## Edge Cases

- .claude/ doesn't exist (create it)
- Partial previous installation
- Import statement malformed in CLAUDE.md
- Multiple Amplihack versions installed
- User cancels mid-installation
- Network errors (if downloading files)

## Test Requirements

- Install to clean project
- Upgrade existing installation
- Handle conflicts gracefully
- Respect force flag
- Work in both install and UVX modes
- Prompt for user decisions
- Skip prompts in CI environments
- Create proper backups
- Handle all error scenarios
- Rollback on failure
