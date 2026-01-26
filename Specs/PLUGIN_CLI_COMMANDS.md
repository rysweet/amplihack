# Module Specification: Plugin CLI Commands

## Purpose

Provide user-facing CLI commands for installing, uninstalling, and verifying amplihack plugins through the `amplihack plugin` command interface.

## Problem

Issue #1948 requires CLI commands for plugin management, but currently only `PluginManager` backend exists without proper CLI integration. Users cannot easily install, uninstall, or verify plugins via command line.

## Solution Overview

Create three CLI command handlers that wrap the existing `PluginManager` class:

- `plugin install` - Install plugin from source
- `plugin uninstall` - Remove plugin cleanly
- `plugin verify` - Verify installation and discoverability

## Contract

### Inputs

**Command: `amplihack plugin install [source] [options]`**

- `source` (str): Git URL or local path to plugin
- `--force` (bool, optional): Overwrite existing plugin

**Command: `amplihack plugin uninstall [plugin_name]`**

- `plugin_name` (str): Name of plugin to remove

**Command: `amplihack plugin verify [plugin_name]`**

- `plugin_name` (str): Name of plugin to verify
- Returns: Exit code 0 (success) or 1 (failure)

### Outputs

**Install:**

- Success: Prints installation confirmation, location, exit code 0
- Failure: Prints error message, exit code 1

**Uninstall:**

- Success: Prints removal confirmation, exit code 0
- Failure: Prints error message, exit code 1

**Verify:**

- Success: Prints verification report (installed, discoverable, hooks loaded), exit code 0
- Failure: Prints diagnostics, exit code 1

### Side Effects

**Install:**

- Creates plugin directory at `~/.amplihack/.claude/plugins/{plugin_name}/`
- Updates `~/.claude/settings.json` with plugin registration
- Adds plugin to `enabledPlugins` array

**Uninstall:**

- Removes plugin directory
- Removes plugin from `~/.claude/settings.json`
- Removes from `enabledPlugins` array

**Verify:**

- No side effects (read-only operation)

## Implementation Design

### File Structure

```
src/amplihack/
├── cli.py                    # Modified: Add command handlers
└── plugin_manager/
    ├── manager.py            # Existing: Core PluginManager
    ├── cli_handlers.py       # NEW: CLI command implementations
    └── verifier.py           # NEW: Verification logic
```

### Module 1: CLI Handlers (`cli_handlers.py`)

**Purpose:** Implement command handlers for CLI integration

**Public API:**

```python
def handle_plugin_install(args: argparse.Namespace) -> int:
    """Handle plugin install command."""

def handle_plugin_uninstall(args: argparse.Namespace) -> int:
    """Handle plugin uninstall command."""

def handle_plugin_verify(args: argparse.Namespace) -> int:
    """Handle plugin verify command."""

__all__ = [
    "handle_plugin_install",
    "handle_plugin_uninstall",
    "handle_plugin_verify"
]
```

**Implementation:**

```python
def handle_plugin_install(args: argparse.Namespace) -> int:
    """Install plugin from source.

    Args:
        args: Parsed arguments with 'source' and 'force' attributes

    Returns:
        0 on success, 1 on failure
    """
    manager = PluginManager()
    result = manager.install(args.source, force=getattr(args, 'force', False))

    if result.success:
        print(f"✅ Plugin installed: {result.plugin_name}")
        print(f"   Location: {result.installed_path}")
        print(f"   {result.message}")
        return 0
    else:
        print(f"❌ Installation failed: {result.message}")
        return 1

def handle_plugin_uninstall(args: argparse.Namespace) -> int:
    """Uninstall plugin.

    Args:
        args: Parsed arguments with 'plugin_name' attribute

    Returns:
        0 on success, 1 on failure
    """
    manager = PluginManager()
    success = manager.uninstall(args.plugin_name)

    if success:
        print(f"✅ Plugin removed: {args.plugin_name}")
        return 0
    else:
        print(f"❌ Failed to remove plugin: {args.plugin_name}")
        print("   Plugin may not be installed or removal failed")
        return 1

def handle_plugin_verify(args: argparse.Namespace) -> int:
    """Verify plugin installation and discoverability.

    Args:
        args: Parsed arguments with 'plugin_name' attribute

    Returns:
        0 if fully verified, 1 if any check fails
    """
    from .verifier import PluginVerifier

    verifier = PluginVerifier(args.plugin_name)
    result = verifier.verify()

    print(f"Plugin: {args.plugin_name}")
    print(f"  Installed: {'✅' if result.installed else '❌'}")
    print(f"  Discoverable: {'✅' if result.discoverable else '❌'}")
    print(f"  Hooks loaded: {'✅' if result.hooks_loaded else '❌'}")

    if not result.success:
        print("\nDiagnostics:")
        for issue in result.issues:
            print(f"  - {issue}")

    return 0 if result.success else 1
```

### Module 2: Plugin Verifier (`verifier.py`)

**Purpose:** Verify plugin installation and discoverability

**Public API:**

```python
@dataclass
class VerificationResult:
    """Result of plugin verification."""
    success: bool
    installed: bool
    discoverable: bool
    hooks_loaded: bool
    issues: list[str]

class PluginVerifier:
    """Verify plugin installation status."""

    def __init__(self, plugin_name: str):
        """Initialize verifier for specific plugin."""

    def verify(self) -> VerificationResult:
        """Run all verification checks."""

    def check_installed(self) -> bool:
        """Check if plugin directory exists."""

    def check_discoverable(self) -> bool:
        """Check if plugin is in settings.json."""

    def check_hooks_loaded(self) -> bool:
        """Check if hooks are registered."""

__all__ = ["PluginVerifier", "VerificationResult"]
```

**Implementation:**

```python
@dataclass
class VerificationResult:
    success: bool
    installed: bool
    discoverable: bool
    hooks_loaded: bool
    issues: list[str]

class PluginVerifier:
    """Verify plugin installation and discoverability."""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.plugin_root = Path.home() / ".amplihack" / ".claude" / "plugins" / plugin_name
        self.settings_path = Path.home() / ".claude" / "settings.json"

    def verify(self) -> VerificationResult:
        """Run all verification checks."""
        issues = []

        # Check 1: Plugin directory exists
        installed = self.check_installed()
        if not installed:
            issues.append(f"Plugin directory not found: {self.plugin_root}")

        # Check 2: Plugin in settings.json
        discoverable = self.check_discoverable()
        if not discoverable:
            issues.append(f"Plugin not found in {self.settings_path}")

        # Check 3: Hooks loaded
        hooks_loaded = self.check_hooks_loaded()
        if not hooks_loaded:
            issues.append("Hooks not registered or hooks.json missing")

        success = installed and discoverable and hooks_loaded

        return VerificationResult(
            success=success,
            installed=installed,
            discoverable=discoverable,
            hooks_loaded=hooks_loaded,
            issues=issues
        )

    def check_installed(self) -> bool:
        """Check if plugin directory exists with manifest."""
        manifest = self.plugin_root / ".claude-plugin" / "plugin.json"
        return self.plugin_root.exists() and manifest.exists()

    def check_discoverable(self) -> bool:
        """Check if plugin is in Claude Code settings."""
        if not self.settings_path.exists():
            return False

        try:
            import json
            settings = json.loads(self.settings_path.read_text())
            enabled_plugins = settings.get("enabledPlugins", [])
            return self.plugin_name in enabled_plugins
        except (json.JSONDecodeError, KeyError):
            return False

    def check_hooks_loaded(self) -> bool:
        """Check if hooks.json exists and is valid."""
        hooks_json = self.plugin_root / ".claude" / "tools" / "amplihack" / "hooks" / "hooks.json"
        if not hooks_json.exists():
            return False

        try:
            import json
            hooks = json.loads(hooks_json.read_text())
            # Verify at least one hook is defined
            return len(hooks) > 0
        except json.JSONDecodeError:
            return False
```

### Module 3: CLI Integration (`cli.py` modifications)

**Changes to `cli.py`:**

```python
# Add imports at top
from .plugin_manager.cli_handlers import (
    handle_plugin_install,
    handle_plugin_uninstall,
    handle_plugin_verify
)

# In create_parser() function, modify plugin subparser wiring:
def create_parser():
    # ... existing code ...

    # Plugin management commands (already exists in lines 415-436)
    plugin_parser = subparsers.add_parser("plugin", help="Plugin management commands")
    plugin_subparsers = plugin_parser.add_subparsers(
        dest="plugin_command", help="Plugin subcommands"
    )

    # Install command
    install_parser = plugin_subparsers.add_parser(
        "install", help="Install plugin from git URL or local path"
    )
    install_parser.add_argument("source", help="Git URL or local directory path")
    install_parser.add_argument("--force", action="store_true", help="Overwrite existing plugin")

    # Uninstall command
    uninstall_parser = plugin_subparsers.add_parser(
        "uninstall", help="Remove plugin"
    )
    uninstall_parser.add_argument("plugin_name", help="Name of plugin to remove")

    # Verify command (already exists)
    verify_parser = plugin_subparsers.add_parser(
        "verify", help="Verify plugin installation and discoverability"
    )
    verify_parser.add_argument("plugin_name", help="Name of plugin to verify")

    # Link command (already exists - for future use)
    # ...

# In main() function, add command dispatch:
def main(argv=None):
    # ... existing code ...

    # Handle plugin commands
    if args.command == "plugin":
        if args.plugin_command == "install":
            return handle_plugin_install(args)
        elif args.plugin_command == "uninstall":
            return handle_plugin_uninstall(args)
        elif args.plugin_command == "verify":
            return handle_plugin_verify(args)
        else:
            plugin_parser.print_help()
            return 1

    # ... rest of existing code ...
```

## Dependencies

- **Standard Library:** `argparse`, `json`, `pathlib`
- **Internal:** `PluginManager` (already exists in `plugin_manager/manager.py`)

## Implementation Notes

### Key Design Decisions

1. **Separation of Concerns:** CLI handlers are separate from core `PluginManager` logic
2. **User-Friendly Output:** Clear success/failure messages with actionable information
3. **Exit Codes:** Standard Unix convention (0=success, 1=failure)
4. **Verification Checks:** Three-layer verification (installed, discoverable, hooks loaded)

### Simplicity Optimizations

- Reuse existing `PluginManager` class (no duplication)
- Thin CLI handlers (10-20 lines each)
- Verification logic isolated in separate module
- No complex error handling - fail fast with clear messages

### Testing Strategy

**Unit Tests:**

- Test each handler with mocked `PluginManager`
- Test `PluginVerifier` with fixture directories
- Test exit codes for success/failure paths

**Integration Tests:**

- Install plugin from test fixture
- Verify installation
- Uninstall and verify cleanup

**E2E Tests:**

- Full workflow: install → verify → uninstall
- Test with real plugin directory structure

## Test Requirements

### Unit Tests (`tests/unit/test_cli_handlers.py`)

```python
def test_handle_plugin_install_success(mocker):
    """Test successful plugin installation."""

def test_handle_plugin_install_failure(mocker):
    """Test failed plugin installation."""

def test_handle_plugin_uninstall_success(mocker):
    """Test successful plugin uninstallation."""

def test_handle_plugin_verify_success(tmp_path):
    """Test successful verification."""

def test_handle_plugin_verify_failure(tmp_path):
    """Test verification with missing plugin."""
```

### Integration Tests (`tests/integration/test_plugin_cli_integration.py`)

```python
def test_install_uninstall_workflow(tmp_path):
    """Test complete install → verify → uninstall workflow."""

def test_verify_all_checks(tmp_path):
    """Test verification checks all three requirements."""
```

## Complexity Assessment

- **Total Lines:** ~200 lines
  - `cli_handlers.py`: ~80 lines
  - `verifier.py`: ~100 lines
  - `cli.py` modifications: ~20 lines
- **Effort:** 3-5 hours
- **Risk:** Low (wraps existing functionality)

## Success Metrics

- [ ] `amplihack plugin install <source>` installs successfully
- [ ] `amplihack plugin uninstall <name>` removes cleanly
- [ ] `amplihack plugin verify <name>` reports all three checks
- [ ] Exit codes are correct (0=success, 1=failure)
- [ ] User-friendly output with clear messages
- [ ] Test coverage > 80%

## Philosophy Compliance

- ✅ **Ruthless Simplicity:** Thin wrappers, reuse existing code
- ✅ **Zero-BS Implementation:** All functions work, no stubs
- ✅ **Modular Design:** Clear separation (CLI → handlers → manager)
- ✅ **Regeneratable:** Can rebuild from this spec
- ✅ **Single Responsibility:** Each module has one clear purpose
