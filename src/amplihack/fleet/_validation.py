"""Shared validation utilities for fleet modules.

Centralizes name validation and dangerous-input detection to avoid
duplicating the same logic across multiple fleet files.

Public API:
    validate_vm_name: Validate VM name for safe subprocess use
    validate_session_name: Validate tmux session name
    is_dangerous_input: Check if text contains dangerous shell/SQL patterns
    DANGEROUS_PATTERNS: Compiled regexes for destructive commands
    VM_NAME_RE: Compiled regex for VM names
    SESSION_NAME_RE: Compiled regex for session names
"""

from __future__ import annotations

import re

__all__ = [
    "validate_vm_name",
    "validate_session_name",
    "is_dangerous_input",
    "DANGEROUS_PATTERNS",
    "VM_NAME_RE",
    "SESSION_NAME_RE",
]

VM_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
SESSION_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")

# --- Safety: dangerous input blocklist (H10) ---
# Uses regex with word boundaries to prevent bypass via case/syntax variations.
DANGEROUS_PATTERNS = [
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\brm\s+-r\s+/", re.IGNORECASE),
    re.compile(r"\brmdir\s+/", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+--force\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+-f\b", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE),
    re.compile(r">\s*/dev/sda", re.IGNORECASE),
    re.compile(r"\bmkfs\.", re.IGNORECASE),
    re.compile(r":\(\)\s*\{", re.IGNORECASE),  # fork bomb prefix
]


def validate_vm_name(name: str) -> str:
    """Validate VM name contains only safe characters for subprocess use."""
    if not VM_NAME_RE.match(name):
        raise ValueError(f"Invalid VM name: {name!r}")
    return name


def validate_session_name(name: str) -> str:
    """Validate session name contains only safe characters."""
    if not SESSION_NAME_RE.match(name):
        raise ValueError(f"Invalid session name: {name!r}")
    return name


def is_dangerous_input(text: str) -> bool:
    """Check if input text contains dangerous patterns."""
    return any(pattern.search(text) for pattern in DANGEROUS_PATTERNS)
