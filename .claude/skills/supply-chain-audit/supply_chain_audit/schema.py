# File: supply_chain_audit/schema.py
"""Finding schema — 11-field contract from contracts.md."""

import re
from dataclasses import dataclass

VALID_SEVERITIES = {"Critical", "High", "Medium", "Info"}
VALID_TOOLS = frozenset(
    {
        None,
        "crane",
        "gh",
        "syft",
        "grype",
        "cosign",
        "actionlint",
        "zizmor",
        "detect-secrets",
        "cargo-audit",
        "go-mod-verify",
        "hadolint",
    }
)

_SEVERITY_FROM_PREFIX = {
    "CRITICAL": "Critical",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "INFO": "Info",
}

_ID_PATTERN = re.compile(r"^(CRITICAL|HIGH|MEDIUM|INFO)-(\d{3})$")


class FindingId:
    """Validates and parses a finding ID in {SEVERITY}-{NNN} format."""

    def __init__(self, id_str: str):
        if "*" in str(id_str):
            raise ValueError(f"wildcard not allowed in finding ID: '{id_str}'")

        match = _ID_PATTERN.match(str(id_str))
        if not match:
            s = str(id_str)
            if "-" not in s:
                raise ValueError(
                    f"Invalid finding ID '{s}': missing severity prefix. "
                    "Expected format: CRITICAL-001, HIGH-042, MEDIUM-007, INFO-001"
                )
            parts = s.split("-", 1)
            prefix, seq = parts[0], parts[1]
            if prefix not in _SEVERITY_FROM_PREFIX:
                if prefix.upper() in _SEVERITY_FROM_PREFIX:
                    raise ValueError(
                        f"Invalid severity prefix '{prefix}' in finding ID '{s}': "
                        "severity prefix must be uppercase (CRITICAL, HIGH, MEDIUM, INFO)"
                    )
                raise ValueError(
                    f"Invalid severity prefix '{prefix}' in finding ID '{s}'. "
                    "Must be one of: CRITICAL, HIGH, MEDIUM, INFO"
                )
            if not seq:
                raise ValueError(f"Invalid finding ID '{s}': missing sequence number")
            if not re.match(r"^\d{3}$", seq):
                raise ValueError(
                    f"Invalid finding ID '{s}': sequence must be 3-digit zero-padded "
                    f"(e.g., 001, 042, 007). Got: '{seq}'"
                )
            raise ValueError(f"Invalid finding ID '{s}'")

        self._raw = id_str
        self._severity = _SEVERITY_FROM_PREFIX[match.group(1)]
        self._sequence = int(match.group(2))

    @property
    def severity(self) -> str:
        return self._severity

    @property
    def sequence(self) -> int:
        return self._sequence

    def __str__(self) -> str:
        return self._raw

    def __repr__(self) -> str:
        return f"FindingId('{self._raw}')"


@dataclass
class Finding:
    """A single supply chain security finding — 11 required fields + optional fields."""

    # Required fields (11)
    id: str
    dimension: int
    severity: str
    file: str
    line: int
    current_value: str
    expected_value: str
    rationale: str
    offline_detectable: bool

    # Optional fields
    tool_required: str | None = None
    contains_secret: bool = False
    fix_url: str | None = None
    accepted_risk: bool = False

    def __post_init__(self):
        # Validate ID format (also catches wildcards)
        FindingId(self.id)

        # Validate dimension
        if not isinstance(self.dimension, int) or self.dimension < 1 or self.dimension > 12:
            raise ValueError(f"dimension must be an integer 1-12, got {self.dimension!r}")

        # Validate severity enum
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {sorted(VALID_SEVERITIES)}, got {self.severity!r}"
            )

        # Validate file path — must be relative, no traversal
        f = self.file
        if f.startswith("/"):
            raise ValueError(f"file must be a relative POSIX path, got absolute path: {f!r}")
        if ".." in f.split("/"):
            raise ValueError(f"file contains path traversal '..': {f!r}")
        if "\x00" in f:
            raise ValueError(f"file contains null byte: {f!r}")

        # Validate line number
        if not isinstance(self.line, int) or self.line < 0:
            raise ValueError(f"line must be a non-negative integer, got {self.line!r}")

        # Validate tool_required against allowlist
        if self.tool_required not in VALID_TOOLS:
            raise ValueError(
                f"tool_required '{self.tool_required}' not in approved list: "
                f"{sorted(t for t in VALID_TOOLS if t)}"
            )

    def render(self) -> str:
        """Render finding as markdown, redacting secret values."""
        current = "<REDACTED>" if self.contains_secret else self.current_value
        # Only redact expected_value if it also would expose a secret
        expected = self.expected_value

        lines = [
            f"**Finding {self.id}** (Dim {self.dimension}) — **{self.severity}**",
            f"**File**: `{self.file}:{self.line}`",
            f"**Severity**: {self.severity}",
            f"**Current**: `{current}`",
            f"**Expected**: `{expected}`",
            f"**Why**: {self.rationale}",
        ]
        if self.accepted_risk:
            lines.append("_[ACCEPTED RISK — review date applies]_")
        if self.fix_url:
            lines.append(f"**Fix**: {self.fix_url}")
        return "\n".join(lines)


def validate_finding(findings: list[Finding]) -> None:
    """Check a list of findings for duplicate IDs and other consistency issues.

    Raises ValueError if duplicates found.
    """
    seen_ids: set = set()
    for f in findings:
        if f.id in seen_ids:
            raise ValueError(
                f"duplicate finding id detected: '{f.id}' appears more than once in the report"
            )
        seen_ids.add(f.id)
