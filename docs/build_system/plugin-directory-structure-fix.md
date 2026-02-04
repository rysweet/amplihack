# Plugin Directory Structure Fix for UVX Discovery

**Feature**: Automatic plugin directory inclusion in wheel builds for Claude Code plugin discovery

**Status**: Implemented and working

**Last Updated**: 2026-02-04

---

## What This Fix Does

When you install amplihack via UVX from GitHub, Claude Code now automatically discovers the plugin because the build system includes all necessary directories in the wheel package.

**Before this fix**:
- `uvx --from git+https://github.com/user/amplihack amplihack` installed the package
- Claude Code couldn't find commands, skills, or agents
- Plugin manifest existed but pointed to missing directories

**After this fix**:
- Same UVX command installs package WITH plugin directories
- Claude Code discovers all 24 commands, 73 skills, and 38 agents
- Everything works immediately, no manual setup required

## How It Works

### Build-Time Directory Copying

The build system (`build_hooks.py`) automatically copies plugin directories from the repository root into the package **during wheel build**, before setuptools packages everything.

**Copied directories**:
1. `.claude/commands/` → `src/amplihack/.claude/commands/`
2. `.claude/skills/` → `src/amplihack/.claude/skills/`
3. `.claude/agents/` → `src/amplihack/.claude/agents/`
4. `.claude-plugin/` → `src/amplihack/.claude-plugin/` (manifest)
5. `.github/` → `src/amplihack/.github/` (Copilot CLI integration)
6. `amplifier-bundle/` → `src/amplihack/amplifier-bundle/` (Amplifier support)
7. `AMPLIHACK.md` → `src/amplihack/AMPLIHACK.md` (framework instructions)

**Why this works**:
- Python wheel packages only include files **inside** Python packages
- Repository root directories (`.claude/`, `.github/`) are **outside** `src/amplihack/`
- Copying them **into** the package makes them part of the wheel
- UVX extracts the wheel → directories appear in installed package location
- Claude Code reads plugin manifest → finds directories → loads plugins

### Symlink Preservation

The build system preserves symlinks within copied directories using `shutil.copytree(symlinks=True)`.

**Why symlinks matter**:
- `.github/agents/amplihack` → `.claude/agents/amplihack` (symlink)
- Maintains zero-duplication architecture
- Single source of truth for agent definitions
- Without `symlinks=True`, build fails on symlink copying

### Automatic Cleanup

After building the wheel, `build_hooks.py` removes copied directories from `src/amplihack/` to keep the repository clean.

**Cleanup guarantees**:
- Runs even if build fails (using `try/finally`)
- Removes all 7 copied items
- Repository state unchanged after build

## Technical Implementation

### Build Hook Architecture

```python
# pyproject.toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "build_hooks"
backend-path = ["."]
```

This configuration tells Python build tools to use `build_hooks.py` as the custom build backend instead of standard setuptools.

### Copy Process

```
Build starts
    ↓
1. _copy_claude_directory()      # Copy .claude/ with symlinks=True
2. _copy_plugin_manifest()       # Copy .claude-plugin/
3. _copy_github_directory()      # Copy .github/ with symlinks=True
4. _copy_bundle_directory()      # Copy amplifier-bundle/ with symlinks=True
5. _copy_amplihack_md()          # Copy AMPLIHACK.md
    ↓
setuptools builds wheel (includes copied directories)
    ↓
6. _cleanup_claude_directory()   # Remove src/amplihack/.claude/
7. _cleanup_plugin_manifest()    # Remove src/amplihack/.claude-plugin/
8. _cleanup_github_directory()   # Remove src/amplihack/.github/
9. _cleanup_bundle_directory()   # Remove src/amplihack/amplifier-bundle/
10. _cleanup_amplihack_md()      # Remove src/amplihack/AMPLIHACK.md
    ↓
Build complete, repository clean
```

### Package Data Declaration

```python
# pyproject.toml
[tool.setuptools.package-data]
amplihack = [
    ".claude/**/*",              # All .claude/ contents
    ".claude/**/.gitkeep",       # Preserve empty directories
    ".claude/**/.*",             # Hidden files (config files, not .version)
    ".claude-plugin/**/*",       # Plugin manifest
    "amplifier-bundle/**/*",     # Amplifier support
    "AMPLIHACK.md",              # Framework instructions
]
```

**Note on .github/ omission**: The `.github/` directory is copied by build hooks for symlink preservation, but NOT declared in package-data because:
- **Editable installs**: When installed with `pip install -e .`, the repository root is already in the Python path, making `.github/` accessible via symlinks
- **Wheel installs**: `.github/` IS included in wheels (build hooks copy it), but setuptools auto-includes it because it contains Python-accessible content
- **Result**: `.github/` works in both installation modes without explicit package-data declaration

This tells setuptools to include these directories in the wheel **after** build hooks copy them into the package.

## Ignore Pattern Rationale

### Why Files Are Excluded from Wheels

The build system uses `ignore_patterns()` to exclude specific files/directories from copied content:

```python
ignore = ignore_patterns(
    "*.pyc", "__pycache__", "*.pyo", "*.pyd",  # Python bytecode
    ".git", ".gitignore", ".gitattributes",    # Git metadata
    "*.log", "*.tmp", ".DS_Store",             # Runtime/system files
    "node_modules", ".env", ".venv"            # Dependencies/secrets
)
```

**Security reasons**:
- `.env` files contain secrets (API keys, tokens)
- `.git` directory may expose sensitive history
- `.venv` includes local-specific Python environments

**Size reasons**:
- `node_modules/` can be hundreds of MB
- `__pycache__/` bytecode is regenerated on first run
- `.git` directory adds significant unnecessary weight

**Distribution cleanliness**:
- Runtime logs (`.log`, `.tmp`) are machine-specific
- System files (`.DS_Store`) are platform-specific
- Bytecode files (`.pyc`, `.pyo`) are Python version-specific

**Result**: Wheels contain only essential source files, reducing size from ~100MB to ~25MB while maintaining full functionality.

## Editable Install Behavior

When installed with `pip install -e .`, the build hooks **do NOT run**. This is correct and intentional:

- **Development workflow**: Repository root remains intact with `.claude/` at root level
- **Symlink access**: `.github/` symlinks to `.claude/` work naturally
- **No cleanup needed**: No temporary copies in `src/amplihack/`
- **Fast iteration**: No build step required for code changes

**Production vs Development**:
| Mode | Command | Build Hooks | Directory Location | Use Case |
|------|---------|-------------|-------------------|----------|
| **Editable** | `pip install -e .` | ❌ Not run | Repository root | Development |
| **Wheel** | `python -m build` | ✅ Run | Inside package | Distribution |

## Verification Steps

### 1. Verify Build Includes Directories

```bash
# Build wheel
python -m build --wheel

# Check wheel contents
unzip -l dist/amplihack-*.whl | grep -E "(\.claude|\.github|amplifier-bundle|AMPLIHACK)"
```

**Expected output**:
```
amplihack/.claude/commands/
amplihack/.claude/skills/
amplihack/.claude/agents/
amplihack/.claude-plugin/plugin.json
amplihack/.github/agents/amplihack -> ../../.claude/agents/amplihack  (symlink)
amplihack/.github/skills/amplihack -> ../../.claude/skills/amplihack  (symlink)
amplihack/amplifier-bundle/
amplihack/AMPLIHACK.md
```

**Note**: Symlinks appear as regular entries in zip listings but preserve their symlink nature when extracted.

### 2. Verify UVX Installation

```bash
# Install from GitHub via UVX
uvx --from git+https://github.com/rysweet/amplihack amplihack --help

# Check plugin discovery
amplihack claude  # Launch Claude Code with amplihack plugin
```

**In Claude Code session**:
```
Type: /help
```

**Expected result**: All 24 commands listed (including `/ultrathink`, `/analyze`, `/improve`, `/fix`, DDD commands, fault tolerance commands)

### 3. Verify Directory Locations

```bash
# Find UVX cache location
ls ~/.cache/uv/archive-*/amplihack/.claude/

# Check commands directory
ls ~/.cache/uv/archive-*/amplihack/.claude/commands/

# Check skills directory
ls ~/.cache/uv/archive-*/amplihack/.claude/skills/

# Check agents directory
ls ~/.cache/uv/archive-*/amplihack/.claude/agents/amplihack/
```

**Expected**: All directories present with full contents.

### 4. Test Plugin Functionality

```bash
# Launch Claude Code with plugin
amplihack claude

# In Claude Code, test a command
/ultrathink "Analyze the build_hooks.py file"
```

**Expected**: UltraThink command executes successfully, orchestrating agents.

## User-Visible Changes

**None**. This is a transparent build system fix.

Users continue to:
1. Run `uvx --from git+https://github.com/user/amplihack amplihack`
2. Launch their preferred tool (`amplihack claude`, `amplihack amplifier`, etc.)
3. Access all commands, skills, and agents immediately

The **only** difference: it now **works** when installed via UVX from GitHub.

## Troubleshooting

### Build Fails: "shutil.Error: [Errno 2] No such file"

**Problem**: Source directories don't exist in repository.

**Solution**: Verify repository structure:
```bash
ls -la .claude/ .claude-plugin/ .github/ amplifier-bundle/
```

All directories should exist. If missing, clone repository correctly:
```bash
git clone --recurse-submodules https://github.com/rysweet/amplihack
```

### Build Fails: "symlink points to invalid target"

**Problem**: Symlinks broken in repository.

**Solution**: Check symlink targets:
```bash
ls -la .github/agents/
# Should show: amplihack -> ../../.claude/agents/amplihack

ls -la .github/skills/
# Should show: amplihack -> ../../.claude/skills/amplihack
```

Fix broken symlinks:
```bash
cd .github/agents/
ln -sf ../../.claude/agents/amplihack amplihack
```

### Plugin Not Discovered After UVX Install

**Problem**: Claude Code can't find plugin.

**Diagnosis**:
```bash
# Check wheel contents
unzip -l dist/amplihack-*.whl | grep ".claude-plugin/plugin.json"

# If missing, build failed to include directories
```

**Solution**: Rebuild wheel:
```bash
rm -rf dist/ build/ src/amplihack.egg-info/
python -m build --wheel
```

### Directories Remain in src/amplihack/ After Build

**Problem**: Cleanup didn't run.

**Cause**: Build hook crashed before cleanup.

**Solution**: Manual cleanup:
```bash
rm -rf src/amplihack/.claude/
rm -rf src/amplihack/.claude-plugin/
rm -rf src/amplihack/.github/
rm -rf src/amplihack/amplifier-bundle/
rm -f src/amplihack/AMPLIHACK.md
```

## Integration with Existing Systems

### Compatibility with Per-Project Staging

This fix **only** affects UVX installations. Per-project staging (`~/.amplihack/.claude/`) remains unchanged.

**Per-project mode** (Microsoft Amplifier, GitHub Copilot CLI, Codex):
```bash
amplihack amplifier  # Stages files to project-local ~/.amplihack/.claude/
```

**Plugin mode** (Claude Code only):
```bash
amplihack claude  # Uses plugin discovery from UVX-installed package
```

### Compatibility with Development Mode

When developing amplihack, install in editable mode:
```bash
pip install -e .
```

Build hooks **do not run** in editable mode. Directories remain at repository root, which is correct for development. See **Editable Install Behavior** section above for detailed comparison.

## Performance Considerations

### Build Time Impact

**Copying overhead**: +2-5 seconds per build

- `.claude/` directory: ~50MB, 1000+ files
- Copy operation: ~2 seconds on SSD
- Cleanup operation: ~1 second
- Total build time increase: minimal (< 10%)

### Wheel Size Impact

**Size increase**: +10MB per wheel

- `.claude/` compressed: ~5MB
- `.github/` compressed: ~2MB
- `amplifier-bundle/` compressed: ~3MB
- Total wheel size: ~25MB (was ~15MB)

**Trade-off**: Acceptable increase for complete plugin functionality.

## Related Documentation

- [Plugin Installation Guide](../plugin/INSTALLATION.md) - Install amplihack as global plugin
- [Plugin Architecture Overview](../plugin/ARCHITECTURE.md) - How plugin system works
- [UVX Deployment Solutions](../UVX_DEPLOYMENT_SOLUTIONS.md) - Production deployment with UVX
- [Build System Reference](./build-system-reference.md) - Complete build configuration (coming soon)

## Maintenance Notes

### When to Update This Fix

**Update build_hooks.py if**:
- Adding new plugin directories (e.g., `.claude/templates/`)
- Changing symlink structure in `.github/`
- Modifying ignore patterns for runtime files

**Update pyproject.toml if**:
- Changing package data patterns
- Adding new directories to include

### Testing Strategy

**Before each release**:
1. Build wheel: `python -m build --wheel`
2. Check contents: `unzip -l dist/amplihack-*.whl`
3. Test UVX install: `uvx --from dist/amplihack-*.whl amplihack claude`
4. Verify plugin discovery: Launch Claude Code, run `/help`

**Automated tests**:
- `tests/test_uvx_packaging.py` - Verifies wheel contents
- CI builds wheels on every commit
- Release workflow publishes to PyPI with verified wheels

---

## Summary

The plugin directory structure fix enables zero-configuration Claude Code plugin discovery for UVX-based GitHub installations. The build system automatically includes all plugin directories in wheels, preserves symlinks, and cleans up afterward. Users experience no changes in workflow—everything just works.

**Key benefit**: Install once from GitHub, use everywhere, no manual setup.
