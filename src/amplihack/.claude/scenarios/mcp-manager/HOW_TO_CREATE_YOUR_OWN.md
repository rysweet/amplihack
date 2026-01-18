# How to Create Your Own Configuration Manager Tool

This guide shows you how to create a similar configuration management tool for other JSON/YAML configuration files, following the MCP Manager pattern.

## Overview

MCP Manager demonstrates a four-module brick architecture for safe configuration management:

1. **Config I/O Module** - Atomic reads/writes with backup
2. **Operations Module** - Business logic (immutable)
3. **CLI Module** - User interface
4. **Public API Module** - Exports

This pattern can be adapted for any configuration management task.

## Step 1: Define Your Configuration Schema

First, understand the configuration structure you'll manage.

**Example: Managing Docker Compose Services**

```yaml
# docker-compose.yml
services:
  web:
    image: nginx:latest
    enabled: true
    ports:
      - "80:80"
  db:
    image: postgres:14
    enabled: false
```

**Identify:**

- What you're managing: Services
- Key operations: enable/disable/add/remove
- Validation rules: required fields, constraints

## Step 2: Create Config I/O Module

**File**: `config_manager.py`

**Template:**

```python
"""Configuration management for <your config file>."""

import json  # or yaml, toml, etc.
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def read_config(config_path: Path) -> dict[str, Any]:
    """Read and parse configuration file.

    Args:
        config_path: Path to config file

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If config doesn't exist
        <ParseError>: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)  # or yaml.safe_load(f)


def write_config(config_path: Path, data: dict[str, Any]) -> None:
    """Write configuration atomically.

    Uses temp file + rename for atomic write.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = config_path.with_suffix('.tmp')

    try:
        mode = config_path.stat().st_mode if config_path.exists() else 0o644

        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)  # or yaml.dump(data, f)
            f.write('\n')

        temp_path.chmod(mode)
        temp_path.replace(config_path)  # Atomic

    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def backup_config(config_path: Path) -> Path:
    """Create timestamped backup."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.parent / f"{config_path.stem}_backup_{timestamp}{config_path.suffix}"

    shutil.copy2(config_path, backup_path)
    _cleanup_old_backups(config_path.parent, config_path.stem)

    return backup_path


def restore_config(backup_path: Path, config_path: Path) -> None:
    """Restore from backup."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    shutil.copy2(backup_path, config_path)


def _cleanup_old_backups(backup_dir: Path, stem: str, keep_count: int = 10) -> None:
    """Remove old backups, keep most recent."""
    backup_pattern = f"{stem}_backup_*"
    backups = sorted(backup_dir.glob(backup_pattern), reverse=True)

    for old_backup in backups[keep_count:]:
        try:
            old_backup.unlink()
        except OSError:
            pass
```

**Key Principles:**

- Atomic writes (temp file + rename)
- Preserve file permissions
- Auto-cleanup old backups
- Clear error messages

## Step 3: Create Operations Module

**File**: `operations.py`

**Template:**

```python
"""Business logic for <configuration entity> management."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfigEntity:
    """Model for your configuration entity.

    Attributes:
        name: Unique identifier
        # Add your fields here
        enabled: Whether entity is enabled
    """
    name: str
    # Add your fields
    enabled: bool = True

    def validate(self) -> list[str]:
        """Validate entity configuration.

        Returns:
            List of error messages, empty if valid
        """
        errors = []

        # Add your validation rules
        if not self.name:
            errors.append("Name is required")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            # Add your fields
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ConfigEntity":
        """Create from configuration dict."""
        return cls(
            name=name,
            # Map your fields from data
            enabled=data.get("enabled", True),
        )


def list_entities(config: dict[str, Any]) -> list[ConfigEntity]:
    """List all entities from configuration."""
    entities = []
    # Adjust key to match your config structure
    entity_data = config.get("entities", [])

    for data in entity_data:
        if isinstance(data, dict):
            name = data.get("name", "")
            entities.append(ConfigEntity.from_dict(name, data))

    return entities


def enable_entity(config: dict[str, Any], name: str) -> dict[str, Any]:
    """Enable an entity (immutable operation).

    Returns new config dict, does not modify input.
    """
    import copy
    new_config = copy.deepcopy(config)

    entities = new_config.get("entities", [])
    found = False

    for entity_data in entities:
        if isinstance(entity_data, dict) and entity_data.get("name") == name:
            entity_data["enabled"] = True
            found = True
            break

    if not found:
        raise ValueError(f"Entity not found: {name}")

    return new_config


def disable_entity(config: dict[str, Any], name: str) -> dict[str, Any]:
    """Disable an entity (immutable operation)."""
    import copy
    new_config = copy.deepcopy(config)

    entities = new_config.get("entities", [])
    found = False

    for entity_data in entities:
        if isinstance(entity_data, dict) and entity_data.get("name") == name:
            entity_data["enabled"] = False
            found = True
            break

    if not found:
        raise ValueError(f"Entity not found: {name}")

    return new_config


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate entire configuration."""
    errors = []

    # Check structure
    if "entities" not in config:
        errors.append("Missing 'entities' key")
        return errors

    entities = config.get("entities")
    if not isinstance(entities, list):
        errors.append("'entities' must be a list")
        return errors

    # Validate each entity
    seen_names = set()
    for idx, entity_data in enumerate(entities):
        if not isinstance(entity_data, dict):
            errors.append(f"Entity at index {idx} is not a dict")
            continue

        name = entity_data.get("name", "")
        entity = ConfigEntity.from_dict(name, entity_data)
        entity_errors = entity.validate()

        if entity_errors:
            errors.extend([f"Entity '{name}': {err}" for err in entity_errors])

        # Check duplicates
        if name in seen_names:
            errors.append(f"Duplicate name: {name}")
        seen_names.add(name)

    return errors
```

**Key Principles:**

- Immutable operations (deep copy, return new)
- Data model with validation
- Clear error messages
- Type hints throughout

## Step 4: Create CLI Module

**File**: `cli.py`

**Template:**

```python
"""Command-line interface."""

import argparse
import sys
from pathlib import Path

from .config_manager import backup_config, read_config, restore_config, write_config
from .operations import (
    ConfigEntity,
    enable_entity,
    disable_entity,
    list_entities,
    validate_config,
)


def get_config_path() -> Path:
    """Get path to configuration file."""
    # Adjust to your config location
    return Path("config.json")


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format ASCII table."""
    if not rows:
        return "No data to display"

    # Calculate widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Build table
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_cells = [f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)]
    header_line = "|" + "|".join(header_cells) + "|"

    data_lines = []
    for row in rows:
        cells = [f" {str(cell):<{col_widths[i]}} " for i, cell in enumerate(row)]
        data_lines.append("|" + "|".join(cells) + "|")

    return "\n".join([separator, header_line, separator] + data_lines + [separator])


def cmd_list(args: argparse.Namespace) -> int:
    """List command."""
    try:
        config_path = get_config_path()
        config = read_config(config_path)
        entities = list_entities(config)

        if not entities:
            print("No entities configured")
            return 0

        # Build table
        headers = ["Name", "Enabled"]  # Adjust columns
        rows = [[e.name, "Yes" if e.enabled else "No"] for e in entities]

        print(format_table(headers, rows))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_enable(args: argparse.Namespace) -> int:
    """Enable command."""
    try:
        config_path = get_config_path()
        config = read_config(config_path)

        backup_path = backup_config(config_path)
        print(f"Created backup: {backup_path.name}")

        try:
            new_config = enable_entity(config, args.name)

            errors = validate_config(new_config)
            if errors:
                print("Validation errors:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                raise ValueError("Validation failed")

            write_config(config_path, new_config)
            print(f"Successfully enabled: {args.name}")
            return 0

        except Exception as e:
            restore_config(backup_path, config_path)
            print(f"Error (rolled back): {e}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_disable(args: argparse.Namespace) -> int:
    """Disable command."""
    # Similar to cmd_enable, but call disable_entity
    pass


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate command."""
    try:
        config_path = get_config_path()
        config = read_config(config_path)

        errors = validate_config(config)

        if not errors:
            print("✓ Configuration is valid")
            return 0
        else:
            print("Validation errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="your-tool",
        description="Manage <your configuration>",
    )

    subparsers = parser.add_subparsers(dest="command")

    # List command
    subparsers.add_parser("list", help="List all entities")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable entity")
    enable_parser.add_argument("name", help="Entity name")

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable entity")
    disable_parser.add_argument("name", help="Entity name")

    # Validate command
    subparsers.add_parser("validate", help="Validate configuration")

    args = parser.parse_args(argv)

    # Dispatch
    if args.command == "list":
        return cmd_list(args)
    elif args.command == "enable":
        return cmd_enable(args)
    elif args.command == "disable":
        return cmd_disable(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Key Principles:**

- Clear command structure
- Backup before modifications
- Rollback on errors
- User-friendly output

## Step 5: Create Public API Module

**File**: `__init__.py`

```python
"""Your tool - Configuration management."""

from .config_manager import backup_config, read_config, restore_config, write_config
from .operations import (
    ConfigEntity,
    enable_entity,
    disable_entity,
    list_entities,
    validate_config,
)
from .cli import main

__all__ = [
    "read_config",
    "write_config",
    "backup_config",
    "restore_config",
    "ConfigEntity",
    "list_entities",
    "enable_entity",
    "disable_entity",
    "validate_config",
    "main",
]

__version__ = "1.0.0"
```

## Step 6: Create Tests

**File**: `tests/test_config_manager.py`

```python
"""Tests for config_manager."""

import json
import pytest
from ..config_manager import read_config, write_config, backup_config


@pytest.fixture
def temp_config(tmp_path):
    config_path = tmp_path / "config.json"
    config = {"entities": []}
    config_path.write_text(json.dumps(config))
    return config_path


def test_read_config(temp_config):
    config = read_config(temp_config)
    assert isinstance(config, dict)


def test_write_config_atomic(tmp_path):
    config_path = tmp_path / "config.json"
    write_config(config_path, {"test": "data"})

    # No .tmp file remains
    assert not config_path.with_suffix('.tmp').exists()


def test_backup_config(temp_config):
    backup_path = backup_config(temp_config)
    assert backup_path.exists()
    assert "backup" in backup_path.name
```

**File**: `tests/test_operations.py`

```python
"""Tests for operations."""

import pytest
from ..operations import ConfigEntity, enable_entity, validate_config


def test_entity_validate():
    entity = ConfigEntity(name="test")
    errors = entity.validate()
    assert errors == []


def test_enable_entity_immutability():
    config = {"entities": [{"name": "test", "enabled": False}]}
    new_config = enable_entity(config, "test")

    # Original unchanged
    assert config["entities"][0]["enabled"] is False
    # New config modified
    assert new_config["entities"][0]["enabled"] is True
```

## Step 7: Write Documentation

Create comprehensive README.md with:

- Overview and features
- Installation instructions
- Usage examples for each command
- Architecture description
- Safety features explanation
- Error handling examples

## Testing Checklist

Before considering your tool complete:

- [ ] All unit tests pass
- [ ] Atomic writes work (no partial data)
- [ ] Backups created before modifications
- [ ] Rollback works on errors
- [ ] Immutable operations don't modify input
- [ ] Validation catches invalid data
- [ ] CLI commands have clear output
- [ ] Error messages are helpful
- [ ] Old backups cleaned up automatically
- [ ] File permissions preserved

## Common Pitfalls

1. **Forgetting Deep Copy**: Always deep copy in immutable operations
2. **No Validation**: Validate before writing to prevent corruption
3. **Missing Rollback**: Always wrap modifications in try/except with rollback
4. **Temp File Cleanup**: Ensure .tmp files cleaned up on error
5. **Permission Loss**: Preserve original file permissions

## Adaptation Examples

### YAML Configuration

```python
import yaml

def read_config(path):
    with open(path) as f:
        return yaml.safe_load(f)

def write_config(path, data):
    temp_path = path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    temp_path.replace(path)
```

### TOML Configuration

```python
import tomli
import tomli_w

def read_config(path):
    with open(path, 'rb') as f:
        return tomli.load(f)

def write_config(path, data):
    temp_path = path.with_suffix('.tmp')
    with open(temp_path, 'wb') as f:
        tomli_w.dump(data, f)
    temp_path.replace(path)
```

### Environment Variables

```python
# For .env files
from dotenv import dotenv_values, set_key

def read_config(path):
    return dict(dotenv_values(path))

def enable_feature(path, name):
    set_key(path, name, "true")
```

## Philosophy Compliance

Your tool should follow amplihack principles:

✓ **Ruthless Simplicity** - One module, one purpose
✓ **Modular Design** - Self-contained bricks
✓ **Zero-BS** - Everything works, no placeholders
✓ **Regeneratable** - Clear specifications

## Next Steps

After creating your basic tool:

1. Add more commands (add, remove, edit)
2. Add interactive mode
3. Add configuration validation schemas
4. Add export/import functionality
5. Create a companion skill in `.claude/skills/`

## Questions?

Refer to MCP Manager implementation as reference:

- `/home/azureuser/src/amplihack3/.claude/scenarios/mcp-manager/`

Each module demonstrates the pattern clearly with full working code.
