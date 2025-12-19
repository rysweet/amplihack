"""
Check broken links in documentation sites and markdown files.

This module provides tools to check for broken links using linkinator.
"""

from .link_checker import (
    BrokenLink,
    LinkCheckReport,
    check_local,
    check_site,
    format_report,
    get_exit_code,
)

__all__ = [
    "BrokenLink",
    "LinkCheckReport",
    "check_site",
    "check_local",
    "format_report",
    "get_exit_code",
]
