"""Shared validation utilities for fleet modules.

Centralizes name validation to avoid duplicating the same regex across 7+ files.

Public API:
    validate_vm_name: Validate VM name for safe subprocess use
    validate_session_name: Validate tmux session name
    VM_NAME_RE: Compiled regex for VM names
    SESSION_NAME_RE: Compiled regex for session names
"""

from __future__ import annotations

import re

__all__ = ["validate_vm_name", "validate_session_name", "VM_NAME_RE", "SESSION_NAME_RE"]

VM_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
SESSION_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")


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
