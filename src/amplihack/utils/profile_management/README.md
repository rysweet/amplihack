# Profile Management System

CLI-based system for managing amplihack component visibility. Profiles control which commands, agents, and skills are visible to Claude Code when it starts.

## Architecture

```
.claude/
├── _all/                    # All components (source of truth)
│   ├── commands/amplihack/
│   ├── agents/amplihack/
│   └── skills/
├── _active/                 # Generated symlink structure for active profile
│   ├── commands/
│   ├── agents/
│   └── skills/
├── commands -> _active/commands   # Top-level symlinks
├── agents -> _active/agents
├── skills -> _active/skills
├── profiles/                # Profile definitions (.yaml files)
│   ├── all.yaml
│   ├── coding.yaml
│   └── research.yaml
└── .active-profile          # Current profile name
```

## User Workflow

**IMPORTANT**: Profile switching MUST be done BEFORE starting Claude Code.

```bash
# OUTSIDE Claude Code
$ amplihack profile use coding
✓ Switched to 'coding' profile
  Commands: 15 enabled
  Agents: 10 enabled
  Skills: 5 enabled

# THEN start Claude Code
$ claude
# Claude Code only sees components enabled by 'coding' profile
```

## CLI Commands

### List Available Profiles

```bash
amplihack profile list
```

Shows all profiles with descriptions and indicates the currently active profile.

### Show Current Profile

```bash
amplihack profile current
```

Displays details about the currently active profile including component counts.

### Switch Profile

```bash
amplihack profile use <profile-name>
```

Switch to a different profile. Creates symlink structure atomically with rollback on error.

**Examples:**
```bash
amplihack profile use all        # Enable all components
amplihack profile use coding     # Development-focused
amplihack profile use research   # Investigation-focused
```

### Show Profile Details

```bash
amplihack profile show <profile-name>
```

Display complete configuration for a profile including all filters and metadata.

### Create New Profile

```bash
amplihack profile create <profile-name>
amplihack profile create <profile-name> --view
```

Create a new profile from template. Use `--view` to display the file contents after creation.

### Validate Profile

```bash
amplihack profile validate <profile-name>
```

Check that a profile YAML file is well-formed and valid.

### Verify Integrity

```bash
amplihack profile verify
```

Verify that the current profile setup is valid and all symlinks are correctly configured.

### Inspect Components

```bash
amplihack profile inspect <profile-name>
amplihack profile inspect <profile-name> --components
```

Show what components would be enabled by a profile without actually switching. Use `--components` to see individual file paths.

## Profile Format

Profiles are YAML files in `.claude/profiles/` directory:

```yaml
name: coding
description: "Development-focused: core workflows, testing, CI/CD"
version: "1.0.0"

includes:
  commands:
    - "amplihack/ultrathink.md"
    - "amplihack/analyze.md"
    - "ddd/*"

  agents:
    - "amplihack/core/*"
    - "amplihack/specialized/fix-agent.md"

  skills:
    - "pdf/*"
    - "xlsx/*"

excludes:
  commands: []
  agents: []
  skills: []

metadata:
  author: "amplihack"
  tags: ["coding", "development"]
  builtin: true
```

### Include/Exclude Patterns

- Patterns are glob-style (e.g., `**/*`, `amplihack/*`, `*/test.md`)
- Includes are applied first (union of all patterns)
- Excludes are removed from includes
- Paths are relative to category directory (commands/, agents/, skills/)

## Built-in Profiles

### all
Complete amplihack environment - all components enabled.

```yaml
includes:
  commands: ["**/*"]
  agents: ["**/*"]
  skills: ["**/*"]
excludes: {}
```

### coding
Development-focused: core workflows, testing, CI/CD.

```yaml
includes:
  commands:
    - "amplihack/ultrathink.md"
    - "amplihack/analyze.md"
    - "amplihack/fix.md"
    - "ddd/*"
  agents:
    - "amplihack/core/*"
    - "amplihack/specialized/fix-agent.md"
    - "amplihack/specialized/cleanup.md"
  skills:
    - "pdf/*"
    - "xlsx/*"
```

### research
Investigation-focused: analysis and discovery.

```yaml
includes:
  commands:
    - "amplihack/ultrathink.md"
    - "amplihack/analyze.md"
    - "amplihack/knowledge-builder.md"
  agents:
    - "amplihack/core/architect.md"
    - "amplihack/specialized/analyzer.md"
    - "amplihack/specialized/knowledge-archaeologist.md"
  skills:
    - "pdf/*"
    - "docx/*"
excludes:
  commands: ["ddd/*"]
  agents: ["amplihack/specialized/fix-agent.md"]
```

## Programmatic Usage

```python
from amplihack.utils.profile_management import ProfileSwitcher, ProfileLoader

# Switch profiles
switcher = ProfileSwitcher()
result = switcher.switch_profile("coding")
print(f"Enabled {result['components']['commands']} commands")

# Load and inspect profiles
loader = ProfileLoader()
profile = loader.load_profile("research")
print(profile.description)

# Get current profile info
info = switcher.get_profile_info()
print(f"Current: {info['name']}")
```

## Key Features

### Zero-Overhead Symlinks
Profiles use symlinks for component filtering - no file copying, instant switching.

### Platform-Aware
Handles Windows junctions and Unix symlinks automatically.

### Atomic Operations
Profile switches are atomic with automatic rollback on error.

### Safety
- Staging directory for building new profile structure
- Backup of current profile before switching
- Rollback on any error during switch

## Testing

Run tests with pytest:

```bash
pytest src/amplihack/utils/profile_management/tests/
```

Test coverage includes:
- Model creation and validation
- YAML loading and parsing
- Symlink operations (cross-platform)
- Profile switching with rollback
- Error conditions and edge cases

## Module Structure

```
profile_management/
├── __init__.py           # Public API exports
├── models.py             # Profile and ComponentFilter classes
├── loader.py             # YAML loading and validation
├── symlink_manager.py    # Platform-aware symlink operations
├── switcher.py           # Profile switching logic
├── cli.py                # CLI command handlers
├── README.md             # This file
└── tests/
    ├── __init__.py
    ├── conftest.py       # Shared fixtures
    ├── test_models.py
    ├── test_loader.py
    └── test_switcher.py
```

## Philosophy Compliance

This module follows amplihack's core principles:

- **Ruthless Simplicity**: Direct symlink manipulation, no complex abstractions
- **Bricks & Studs**: Self-contained module with clear public API
- **Zero-BS Implementation**: All functions work, no stubs or placeholders
- **Regeneratable**: Can be rebuilt from this specification

## Future Enhancements

Potential improvements (not implemented):

1. Profile inheritance (extend base profiles)
2. Dynamic profile generation based on project detection
3. Profile templates for common use cases
4. Integration with Claude Code settings
5. Profile versioning and migration tools
