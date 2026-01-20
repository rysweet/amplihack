# Azure DevOps CLI Tools

Command-line tools for common Azure DevOps workflows. Each tool is a self-contained Python script that can be run directly or imported as a module.

## Available Tools

### Authentication & Configuration

- **auth_check.py** - Verify Azure DevOps authentication and configuration
  - Checks az CLI installation
  - Verifies login status
  - Validates org/project configuration
  - Auto-fix capability with `--auto-fix`

### Work Item Management

- **create_work_item.py** - Create work items with formatted descriptions
  - Auto-converts markdown to HTML
  - Supports all work item types
  - Optional parent linking
  - Field validation

- **link_parent.py** - Link work items to parent items
  - Validates work item IDs
  - Checks link type compatibility
  - Comprehensive error handling

- **query_wiql.py** - Execute WIQL queries
  - Predefined queries (my-items, unassigned, recent)
  - Multiple output formats (table, json, csv, ids-only)
  - Result limiting and pagination

- **list_types.py** - List work item types and fields
  - Show available types
  - Display field schemas
  - Discover custom types

### Utilities

- **format_html.py** - Convert markdown to Azure DevOps HTML
  - Handles headings, lists, code blocks, links
  - CLI and importable functions
  - Stdin and file input support

## Installation

These tools require:

- Python 3.8+
- Azure CLI with DevOps extension
- Active Azure DevOps authentication

## Usage

Each tool can be run directly:

```bash
# Check authentication
python -m .claude.scenarios.az-devops-tools.auth_check

# Create work item
python -m .claude.scenarios.az-devops-tools.create_work_item \
  --type "User Story" \
  --title "My Story" \
  --description "Story description"

# Query work items
python -m .claude.scenarios.az-devops-tools.query_wiql --query my-items
```

Or imported as modules:

```python
from .claude.scenarios.az_devops_tools.common import AzCliWrapper
from .claude.scenarios.az_devops_tools.format_html import markdown_to_html

# Use wrapper for commands
wrapper = AzCliWrapper(org="...", project="...")
result = wrapper.devops_command(["work-item", "list"])

# Format descriptions
html = markdown_to_html("# Title\\n\\nContent")
```

## Configuration

Tools load configuration from (in order):

1. Command-line arguments (--org, --project)
2. Environment variables (AZURE_DEVOPS_ORG_URL, AZURE_DEVOPS_PROJECT)
3. `az devops configure` defaults
4. Config file (if specified with --config)

## Error Handling

All tools use standard exit codes:

- 0: Success
- 1: Authentication error
- 2: Configuration error
- 3: Command execution error
- 4: Validation error

Error messages include actionable guidance for resolution.

## Documentation

See `/docs/azure-devops/` for comprehensive guides:

- Quick start
- Authentication setup
- Work item management
- WIQL queries
- HTML formatting
- Troubleshooting

## Philosophy

These tools follow amplihack principles:

- Single responsibility per tool
- Reusable, composable components
- Clear error messages
- No swallowed exceptions
- Standard library preferred
- Zero-BS implementation (all code works)
