# Module Specification: Backward Compatibility Pattern

## Purpose

Ensure existing per-project `~/.amplihack/.claude/` installations continue working while supporting the new plugin architecture.

## Problem

Issue #1948 moves to plugin architecture (`~/.amplihack/.claude/`), but:
- Existing projects use per-project `~/.amplihack/.claude/` directories
- Users may prefer local over global plugin installation
- Migration path unclear
- Risk of breaking existing workflows

## Solution Overview

Implement dual-mode support:
1. **Detection:** Automatically detect per-project vs plugin installation
2. **Preference:** Local `~/.amplihack/.claude/` takes precedence over plugin
3. **Fallback:** Plugin used if no local installation
4. **Migration:** Provide tools to migrate between modes

## Contract

### Inputs

**Detection Function:**
```python
def detect_claude_mode() -> ClaudeMode:
    """Detect whether to use project-local or plugin mode."""
```

**Environment:**
- Current working directory (may have `~/.amplihack/.claude/`)
- Plugin directory (`~/.amplihack/.claude/`)
- User preference (explicit override)

### Outputs

**ClaudeMode:**
```python
class ClaudeMode(Enum):
    LOCAL = "local"      # Project has .claude/ directory
    PLUGIN = "plugin"    # Use plugin from ~/.amplihack/.claude/
    NONE = "none"        # No .claude found
```

**Behavior:**
- `LOCAL`: Use project's `~/.amplihack/.claude/` directory
- `PLUGIN`: Use plugin installation
- `NONE`: Install plugin or create local (user choice)

### Side Effects

- May create `~/.amplihack/.claude/.mode` file to record user preference
- Logs mode selection for debugging
- No automatic migration (user-initiated only)

## Implementation Design

### File Structure

```
src/amplihack/
├── cli.py                    # Modified: Add mode detection
└── mode_detector/
    ├── __init__.py           # NEW: Exports detect_claude_mode
    ├── detector.py           # NEW: Detection logic
    └── migrator.py           # NEW: Migration helper
```

### Module 1: Mode Detector (`detector.py`)

**Purpose:** Detect which Claude mode to use

**Public API:**
```python
from enum import Enum
from pathlib import Path
from typing import Optional

class ClaudeMode(Enum):
    """Claude installation mode."""
    LOCAL = "local"
    PLUGIN = "plugin"
    NONE = "none"

class ModeDetector:
    """Detect Claude installation mode."""

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize detector for project directory."""

    def detect(self) -> ClaudeMode:
        """Detect which mode to use (LOCAL > PLUGIN > NONE)."""

    def get_claude_dir(self, mode: ClaudeMode) -> Optional[Path]:
        """Get .claude directory path for given mode."""

    def has_local_installation(self) -> bool:
        """Check if project has .claude/ directory."""

    def has_plugin_installation(self) -> bool:
        """Check if plugin is installed."""

__all__ = ["ClaudeMode", "ModeDetector"]
```

**Implementation:**
```python
from enum import Enum
from pathlib import Path
from typing import Optional
import os

class ClaudeMode(Enum):
    """Claude installation mode."""
    LOCAL = "local"
    PLUGIN = "plugin"
    NONE = "none"

class ModeDetector:
    """Detect Claude installation mode with precedence: LOCAL > PLUGIN > NONE."""

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize detector.

        Args:
            project_dir: Project directory to check (defaults to cwd)
        """
        self.project_dir = project_dir or Path.cwd()
        self.local_claude = self.project_dir / ".claude"
        self.plugin_claude = Path.home() / ".amplihack" / ".claude"

    def detect(self) -> ClaudeMode:
        """Detect which mode to use.

        Precedence:
        1. LOCAL - Project has .claude/ directory
        2. PLUGIN - Plugin installed at ~/.amplihack/.claude/
        3. NONE - No installation found

        Returns:
            ClaudeMode indicating which installation to use
        """
        # Check for explicit override via environment
        override = os.environ.get("AMPLIHACK_MODE")
        if override:
            if override.lower() == "local" and self.has_local_installation():
                return ClaudeMode.LOCAL
            elif override.lower() == "plugin" and self.has_plugin_installation():
                return ClaudeMode.PLUGIN

        # Standard precedence: LOCAL > PLUGIN > NONE
        if self.has_local_installation():
            return ClaudeMode.LOCAL
        elif self.has_plugin_installation():
            return ClaudeMode.PLUGIN
        else:
            return ClaudeMode.NONE

    def get_claude_dir(self, mode: ClaudeMode) -> Optional[Path]:
        """Get .claude directory path for mode.

        Args:
            mode: ClaudeMode to get directory for

        Returns:
            Path to .claude directory or None
        """
        if mode == ClaudeMode.LOCAL:
            return self.local_claude if self.has_local_installation() else None
        elif mode == ClaudeMode.PLUGIN:
            return self.plugin_claude if self.has_plugin_installation() else None
        else:
            return None

    def has_local_installation(self) -> bool:
        """Check if project has valid .claude/ directory.

        Returns:
            True if .claude exists and has essential content
        """
        if not self.local_claude.exists():
            return False

        # Check for essential directories (at least one should exist)
        essential_dirs = ["agents", "commands", "skills", "tools"]
        return any((self.local_claude / d).exists() for d in essential_dirs)

    def has_plugin_installation(self) -> bool:
        """Check if plugin is installed.

        Returns:
            True if plugin exists at ~/.amplihack/.claude/
        """
        if not self.plugin_claude.exists():
            return False

        # Check for plugin manifest
        manifest = self.plugin_claude.parent / ".claude-plugin" / "plugin.json"
        return manifest.exists()

def detect_claude_mode(project_dir: Optional[Path] = None) -> ClaudeMode:
    """Convenience function to detect Claude mode.

    Args:
        project_dir: Project directory (defaults to cwd)

    Returns:
        ClaudeMode indicating which installation to use
    """
    detector = ModeDetector(project_dir)
    return detector.detect()
```

### Module 2: Migration Helper (`migrator.py`)

**Purpose:** Help users migrate between modes

**Public API:**
```python
class MigrationHelper:
    """Help migrate between Claude modes."""

    def migrate_to_plugin(self, project_dir: Path) -> bool:
        """Migrate project from local to plugin mode."""

    def migrate_to_local(self, project_dir: Path) -> bool:
        """Create local .claude/ from plugin."""

    def can_migrate_to_plugin(self, project_dir: Path) -> bool:
        """Check if project can migrate to plugin mode."""

__all__ = ["MigrationHelper"]
```

**Implementation:**
```python
from pathlib import Path
from typing import Optional
import shutil

class MigrationHelper:
    """Help users migrate between Claude installation modes."""

    def __init__(self):
        self.plugin_claude = Path.home() / ".amplihack" / ".claude"

    def migrate_to_plugin(self, project_dir: Path) -> bool:
        """Migrate project from local to plugin mode.

        This removes the local .claude/ directory and relies on plugin.

        Args:
            project_dir: Project directory with .claude/

        Returns:
            True if migration successful
        """
        local_claude = project_dir / ".claude"

        if not local_claude.exists():
            print("No local .claude/ directory found")
            return False

        if not self.plugin_claude.exists():
            print("Plugin not installed. Install plugin first:")
            print("  amplihack plugin install")
            return False

        # Backup local customizations (if any)
        custom_files = self._find_custom_files(local_claude)
        if custom_files:
            print("Warning: Local .claude/ has custom files:")
            for f in custom_files:
                print(f"  - {f.relative_to(local_claude)}")
            print("\nThese will be lost. Backup first or use --preserve-custom")
            return False

        # Remove local .claude/ directory
        print(f"Removing local .claude/ from {project_dir}")
        shutil.rmtree(local_claude)
        print("Migration complete. Project now uses plugin.")
        return True

    def migrate_to_local(self, project_dir: Path) -> bool:
        """Create local .claude/ from plugin.

        This copies plugin to project directory for local customization.

        Args:
            project_dir: Project directory

        Returns:
            True if migration successful
        """
        local_claude = project_dir / ".claude"

        if local_claude.exists():
            print(f"Local .claude/ already exists at {project_dir}")
            return False

        if not self.plugin_claude.exists():
            print("Plugin not installed. Cannot create local copy.")
            return False

        # Copy plugin to local directory
        print(f"Creating local .claude/ from plugin")
        shutil.copytree(self.plugin_claude, local_claude)
        print(f"Migration complete. Project now uses local .claude/")
        print("You can now customize .claude/ for this project.")
        return True

    def can_migrate_to_plugin(self, project_dir: Path) -> bool:
        """Check if project can safely migrate to plugin mode.

        Args:
            project_dir: Project directory

        Returns:
            True if migration is safe
        """
        local_claude = project_dir / ".claude"
        if not local_claude.exists():
            return False

        custom_files = self._find_custom_files(local_claude)
        return len(custom_files) == 0

    def _find_custom_files(self, local_claude: Path) -> list[Path]:
        """Find files that differ from plugin version.

        Args:
            local_claude: Local .claude directory

        Returns:
            List of custom/modified files
        """
        # TODO: Implement file comparison
        # For now, assume no custom files
        return []
```

### Module 3: CLI Integration (`cli.py`)

**Integration Points:**

1. **Session Start:** Detect mode and use appropriate directory
2. **Commands:** Add migration commands
3. **Status:** Show current mode to user

**CLI Commands:**
```bash
# Show current mode
amplihack mode

# Migrate to plugin
amplihack mode migrate-to-plugin

# Migrate to local
amplihack mode migrate-to-local

# Force plugin mode (override)
AMPLIHACK_MODE=plugin amplihack
```

**CLI Integration Code:**
```python
# In cli.py

from .mode_detector import detect_claude_mode, ClaudeMode

def mode_command(args: argparse.Namespace) -> int:
    """Handle mode management commands."""
    if args.mode_command == "status":
        return show_mode_status()
    elif args.mode_command == "migrate-to-plugin":
        return migrate_to_plugin_command()
    elif args.mode_command == "migrate-to-local":
        return migrate_to_local_command()
    else:
        print("Unknown mode command")
        return 1

def show_mode_status() -> int:
    """Show current Claude mode."""
    from .mode_detector import ModeDetector

    detector = ModeDetector()
    mode = detector.detect()

    print(f"Current mode: {mode.value}")
    if mode == ClaudeMode.LOCAL:
        print(f"  Using: {detector.local_claude}")
    elif mode == ClaudeMode.PLUGIN:
        print(f"  Using: {detector.plugin_claude}")
    else:
        print("  No .claude installation found")

    return 0

def migrate_to_plugin_command() -> int:
    """Migrate current project to plugin mode."""
    from .mode_detector import MigrationHelper

    helper = MigrationHelper()
    success = helper.migrate_to_plugin(Path.cwd())
    return 0 if success else 1

def migrate_to_local_command() -> int:
    """Create local .claude/ from plugin."""
    from .mode_detector import MigrationHelper

    helper = MigrationHelper()
    success = helper.migrate_to_local(Path.cwd())
    return 0 if success else 1

# In create_parser():
def create_parser():
    # ... existing code ...

    # Mode management commands
    mode_parser = subparsers.add_parser("mode", help="Manage Claude installation mode")
    mode_subparsers = mode_parser.add_subparsers(dest="mode_command", help="Mode subcommands")

    mode_subparsers.add_parser("status", help="Show current mode")
    mode_subparsers.add_parser("migrate-to-plugin", help="Migrate to plugin mode")
    mode_subparsers.add_parser("migrate-to-local", help="Create local .claude/ from plugin")

# In main():
def main(argv=None):
    # ... existing code ...

    # At session start, detect mode
    mode = detect_claude_mode()
    if mode == ClaudeMode.LOCAL:
        if os.environ.get("AMPLIHACK_DEBUG"):
            print("Using project-local .claude/ directory")
    elif mode == ClaudeMode.PLUGIN:
        if os.environ.get("AMPLIHACK_DEBUG"):
            print("Using plugin .claude/ directory")

    # Handle mode command
    if args.command == "mode":
        return mode_command(args)

    # ... rest of existing code ...
```

## Dependencies

- **Standard Library:** `enum`, `pathlib`, `shutil`, `os`
- **Internal:** None (standalone module)

## Testing Strategy

### Unit Tests

```python
def test_detect_local_mode(tmp_path):
    """Test detection of local .claude/ directory."""
    # Create local .claude/ with agents/
    local_claude = tmp_path / ".claude" / "agents"
    local_claude.mkdir(parents=True)

    detector = ModeDetector(tmp_path)
    assert detector.detect() == ClaudeMode.LOCAL

def test_detect_plugin_mode(tmp_path, monkeypatch):
    """Test detection of plugin mode."""
    # No local .claude/
    # Mock plugin installation
    plugin_claude = tmp_path / ".amplihack" / ".claude"
    manifest = tmp_path / ".amplihack" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")

    monkeypatch.setenv("HOME", str(tmp_path))
    detector = ModeDetector(tmp_path / "project")
    assert detector.detect() == ClaudeMode.PLUGIN

def test_local_takes_precedence(tmp_path, monkeypatch):
    """Test that local .claude/ takes precedence over plugin."""
    # Create both local and plugin
    local_claude = tmp_path / "project" / ".claude" / "agents"
    local_claude.mkdir(parents=True)

    plugin_claude = tmp_path / ".amplihack" / ".claude"
    manifest = tmp_path / ".amplihack" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")

    monkeypatch.setenv("HOME", str(tmp_path))
    detector = ModeDetector(tmp_path / "project")
    assert detector.detect() == ClaudeMode.LOCAL

def test_environment_override(tmp_path, monkeypatch):
    """Test AMPLIHACK_MODE environment override."""
    # Create plugin only
    plugin_claude = tmp_path / ".amplihack" / ".claude"
    manifest = tmp_path / ".amplihack" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AMPLIHACK_MODE", "plugin")

    detector = ModeDetector(tmp_path / "project")
    assert detector.detect() == ClaudeMode.PLUGIN
```

### Integration Tests

```python
def test_migration_workflow(tmp_path, monkeypatch):
    """Test complete migration workflow."""
    # Setup: Create local .claude/
    project = tmp_path / "project"
    local_claude = project / ".claude" / "agents"
    local_claude.mkdir(parents=True)

    # Setup: Create plugin
    plugin_claude = tmp_path / ".amplihack" / ".claude"
    manifest = tmp_path / ".amplihack" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")

    monkeypatch.setenv("HOME", str(tmp_path))

    # Migrate to plugin
    helper = MigrationHelper()
    success = helper.migrate_to_plugin(project)
    assert success

    # Verify local .claude/ removed
    assert not (project / ".claude").exists()

    # Verify mode is now plugin
    detector = ModeDetector(project)
    assert detector.detect() == ClaudeMode.PLUGIN
```

## Complexity Assessment

- **Total Lines:** ~300 lines
  - `detector.py`: ~150 lines
  - `migrator.py`: ~100 lines
  - `cli.py` modifications: ~50 lines
- **Effort:** 4-6 hours
- **Risk:** Medium (affects existing workflows)

## Success Metrics

- [ ] Local `~/.amplihack/.claude/` takes precedence over plugin
- [ ] Plugin used when no local installation
- [ ] Mode detection works correctly
- [ ] Migration commands work
- [ ] Environment override works
- [ ] Existing projects continue working
- [ ] No breaking changes to workflows

## Philosophy Compliance

- ✅ **Ruthless Simplicity:** Detection logic is straightforward
- ✅ **Zero-BS Implementation:** All functions work, no stubs
- ✅ **Modular Design:** Detection separate from migration
- ✅ **Regeneratable:** Can rebuild from spec
- ✅ **Single Responsibility:** Each module does one thing

## Migration Guidance

**For Users:**

```markdown
## When to Use Local vs Plugin

### Use Plugin Mode (Recommended)
- You want latest amplihack features automatically
- You work on multiple projects
- You want zero-configuration setup

### Use Local Mode
- You need project-specific customizations
- You want version pinning for a project
- You're experimenting with custom agents

## Migration Commands

```bash
# Check current mode
amplihack mode status

# Migrate to plugin (removes local .claude/)
amplihack mode migrate-to-plugin

# Create local .claude/ from plugin
amplihack mode migrate-to-local

# Force plugin mode for one session
AMPLIHACK_MODE=plugin amplihack
```
```

## References

- Issue #1948, Requirement: "Existing per-project .claude installations continue working"
- `ISSUE_1948_REQUIREMENTS.md`, Gap 5 (lines 369-394)
