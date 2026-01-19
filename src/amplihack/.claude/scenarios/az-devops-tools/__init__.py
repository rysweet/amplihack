"""Azure DevOps CLI tools for common workflows.

This package provides command-line tools for working with Azure DevOps:
- auth_check: Verify authentication and configuration
- format_html: Convert markdown to Azure DevOps HTML
- create_work_item: Create work items with formatted descriptions
- link_parent: Link work items to parent items
- query_wiql: Execute WIQL queries
- list_types: List work item types and fields
"""

__version__ = "0.1.0"
__all__ = [
    "auth_check",
    "format_html",
    "create_work_item",
    "link_parent",
    "query_wiql",
    "list_types",
]
