# Module: ClaudeMdIntegrator

## Purpose

Add import statement to user's CLAUDE.md to integrate Amplihack configuration.

## Contract

### Inputs
- `claude_md_path: Path` - User's `.claude/CLAUDE.md` file
- `namespace_path: str = ".claude/amplihack/CLAUDE.md"` - Import target
- `dry_run: bool = False` - Preview changes without applying

### Outputs
- `IntegrationResult` - What was or would be changed

```python
@dataclass
class IntegrationResult:
    success: bool
    action_taken: str  # "added", "already_present", "created_new", "error"
    preview: str  # Show user what will change
    backup_path: Optional[Path]  # Where backup was saved
    error: Optional[str]
```

### Side Effects
- Reads existing CLAUDE.md (if exists)
- Creates backup before modification
- Writes updated CLAUDE.md with import statement
- Creates new CLAUDE.md if it doesn't exist

## Dependencies

- `pathlib.Path`
- `shutil.copy` (for backup)
- Standard library only

## Implementation Notes

### Import Statement Format
```markdown
@.claude/amplihack/CLAUDE.md
```

### Integration Logic

1. **File doesn't exist**: Create minimal CLAUDE.md with just the import
2. **File exists without import**: Add import at top, after any frontmatter
3. **File exists with import**: No-op, return "already_present"
4. **Dry run**: Return preview without writing

### File Structure
```markdown
# User's existing content here

@.claude/amplihack/CLAUDE.md

# More user content
```

Place import at the top (after frontmatter if present) so Amplihack context loads first.

### Backup Strategy
- Always backup before modifying: `.claude/CLAUDE.md.backup.{timestamp}`
- Keep last 3 backups, delete older ones
- Never delete user's original file without backup

## Key Design Decisions

- Import goes at top for precedence
- Always backup before modification
- Idempotent (can run multiple times safely)
- Preview mode for user consent
- Creates minimal file if none exists

## Edge Cases

- Empty CLAUDE.md file
- CLAUDE.md with only whitespace
- Import statement already present (different format)
- Multiple import statements
- Symlinked CLAUDE.md
- Permission errors
- Disk full during write

## Test Requirements

- Add import to existing file
- Create new file with import
- Detect existing import (exact match)
- Detect existing import (whitespace variations)
- Create backup before modification
- Preview mode (no writes)
- Handle permission errors
- Handle disk space errors
- Preserve file permissions
- Handle symlinks correctly
