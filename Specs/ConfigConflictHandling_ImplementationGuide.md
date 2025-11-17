# Implementation Guide: Config Conflict Handling

Quick reference for implementing the config conflict handling system.

## Overview

This guide provides the essential information needed to implement the configuration conflict handling system designed in `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/ConfigConflictHandling.md`.

## Implementation Order

Implement modules in this exact order (dependencies flow downward):

```
1. ConfigConflictDetector    (no dependencies)
2. NamespaceInstaller        (no dependencies)
3. ClaudeMdIntegrator        (no dependencies)
4. InstallationOrchestrator  (uses 1, 2, 3)
5. ConfigCLI                 (uses 1, 2, 3)
```

## Module Quick Reference

### 1. ConfigConflictDetector

**File**: `src/amplihack/installation/conflict_detector.py`

**Key Classes**:
```python
@dataclass
class ConflictReport:
    has_conflicts: bool
    existing_claude_md: bool
    existing_agents: List[str]
    would_overwrite: List[Path]
    safe_to_namespace: bool

def detect_conflicts(target_dir: Path, manifest: List[str]) -> ConflictReport:
    """Detect config conflicts in target directory."""
    pass
```

**Tests**: `tests/installation/test_conflict_detector.py`
- test_detect_no_conflicts_empty_dir
- test_detect_existing_claude_md
- test_detect_conflicting_agents
- test_detect_upgrade_scenario

**Spec**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/ConfigConflictDetector.md`

---

### 2. NamespaceInstaller

**File**: `src/amplihack/installation/namespace_installer.py`

**Key Classes**:
```python
@dataclass
class InstallResult:
    success: bool
    installed_path: Path
    files_installed: List[Path]
    errors: List[str]

def install_to_namespace(
    source_dir: Path,
    target_dir: Path,
    force: bool = False
) -> InstallResult:
    """Install files to .claude/amplihack/ namespace."""
    pass
```

**Tests**: `tests/installation/test_namespace_installer.py`
- test_install_to_empty_namespace
- test_install_fails_without_force
- test_install_with_force_overwrites

**Spec**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/NamespaceInstaller.md`

---

### 3. ClaudeMdIntegrator

**File**: `src/amplihack/installation/claude_md_integrator.py`

**Key Classes**:
```python
@dataclass
class IntegrationResult:
    success: bool
    action_taken: str  # "added", "already_present", "created_new", "error"
    preview: str
    backup_path: Optional[Path]
    error: Optional[str]

def integrate_import(
    claude_md_path: Path,
    namespace_path: str = ".claude/amplihack/CLAUDE.md",
    dry_run: bool = False
) -> IntegrationResult:
    """Add import statement to CLAUDE.md."""
    pass

def remove_import(
    claude_md_path: Path,
    namespace_path: str = ".claude/amplihack/CLAUDE.md"
) -> IntegrationResult:
    """Remove import statement from CLAUDE.md."""
    pass
```

**Tests**: `tests/installation/test_claude_md_integrator.py`
- test_add_import_to_existing_file
- test_create_new_file_with_import
- test_detect_existing_import
- test_remove_import
- test_backup_creation

**Spec**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/ClaudeMdIntegrator.md`

---

### 4. InstallationOrchestrator

**File**: `src/amplihack/installation/orchestrator.py`

**Key Classes**:
```python
from enum import Enum

class InstallMode(Enum):
    INSTALL = "install"
    UVX = "uvx"

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

def orchestrate_installation(
    mode: InstallMode,
    target_dir: Path,
    force: bool = False,
    auto_integrate: bool = True
) -> OrchestrationResult:
    """Coordinate complete installation workflow."""
    pass
```

**Tests**: `tests/installation/test_orchestrator.py`
- test_fresh_install_flow
- test_upgrade_flow
- test_conflict_resolution_flow
- test_uvx_mode_flow

**Spec**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/InstallationOrchestrator.md`

---

### 5. ConfigCLI

**File**: `src/amplihack/installation/config_cli.py`

**Commands**:
```python
import click

@click.group()
def config():
    """Manage Amplihack configuration."""
    pass

@config.command()
def show():
    """Display configuration status."""
    pass

@config.command()
@click.option('--force', is_flag=True)
@click.option('--dry-run', is_flag=True)
def integrate(force: bool, dry_run: bool):
    """Add Amplihack import to CLAUDE.md."""
    pass

@config.command()
@click.option('--keep-files', is_flag=True)
def remove(keep_files: bool):
    """Remove Amplihack integration."""
    pass

@config.command()
@click.option('--force', is_flag=True, required=True)
def reset(force: bool):
    """Reset Amplihack configuration."""
    pass
```

**Tests**: `tests/installation/test_config_cli.py`
- test_show_command
- test_integrate_prompts_user
- test_remove_prompts_user
- test_reset_requires_force

**Spec**: `/Users/ryan/src/amplihack/MicrosoftHackathon2025-AgenticCoding/Specs/Modules/ConfigCLI.md`

---

## Critical Implementation Details

### Backup File Naming

```python
from datetime import datetime

def create_backup_path(original: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return original.with_suffix(f"{original.suffix}.backup.{timestamp}")
```

### Import Statement Format

Exact format (no variations):
```markdown
@.claude/amplihack/CLAUDE.md
```

### Import Detection Regex

```python
import re

IMPORT_PATTERN = re.compile(
    r'^\s*@\.claude/amplihack/CLAUDE\.md\s*$',
    re.MULTILINE
)

def has_import(content: str) -> bool:
    return bool(IMPORT_PATTERN.search(content))
```

### Atomic File Writing

Always use temp file + rename for atomic writes:

```python
import tempfile
import shutil

def atomic_write(path: Path, content: str):
    """Write file atomically using temp file + rename."""
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=path.parent,
        delete=False,
        encoding='utf-8'
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Atomic rename
    shutil.move(str(tmp_path), str(path))
```

### User Confirmation Pattern

```python
def prompt_user(message: str, default: bool = True) -> bool:
    """Prompt user for yes/no confirmation."""
    try:
        from rich.prompt import Confirm
        return Confirm.ask(message, default=default)
    except ImportError:
        # Fallback without rich
        choice = "Y/n" if default else "y/N"
        response = input(f"{message} [{choice}]: ").strip().lower()

        if not response:
            return default
        return response in ['y', 'yes']
```

### Error Handling Pattern

```python
class ConfigError(Exception):
    """Base exception for config operations."""
    pass

class PermissionError(ConfigError):
    """Permission denied error with helpful message."""
    def __init__(self, path: Path):
        super().__init__(
            f"Cannot write to {path}\n\n"
            f"Permission denied. Try:\n"
            f"  sudo chown $USER {path}\n"
            f"Or run with sudo:\n"
            f"  sudo amplihack install"
        )
```

## Testing Strategy

### Unit Test Structure

```python
import pytest
from pathlib import Path
from amplihack.installation.conflict_detector import detect_conflicts

@pytest.fixture
def temp_claude_dir(tmp_path):
    """Create temporary .claude directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir

def test_detect_no_conflicts_empty_dir(temp_claude_dir):
    """Test conflict detection in empty directory."""
    manifest = ["CLAUDE.md", "agents/architect.md"]

    result = detect_conflicts(temp_claude_dir, manifest)

    assert not result.has_conflicts
    assert not result.existing_claude_md
    assert result.safe_to_namespace
```

### Integration Test Structure

```python
def test_full_installation_flow(tmp_path):
    """Test complete installation flow from start to finish."""
    # Setup
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"

    # Execute
    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=project_dir,
        force=True,
        auto_integrate=True
    )

    # Verify
    assert result.success
    assert (claude_dir / "amplihack" / "CLAUDE.md").exists()
    assert (claude_dir / "CLAUDE.md").exists()

    # Check import was added
    content = (claude_dir / "CLAUDE.md").read_text()
    assert "@.claude/amplihack/CLAUDE.md" in content
```

## Common Pitfalls

### 1. Path Handling

**WRONG**:
```python
# Assumes current directory
path = Path(".claude/CLAUDE.md")
```

**RIGHT**:
```python
# Always use absolute paths
path = target_dir / ".claude" / "CLAUDE.md"
path = path.resolve()
```

### 2. File Reading Encoding

**WRONG**:
```python
content = path.read_text()  # Uses system default encoding
```

**RIGHT**:
```python
content = path.read_text(encoding='utf-8')
```

### 3. Permission Checking

**WRONG**:
```python
# Try to write and hope it works
path.write_text(content)
```

**RIGHT**:
```python
# Check first
if not os.access(path.parent, os.W_OK):
    raise PermissionError(path)
path.write_text(content)
```

### 4. Import Statement Placement

**WRONG**:
```python
# Just append to end
content = existing + "\n@.claude/amplihack/CLAUDE.md\n"
```

**RIGHT**:
```python
# Add at top (after frontmatter if present)
lines = content.split('\n')
# Find insertion point (after frontmatter)
insert_at = find_import_insertion_point(lines)
lines.insert(insert_at, "@.claude/amplihack/CLAUDE.md")
content = '\n'.join(lines)
```

### 5. Backup Management

**WRONG**:
```python
# Single backup, no rotation
backup = path.with_suffix('.backup')
shutil.copy(path, backup)
```

**RIGHT**:
```python
# Timestamped backups with rotation
backup = create_backup_path(path)
shutil.copy(path, backup)
rotate_backups(path, keep_last=3)
```

## Integration with Existing Code

### Current Installation Entry Point

The existing `amplihack install` command should be modified to use the orchestrator:

**File**: `src/amplihack/cli.py` (or wherever install command is)

```python
@cli.command()
@click.option('--force', is_flag=True, help='Skip confirmations')
def install(force: bool):
    """Install Amplihack to current project."""
    from .installation.orchestrator import (
        orchestrate_installation,
        InstallMode
    )

    project_dir = Path.cwd()

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=project_dir,
        force=force,
        auto_integrate=not force  # Prompt unless force
    )

    if result.success:
        click.echo(f"✓ Amplihack installed successfully!")
        if result.integration_result:
            click.echo(f"  Integration: {result.integration_result.action_taken}")
    else:
        click.echo(f"✗ Installation failed")
        for error in result.errors:
            click.echo(f"  {error}")
        sys.exit(1)
```

### UVX Mode Detection

If UVX mode needs to be detected automatically:

```python
def detect_install_mode() -> InstallMode:
    """Detect if running in UVX mode."""
    # Check for UVX environment variable
    if os.environ.get('UVX_ACTIVE'):
        return InstallMode.UVX

    # Check if installed in temporary directory
    if '/tmp/' in sys.prefix or '/var/folders/' in sys.prefix:
        return InstallMode.UVX

    return InstallMode.INSTALL
```

## Checklist for Implementation

### Phase 1: Core Modules
- [ ] Create `src/amplihack/installation/__init__.py`
- [ ] Implement `conflict_detector.py` with tests
- [ ] Implement `namespace_installer.py` with tests
- [ ] Implement `claude_md_integrator.py` with tests
- [ ] All unit tests pass
- [ ] Code review by architect

### Phase 2: Orchestration
- [ ] Implement `orchestrator.py` with tests
- [ ] Update existing install command to use orchestrator
- [ ] Test install mode flow
- [ ] Test UVX mode flow
- [ ] Test upgrade scenario
- [ ] Code review by architect

### Phase 3: CLI Commands
- [ ] Implement `config_cli.py` with tests
- [ ] Register config commands in main CLI
- [ ] Test all config subcommands
- [ ] Verify help text
- [ ] Code review by architect

### Phase 4: Polish
- [ ] Integration tests for complete flows
- [ ] Manual testing checklist completed
- [ ] Error messages reviewed for clarity
- [ ] Documentation updated
- [ ] Ready for release

## Questions During Implementation

If you encounter questions or uncertainties:

1. **Check the module specification** first
2. **Apply the decision framework**:
   - Do we actually need this?
   - What's the simplest solution?
   - Can this be more modular?
3. **Consult the architect** (create issue or discussion)
4. **Document the decision** in code comments

## Success Metrics

Implementation is successful when:

- All tests pass (unit + integration)
- Manual testing checklist completed
- No user files overwritten without consent
- All error cases handled gracefully
- Documentation is clear
- Code follows module specifications

---

This guide provides the essential information for implementation. For complete details, refer to the full specification and individual module specs.
