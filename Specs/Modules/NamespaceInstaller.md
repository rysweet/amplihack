# Module: NamespaceInstaller

## Purpose

Install Amplihack configuration files to `.claude/amplihack/` namespace, avoiding conflicts.

## Contract

### Inputs
- `source_dir: Path` - Amplihack's bundled config files (e.g., `src/amplihack/config/`)
- `target_dir: Path` - User's `.claude/` directory
- `force: bool = False` - Overwrite existing amplihack installation if True

### Outputs
- `InstallResult` - Report of what was installed

```python
@dataclass
class InstallResult:
    success: bool
    installed_path: Path  # .claude/amplihack/
    files_installed: List[Path]
    errors: List[str]
```

### Side Effects
- Creates `.claude/amplihack/` directory
- Copies files from source to namespace
- May overwrite existing `.claude/amplihack/` if force=True

## Dependencies

- `pathlib.Path`
- `shutil.copytree`
- Standard library only

## Implementation Notes

1. Create `.claude/amplihack/` if it doesn't exist
2. If it exists and force=False, return error (upgrade scenario needs explicit consent)
3. Copy all files from source to namespace, preserving directory structure
4. Validate installation by checking key files (CLAUDE.md, agents/)

## Key Design Decisions

- Uses `shutil.copytree` for efficient directory copying
- Does NOT modify user's root `.claude/` files
- Idempotent when force=True (can re-run safely)
- Preserves file permissions and metadata

## Edge Cases

- Target directory doesn't exist (create it)
- Partial installation from previous failed attempt (clean or continue?)
- Disk space issues
- Permission errors

## Test Requirements

- Install to empty .claude/amplihack/
- Fail gracefully when amplihack/ already exists (force=False)
- Overwrite when force=True
- Preserve directory structure
- Handle permission errors
- Create parent directories as needed
