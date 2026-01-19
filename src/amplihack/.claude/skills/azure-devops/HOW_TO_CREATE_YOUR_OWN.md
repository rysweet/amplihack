# How to Create Your Own Azure DevOps Tool

This guide shows you how to create a new tool in the az-devops-tools suite.

## Template Structure

Every tool follows this pattern:

```python
#!/usr/bin/env python3
"""Brief description of what the tool does.

Philosophy:
- Single responsibility
- Standard library preferred
- Clear error messages
- Reusable functions

Public API:
    main_function: Primary tool functionality
    helper_function: Utility function
"""

import argparse
import sys
from typing import Optional

from .common import (
    AzCliWrapper,
    ExitCode,
    handle_error,
    load_config,
)


def main_function(arg1: str, arg2: Optional[str] = None) -> bool:
    """Do the main work of the tool.

    Args:
        arg1: Required argument
        arg2: Optional argument

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If arguments are invalid
    """
    # Implementation here
    pass


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tool description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "--required",
        required=True,
        help="Required argument",
    )

    # Optional arguments
    parser.add_argument(
        "--optional",
        help="Optional argument",
    )

    # Common arguments
    parser.add_argument("--org", help="Azure DevOps organization URL")
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--config", help="Config file path")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    org = args.org or config.get("org")
    project = args.project or config.get("project")

    # Validate required config
    if not org or not project:
        handle_error(
            "Organization and project are required",
            ExitCode.CONFIG_ERROR,
            "Set via --org/--project, environment variables, or az devops configure",
        )

    # Execute main function
    try:
        success = main_function(
            arg1=args.required,
            arg2=args.optional,
        )
        sys.exit(ExitCode.SUCCESS if success else ExitCode.COMMAND_ERROR)
    except ValueError as e:
        handle_error(str(e), ExitCode.VALIDATION_ERROR)
    except Exception as e:
        handle_error(f"Unexpected error: {e}", ExitCode.COMMAND_ERROR)


if __name__ == "__main__":
    main()


__all__ = ["main_function", "main"]
```

## Key Components

### 1. Module Docstring

```python
"""Brief description of what the tool does.

Philosophy:
- Single responsibility
- Standard library preferred
- Clear error messages
- Reusable functions

Public API:
    main_function: Primary tool functionality
    helper_function: Utility function
"""
```

### 2. Use Common Utilities

Import from `common.py`:

```python
from .common import (
    AzCliWrapper,         # For az CLI commands
    ExitCode,             # Standard exit codes
    handle_error,         # Error handling
    load_config,          # Configuration loading
    validate_work_item_id,  # Validation helpers
    format_table,         # Output formatting
)
```

### 3. Argument Parsing

```python
parser = argparse.ArgumentParser(
    description="Tool description",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)

# Always include common arguments
parser.add_argument("--org", help="Azure DevOps organization URL")
parser.add_argument("--project", help="Project name")
parser.add_argument("--config", help="Config file path")
```

### 4. Configuration Loading

```python
config = load_config(args.config)
org = args.org or config.get("org")
project = args.project or config.get("project")

# Validate required config
if not org or not project:
    handle_error(
        "Organization and project are required",
        ExitCode.CONFIG_ERROR,
        "Set via --org/--project, environment variables, or az devops configure",
    )
```

### 5. Error Handling

```python
try:
    # Do work
    result = wrapper.devops_command(["work-item", "show", "--id", work_item_id])
    if not result.success:
        handle_error(
            f"Failed to show work item {work_item_id}",
            ExitCode.COMMAND_ERROR,
            result.stderr,
        )
except ValueError as e:
    handle_error(str(e), ExitCode.VALIDATION_ERROR)
except Exception as e:
    handle_error(f"Unexpected error: {e}", ExitCode.COMMAND_ERROR)
```

### 6. Dual Usage (CLI + Import)

```python
def main_function(arg1: str) -> bool:
    """Reusable function that does the work."""
    # Implementation
    pass

def main() -> None:
    """CLI wrapper around main_function."""
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()

    success = main_function(args.arg1)
    sys.exit(ExitCode.SUCCESS if success else ExitCode.COMMAND_ERROR)

if __name__ == "__main__":
    main()
```

## Testing

Create tests in `tests/test_your_tool.py`:

```python
"""Tests for your_tool module."""

import pytest
from unittest.mock import Mock, patch

from ..your_tool import main_function


class TestMainFunction:
    """Test main_function behavior."""

    def test_success_case(self):
        """Test successful execution."""
        result = main_function("valid_input")
        assert result is True

    def test_validation_error(self):
        """Test validation error handling."""
        with pytest.raises(ValueError, match="Invalid input"):
            main_function("")

    @patch(".claude.scenarios.az_devops_tools.your_tool.AzCliWrapper")
    def test_cli_integration(self, mock_wrapper):
        """Test CLI command execution."""
        mock_result = Mock(success=True, stdout="output")
        mock_wrapper.return_value.devops_command.return_value = mock_result

        result = main_function("input")
        assert result is True
```

## Design Principles

### Single Responsibility

Each tool does ONE thing well:

- `auth_check` only checks authentication
- `format_html` only formats HTML
- `create_work_item` only creates work items

### Composability

Tools can be combined:

```python
from .format_html import markdown_to_html
from .create_work_item import create_work_item

# Format description
html_description = markdown_to_html(markdown_text)

# Create work item with formatted description
create_work_item(
    title="My Story",
    description=html_description,
    work_item_type="User Story",
)
```

### Clear Errors

Always provide actionable error messages:

```python
# BAD
print("Error: Invalid input")

# GOOD
handle_error(
    "Work item ID must be a positive integer",
    ExitCode.VALIDATION_ERROR,
    f"Got: '{work_item_id}'. Example: 1234",
)
```

### No Swallowed Exceptions

```python
# BAD
try:
    do_something()
except:
    pass  # Silent failure

# GOOD
try:
    do_something()
except SpecificError as e:
    handle_error(f"Failed to do something: {e}", ExitCode.COMMAND_ERROR)
```

## Checklist

Before submitting a new tool:

- [ ] Module docstring with philosophy and public API
- [ ] Uses `common.py` utilities
- [ ] Argument parser with common arguments (--org, --project, --config)
- [ ] Configuration loading with fallbacks
- [ ] Proper error handling with actionable messages
- [ ] Standard exit codes
- [ ] Both CLI and importable usage
- [ ] Tests with >80% coverage
- [ ] Added to `__init__.py` exports
- [ ] Documented in main README.md
- [ ] Examples in tool docstring

## Example: Creating a "list-projects" Tool

```python
#!/usr/bin/env python3
"""List all projects in an Azure DevOps organization.

Philosophy:
- Single responsibility: list projects only
- Standard library for formatting
- Clear error messages
- Reusable list_projects function

Public API:
    list_projects: Get list of projects
"""

import argparse
import json
import sys
from typing import List, Dict

from .common import (
    AzCliWrapper,
    ExitCode,
    handle_error,
    load_config,
    format_table,
)


def list_projects(org: str, format: str = "table") -> List[Dict[str, str]]:
    """List all projects in organization.

    Args:
        org: Organization URL
        format: Output format (table, json, csv)

    Returns:
        List of project dictionaries with name, id, description
    """
    wrapper = AzCliWrapper(org=org)
    result = wrapper.devops_command(["project", "list"])

    if not result.success:
        handle_error(
            "Failed to list projects",
            ExitCode.COMMAND_ERROR,
            result.stderr,
        )

    projects = result.json_output.get("value", [])
    return [
        {
            "name": p["name"],
            "id": p["id"],
            "description": p.get("description", ""),
        }
        for p in projects
    ]


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="List Azure DevOps projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format",
    )
    parser.add_argument("--org", required=True, help="Organization URL")
    parser.add_argument("--config", help="Config file path")

    args = parser.parse_args()

    config = load_config(args.config)
    org = args.org or config.get("org")

    if not org:
        handle_error(
            "Organization is required",
            ExitCode.CONFIG_ERROR,
            "Set via --org, environment variable, or az devops configure",
        )

    try:
        projects = list_projects(org, args.format)

        if args.format == "json":
            print(json.dumps(projects, indent=2))
        elif args.format == "csv":
            print("name,id,description")
            for p in projects:
                print(f"{p['name']},{p['id']},{p['description']}")
        else:  # table
            rows = [[p["name"], p["id"], p["description"]] for p in projects]
            print(format_table(["Name", "ID", "Description"], rows))

        sys.exit(ExitCode.SUCCESS)

    except Exception as e:
        handle_error(f"Failed to list projects: {e}", ExitCode.COMMAND_ERROR)


if __name__ == "__main__":
    main()


__all__ = ["list_projects", "main"]
```

This template creates a fully functional tool that:

- Lists projects in an organization
- Supports multiple output formats
- Has proper error handling
- Can be used as CLI or imported
- Follows all design principles
