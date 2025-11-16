# Neo4j Container Naming and Selection

This document describes the container naming and selection system for Neo4j memory persistence.

## Overview

The system provides intelligent container naming with multiple selection modes:

- **Default naming**: `amplihack-<directory-name>` (sanitized and truncated)
- **Interactive mode**: Shows menu of existing containers, allows selection or creation
- **Auto mode**: Non-interactive, uses default or CLI-specified name
- **Priority hierarchy**: CLI argument > Environment variable > Interactive/Auto selection

## Usage

### Interactive Mode (Default)

When starting amplihack with Neo4j enabled, you'll see a menu:

```bash
amplihack launch --use-graph-mem
```

Example menu:

```
======================================================================
Neo4j Container Selection
======================================================================

Existing containers:
  1. ✓ amplihack-project1
     Status: Up 2 hours
     Ports: 7787->7687, 7774->7474

  2. ○ amplihack-project2
     Status: Exited (0) 2 days ago
     Ports: 7787->7687, 7774->7474

  3. Create new container: amplihack-myproject

Select container (1-3):
```

### Specify Container Name (CLI)

Use `--use-memory-db` to specify a container name:

```bash
amplihack launch --use-graph-mem --use-memory-db amplihack-myproject
```

### Auto Mode (Non-Interactive)

Set `AMPLIHACK_AUTO_MODE=1` or use the existing `--auto` flag:

```bash
# Using environment variable
AMPLIHACK_AUTO_MODE=1 amplihack launch --use-graph-mem

# Using CLI flag (for auto mode execution)
amplihack launch --use-graph-mem --auto -- -p "your prompt"
```

Auto mode automatically uses the default container name without prompting.

### Environment Variable

Set a persistent container name via environment:

```bash
export NEO4J_CONTAINER_NAME=amplihack-myproject
amplihack launch --use-graph-mem
```

## Priority Hierarchy

Container name resolution follows this priority (highest to lowest):

1. **CLI argument** (`--use-memory-db <name>`)
2. **Environment variable** (`NEO4J_CONTAINER_NAME`)
3. **Interactive selection** (if not in auto mode)
4. **Auto mode default** (`amplihack-<current-directory>`)

## Container Name Rules

### Sanitization

Directory names are sanitized for use in container names:

- Special characters replaced with dashes: `my_project.v2` → `my-project-v2`
- Consecutive dashes collapsed: `my---project` → `my-project`
- Leading/trailing dashes removed: `-project-` → `project`
- Truncated at 40 characters

### Default Format

Default container names follow the pattern:

```
amplihack-<sanitized-directory-name>
```

Examples:

- `/home/user/my-project` → `amplihack-my-project`
- `/home/user/my_app.v2` → `amplihack-my-app-v2`
- `/home/user/very-long-project-name-that-exceeds-limit` → `amplihack-very-long-project-name-that-exceed` (40 chars)

## Multiple Projects

Each project can have its own Neo4j container with isolated data:

```bash
# Project 1
cd ~/projects/web-app
amplihack launch --use-graph-mem
# Uses: amplihack-web-app

# Project 2
cd ~/projects/api-service
amplihack launch --use-graph-mem
# Uses: amplihack-api-service
```

## Integration with Existing Code

The container selection system integrates seamlessly with existing Neo4j code:

### In Python Code

```python
from amplihack.memory.neo4j.config import get_config

# Get the resolved container name
config = get_config()
print(f"Using container: {config.container_name}")
```

### In CLI Commands

All Neo4j-related commands automatically use the resolved container name:

```bash
# These all use the configured container
docker logs <resolved-container-name>
docker restart <resolved-container-name>
```

## Troubleshooting

### Check Current Container

To see which container is being used:

```bash
docker ps | grep amplihack-
```

### List All Amplihack Containers

```bash
docker ps -a --filter "name=amplihack-"
```

### Switch Containers

To switch to a different container, use the CLI argument:

```bash
amplihack launch --use-graph-mem --use-memory-db amplihack-other-project
```

### Reset to Default

To use the default container name, remove environment variables:

```bash
unset NEO4J_CONTAINER_NAME
unset NEO4J_CONTAINER_NAME_CLI
amplihack launch --use-graph-mem
```

## Implementation Details

### Files Modified

- `src/amplihack/memory/neo4j/container_selection.py` - Core selection logic
- `src/amplihack/memory/neo4j/config.py` - Integration with config system
- `src/amplihack/cli.py` - CLI arguments
- `src/amplihack/memory/neo4j/startup_wizard.py` - Dynamic container references

### Key Functions

- `sanitize_directory_name()` - Sanitizes directory names for containers
- `get_default_container_name()` - Generates default name
- `discover_amplihack_containers()` - Lists existing containers
- `select_container_interactive()` - Interactive menu
- `resolve_container_name()` - Priority-based resolution

## Migration from Old System

Previously, all projects shared the same container: `amplihack-neo4j`.

**No action required** - the system automatically:

1. Detects the old container if it exists
2. Shows it in the interactive menu
3. Allows you to continue using it or create new ones

You can keep using the old shared container by setting:

```bash
export NEO4J_CONTAINER_NAME=amplihack-neo4j
```

## Examples

### Example 1: Default Behavior

```bash
cd ~/projects/my-api
amplihack launch --use-graph-mem
# Interactive menu appears
# Select "Create new container: amplihack-my-api"
# Container created: amplihack-my-api
```

### Example 2: Specify Container

```bash
cd ~/projects/my-api
amplihack launch --use-graph-mem --use-memory-db shared-neo4j
# Uses: shared-neo4j (no menu)
```

### Example 3: Auto Mode

```bash
cd ~/projects/my-api
AMPLIHACK_AUTO_MODE=1 amplihack launch --use-graph-mem
# Automatically creates: amplihack-my-api (no menu)
```

### Example 4: Environment Variable

```bash
export NEO4J_CONTAINER_NAME=company-shared-neo4j
cd ~/projects/project-a
amplihack launch --use-graph-mem
# Uses: company-shared-neo4j

cd ~/projects/project-b
amplihack launch --use-graph-mem
# Uses: company-shared-neo4j (same container)
```

## Benefits

1. **Project Isolation**: Each project can have its own memory container
2. **Flexible Sharing**: Teams can share containers via environment variables
3. **Clear Naming**: Container names reflect the project they serve
4. **Backward Compatible**: Existing `amplihack-neo4j` containers still work
5. **Non-Intrusive**: Auto mode prevents prompts in CI/CD environments
