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
    "SAFE_INPUT_PATTERNS",
    "VM_NAME_RE",
    "SESSION_NAME_RE",
]

VM_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
SESSION_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")

# --- Safety: safe input allow-list ---
# Inputs matching these patterns skip the blocklist entirely.
# These are common safe operations that may accidentally trigger blocklist
# patterns (e.g., "y" matching nothing dangerous, Claude Code commands).
SAFE_INPUT_PATTERNS = [
    re.compile(r"^[yYnN]$"),                         # Single y/n confirmation
    re.compile(r"^(yes|no)$", re.IGNORECASE),         # Full yes/no
    re.compile(r"^/[a-z]"),                            # Slash commands (/dev, /help, etc.)
    re.compile(r"^(exit|quit|q)$", re.IGNORECASE),    # Exit commands
    re.compile(r"^\d+$"),                              # Pure numeric input (menu selection)
    re.compile(r"^(git status|git log|git diff|git branch)"),  # Safe git read-only commands
    re.compile(r"^(ls|pwd|wc|which)\b"),  # Safe read-only shell (no cat/echo — can redirect)
    re.compile(r"^(pytest|make|npm test|npm run|cargo test)"),  # Test/build commands
]

# --- Safety: dangerous input blocklist (H10) ---
# Uses regex with word boundaries to prevent bypass via case/syntax variations.
# Organized by threat category. This is a defense-in-depth layer — the LLM
# confidence thresholds and human --confirm flag are the primary safety gates.
DANGEROUS_PATTERNS = [
    # -- File system destruction --
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\brm\s+-r\s+/", re.IGNORECASE),
    re.compile(r"\brmdir\s+/", re.IGNORECASE),
    re.compile(r"\bshred\b", re.IGNORECASE),
    re.compile(r">\s*/dev/sd[a-z]", re.IGNORECASE),
    re.compile(r"\bmkfs\.", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    # -- Git destructive operations --
    re.compile(r"\bgit\s+push\s+--force\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+-f\b", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-fd", re.IGNORECASE),
    # -- SQL destructive operations --
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE),
    # -- Remote code execution / download-and-run --
    re.compile(r"\bcurl\b.*\|\s*\b(ba)?sh\b", re.IGNORECASE),
    re.compile(r"\bwget\b.*\|\s*\b(ba)?sh\b", re.IGNORECASE),
    re.compile(r"\bcurl\b.*-o\s*-\s*\|", re.IGNORECASE),
    re.compile(r"\bwget\b.*-O\s*-\s*\|", re.IGNORECASE),
    re.compile(r"\bpython[23]?\s+-c\b", re.IGNORECASE),
    re.compile(r"\bperl\s+-e\b", re.IGNORECASE),
    re.compile(r"\bruby\s+-e\b", re.IGNORECASE),
    re.compile(r"\bnode\s+-e\b", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bexec\s*\(", re.IGNORECASE),
    # -- Reverse shells / network exploitation --
    re.compile(r"\bnc\s+-[elp]", re.IGNORECASE),
    re.compile(r"\bncat\b.*-e", re.IGNORECASE),
    re.compile(r"\bsocat\b", re.IGNORECASE),
    re.compile(r"bash\s+-i\s+>&\s*/dev/tcp", re.IGNORECASE),
    re.compile(r"/dev/tcp/", re.IGNORECASE),
    # -- Privilege escalation --
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+\+s\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
    re.compile(r"\bchown\s+root\b", re.IGNORECASE),
    # -- Credential / secret access --
    re.compile(r"\bcat\s+.*/etc/shadow\b", re.IGNORECASE),
    re.compile(r"\bcat\s+.*\.ssh/id_", re.IGNORECASE),
    re.compile(r"\bcat\s+.*\.claude\.json\b", re.IGNORECASE),
    re.compile(r"\bcat\s+.*/hosts\.yml\b", re.IGNORECASE),
    re.compile(r"\bprintenv\b", re.IGNORECASE),
    re.compile(r"\benv\s*$", re.IGNORECASE),  # bare env command
    re.compile(r"\bset\s*$", re.IGNORECASE),  # bare set command
    re.compile(r"ANTHROPIC_API_KEY", re.IGNORECASE),
    re.compile(r"GITHUB_TOKEN", re.IGNORECASE),
    re.compile(r"AZURE_.*SECRET", re.IGNORECASE),
    # -- Persistence / system modification --
    re.compile(r"\bcrontab\b", re.IGNORECASE),
    re.compile(r"\bat\s+-f\b", re.IGNORECASE),
    re.compile(r"\bsystemctl\s+enable\b", re.IGNORECASE),
    re.compile(r">\s*~/\.bashrc\b", re.IGNORECASE),
    re.compile(r">\s*~/\.profile\b", re.IGNORECASE),
    re.compile(r">\s*/etc/", re.IGNORECASE),
    # -- Data exfiltration --
    re.compile(r"\bscp\b.*@", re.IGNORECASE),
    re.compile(r"\brsync\b.*@", re.IGNORECASE),
    re.compile(r"\bbase64\b.*\|.*\bcurl\b", re.IGNORECASE),
    # -- Fork bomb / resource exhaustion --
    re.compile(r":\(\)\s*\{", re.IGNORECASE),  # classic form
    re.compile(r"\bfork\s*\(\)", re.IGNORECASE),
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


_SHELL_METACHAR_RE = re.compile(r"[;|&`]|\$\(")


def is_dangerous_input(text: str) -> bool:
    """Check if input text contains dangerous patterns.

    Shell metacharacters are rejected first to prevent safe-pattern bypass
    via command chaining (e.g., "pytest; rm -rf /").

    Safe patterns (SAFE_INPUT_PATTERNS) are checked next and skip the
    blocklist entirely. This prevents false positives on common operations.
    """
    if _SHELL_METACHAR_RE.search(text):
        return True
    if any(pattern.search(text) for pattern in SAFE_INPUT_PATTERNS):
        return False
    return any(pattern.search(text) for pattern in DANGEROUS_PATTERNS)
