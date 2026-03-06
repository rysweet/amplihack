# Staging API Reference

Developer reference for the unified .claude/ staging mechanism.

## Overview

All amplihack commands (except `claude`) call `_ensure_amplihack_staged()` before launching their respective tools. This ensures `~/.amplihack/.claude/` is populated with agents, skills, tools, and framework files.

## Core Functions

### `_ensure_amplihack_staged()`

Ensures amplihack framework files are staged to `~/.amplihack/.claude/`.

**Signature:**

```python
def _ensure_amplihack_staged() -> None:
    """Ensure amplihack is staged to ~/.amplihack/.claude/ (UVX mode only)."""
```

**Behavior:**

1. Detects deployment mode via `deployment.get_deployment_mode()`
2. Returns immediately if not in UVX mode (development uses source files)
3. Creates `~/.amplihack/.claude/` if missing
4. Calls `copytree_manifest()` to copy framework files
5. Handles errors gracefully with user-friendly messages

**Called by:**

- `cmd_copilot()` - Before launching GitHub Copilot CLI
- `cmd_amplifier()` - Before launching Microsoft Amplifier
- `cmd_rustyclawd()` - Before launching Rustyclawd
- `cmd_codex()` - Before launching Codex

**NOT called by:**

- `cmd_claude()` - Uses different staging mechanism for plugin support

**Example:**

```python
def cmd_copilot(args):
    """Launch GitHub Copilot CLI with amplihack."""
    # Ensure staging before launching
    _ensure_amplihack_staged()

    # Launch tool with full framework access
    launch_copilot_with_hooks()
```

### `copytree_manifest()`

Copies files from source to destination based on manifest specification.

**Signature:**

```python
def copytree_manifest(
    source: Path,
    dest: Path,
    manifest: Dict[str, List[str]],
    overwrite: bool = True
) -> None:
    """Copy directory tree using manifest to filter files."""
```

**Parameters:**

- `source`: Source directory (package's `.claude/` directory)
- `dest`: Destination directory (`~/.amplihack/.claude/`)
- `manifest`: Dictionary mapping subdirectories to glob patterns
- `overwrite`: Whether to replace existing files (default: True)

**Manifest Format:**

```python
STAGING_MANIFEST = {
    "agents": ["**/*.md"],              # All agent markdown files
    "skills": ["**/*.md", "**/*.py"],   # Skill docs and Python files
    "commands": ["**/*.py", "**/*.sh"], # Command scripts
    "tools": ["**/*.py"],               # Tool utilities
    "hooks": ["**/*.py", "**/*.sh"],    # Hook scripts
    "context": ["**/*.md"],             # Context documentation
    "workflow": ["**/*.md"],            # Workflow definitions
}
```

**Example:**

```python
from pathlib import Path
from amplihack.deployment import copytree_manifest

source = Path(__file__).parent / ".claude"
dest = Path.home() / ".amplihack" / ".claude"

copytree_manifest(
    source=source,
    dest=dest,
    manifest=STAGING_MANIFEST,
    overwrite=True
)
```

### `get_deployment_mode()`

Detects current deployment mode (development vs UVX).

**Signature:**

```python
def get_deployment_mode() -> str:
    """Detect deployment mode: 'development' or 'uvx'."""
```

**Returns:**

- `"development"`: Running from source (editable install, git clone)
- `"uvx"`: Running from UVX isolated environment

**Detection Logic:**

```python
def get_deployment_mode() -> str:
    # Check for .git directory (development)
    if (Path(__file__).parent.parent / ".git").exists():
        return "development"

    # Check for UVX environment markers
    if "/.local/share/uv/" in str(Path(__file__)):
        return "uvx"

    return "uvx"  # Default to UVX if uncertain
```

**Example:**

```python
from amplihack.deployment import get_deployment_mode

mode = get_deployment_mode()
if mode == "uvx":
    print("Running in UVX deployment mode")
    _ensure_amplihack_staged()
else:
    print("Running in development mode - using source files")
```

## Constants

### `STAGING_MANIFEST`

Defines which files to copy during staging.

```python
STAGING_MANIFEST: Dict[str, List[str]] = {
    "agents": ["**/*.md"],
    "skills": ["**/*.md", "**/*.py"],
    "commands": ["**/*.py", "**/*.sh"],
    "tools": ["**/*.py"],
    "hooks": ["**/*.py", "**/*.sh"],
    "context": ["**/*.md"],
    "workflow": ["**/*.md"],
}
```

### `STAGING_TARGET`

Target directory for staged files.

```python
STAGING_TARGET: Path = Path.home() / ".amplihack" / ".claude"
```

## Error Handling

### Permission Errors

```python
try:
    _ensure_amplihack_staged()
except PermissionError as e:
    print(f"Error: Cannot write to ~/.amplihack/.claude/")
    print(f"Details: {e}")
    print("Fix: chmod -R u+w ~/.amplihack/")
    sys.exit(1)
```

### Missing Source Files

```python
try:
    copytree_manifest(source, dest, STAGING_MANIFEST)
except FileNotFoundError as e:
    print(f"Error: Cannot find source files to stage")
    print(f"Details: {e}")
    print("This indicates a corrupted package installation")
    sys.exit(1)
```

## Testing

### Verify Staging in Tests

```python
import pytest
from pathlib import Path
from amplihack.cli import _ensure_amplihack_staged

def test_staging_creates_directory(tmp_path, monkeypatch):
    """Test that staging creates target directory."""
    monkeypatch.setenv("HOME", str(tmp_path))

    _ensure_amplihack_staged()

    staged_dir = tmp_path / ".amplihack" / ".claude"
    assert staged_dir.exists()
    assert (staged_dir / "agents").exists()
    assert (staged_dir / "skills").exists()

def test_staging_skipped_in_dev_mode(monkeypatch):
    """Test that staging is skipped in development mode."""
    monkeypatch.setattr(
        "amplihack.deployment.get_deployment_mode",
        lambda: "development"
    )

    # Should return without staging
    _ensure_amplihack_staged()
    # No staging directory created
```

### Manual Testing

```bash
# Test staging from package
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot --help

# Verify staging occurred
ls -la ~/.amplihack/.claude/

# Test re-staging (should be fast)
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot --help

# Test with clean slate
rm -rf ~/.amplihack/.claude/
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot --help
```

## Troubleshooting

### Staging Not Happening

**Symptom**: Agents/skills not available after running command.

**Check deployment mode:**

```python
from amplihack.deployment import get_deployment_mode
print(get_deployment_mode())
# Should print: "uvx"
```

**Check staging call:**

```bash
# Add debug output to _ensure_amplihack_staged()
# Should see: "Staging amplihack to ~/.amplihack/.claude/..."
```

### Stale Files After Update

**Symptom**: Old behavior persists after package upgrade.

**Force re-staging:**

```bash
# Remove staged files
rm -rf ~/.amplihack/.claude/

# Re-run command
uvx --from git+https://github.com/rysweet/amplihack@main amplihack copilot
```

### Partial Staging

**Symptom**: Some files staged but not others.

**Check manifest:**

```python
from amplihack.cli import STAGING_MANIFEST
print(STAGING_MANIFEST)
# Verify expected patterns are present
```

**Check source files:**

```bash
# Find package location
python -c "import amplihack; print(amplihack.__file__)"

# Check source .claude/ directory
ls -la /path/to/package/.claude/
```

## Related

- [Verify Staging](../howto/verify-claude-staging.md) - User guide
- [Unified Staging Architecture](../concepts/unified-staging-architecture.md) - Design rationale
- [UVX Deployment](../UVX_DEPLOYMENT_SOLUTIONS.md) - Deployment patterns
