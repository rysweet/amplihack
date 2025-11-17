# Module: ConfigConflictDetector

## Purpose

Detect existing configuration files that may conflict with Amplihack installation.

## Contract

### Inputs
- `target_dir: Path` - The .claude directory to check
- `manifest: List[str]` - Files that Amplihack wants to install

### Outputs
- `ConflictReport` - Structured report of conflicts

```python
@dataclass
class ConflictReport:
    has_conflicts: bool
    existing_claude_md: bool
    existing_agents: List[str]  # Names of custom agents
    would_overwrite: List[Path]  # Files that would be overwritten
    safe_to_namespace: bool  # True if namespacing solves all conflicts
```

### Side Effects
- Reads filesystem only (no writes)

## Dependencies

- `pathlib.Path`
- Standard library only

## Implementation Notes

1. Check if `.claude/CLAUDE.md` exists
2. Check for files in `.claude/agents/` that match Amplihack agent names
3. Calculate what would be overwritten if installed to root vs namespace
4. A conflict is "safe to namespace" if installing to `.claude/amplihack/` avoids all overwrites

## Edge Cases

- Empty `.claude/` directory (no conflict)
- User has `.claude/amplihack/` already (upgrade scenario)
- Symlinked `.claude/` directory
- Permission issues reading directory

## Test Requirements

- Detect existing CLAUDE.md
- Detect conflicting agent names
- Identify upgrade scenario (amplihack dir already exists)
- Handle missing .claude directory
- Handle permission errors gracefully
