"""Allow-list for safe send_input patterns in outside-in test scenarios.

Security hardening for the gadugi-agentic-test YAML framework's send_input
action.  Only patterns on the allow-list can be used without explicit
confirmation; arbitrary values require passing confirm=True (or the
--confirm CLI flag when invoking a runner).

Safe patterns are common, low-risk interaction responses:
    y / yes / n / no (confirmation prompts)
    <Enter> / empty newline (proceed / dismiss)
    q / quit / exit (leave interactive mode gracefully)

Everything else — free-text commands, file paths, shell snippets — is
considered untrusted by default and requires explicit confirmation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


# --------------------------------------------------------------------------- #
# Default allow-list
# --------------------------------------------------------------------------- #

#: Immutable default set of safe send_input values.
#: Each entry is the *exact* byte sequence the pattern matches (including
#: any trailing newline character that the test scenario would append).
#: Comparisons are case-insensitive and trailing/leading whitespace is
#: stripped before matching.
DEFAULT_SAFE_PATTERNS: frozenset[str] = frozenset(
    {
        # Bare newline / Enter
        "\n",
        "",
        # Affirmative confirmation
        "y",
        "y\n",
        "yes",
        "yes\n",
        # Negative confirmation
        "n",
        "n\n",
        "no",
        "no\n",
        # Exit / quit
        "q",
        "q\n",
        "quit",
        "quit\n",
        "exit",
        "exit\n",
    }
)

#: Environment variable that points to a JSON file with additional safe
#: patterns.  The file must contain a JSON array of strings, e.g.
#:   ["ok\n", "proceed\n"]
ALLOWLIST_ENV_VAR = "AMPLIHACK_SEND_INPUT_ALLOWLIST"


class UnsafeInputError(ValueError):
    """Raised when a send_input value is not on the allow-list and
    confirmation has not been granted.

    Attributes:
        value: The input value that was rejected.
    """

    def __init__(self, value: str) -> None:
        self.value = value
        safe_repr = repr(value)
        super().__init__(
            f"send_input value {safe_repr} is not on the safe allow-list. "
            "Use --confirm to permit arbitrary input, or add the value to "
            f"the allow-list via the {ALLOWLIST_ENV_VAR} environment variable."
        )


def _load_extra_patterns() -> frozenset[str]:
    """Load additional safe patterns from the optional config file.

    Returns an empty frozenset if the env var is unset or the file is absent.
    """
    config_path_str = os.environ.get(ALLOWLIST_ENV_VAR, "")
    if not config_path_str:
        return frozenset()

    config_path = Path(config_path_str)
    if not config_path.is_file():
        return frozenset()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return frozenset()

    if not isinstance(data, list):
        return frozenset()

    return frozenset(str(p) for p in data if isinstance(p, str))


def get_safe_patterns() -> frozenset[str]:
    """Return the effective allow-list (defaults + any configured extras).

    The result includes all entries from :data:`DEFAULT_SAFE_PATTERNS` plus
    any patterns loaded from :data:`ALLOWLIST_ENV_VAR`.
    """
    return DEFAULT_SAFE_PATTERNS | _load_extra_patterns()


def is_safe_pattern(value: str) -> bool:
    """Return True if *value* is on the effective allow-list.

    Comparison is case-insensitive and ignores leading/trailing whitespace
    (but not interior whitespace — ``"y n"`` is not the same as ``"y"``).

    Args:
        value: The send_input value to check.

    Returns:
        True if the value matches a safe pattern, False otherwise.

    Examples:
        >>> is_safe_pattern("y")
        True
        >>> is_safe_pattern("Y\\n")
        True
        >>> is_safe_pattern("rm -rf /")
        False
    """
    normalised = value.strip().lower()
    safe = get_safe_patterns()

    # Direct match on the normalised value or the normalised value + newline
    return normalised in {p.strip().lower() for p in safe}


def validate_send_input(value: str, confirm: bool = False) -> None:
    """Validate a send_input value against the allow-list.

    Args:
        value:   The value from the ``send_input`` action in a test scenario.
        confirm: If True, bypass the allow-list check (equivalent to passing
                 ``--confirm`` on the CLI).  Use sparingly.

    Raises:
        UnsafeInputError: If *value* is not safe and *confirm* is False.

    Examples:
        >>> validate_send_input("y")          # safe — no exception
        >>> validate_send_input("\\n")        # safe — no exception
        >>> validate_send_input("rm -rf /")   # raises UnsafeInputError
        >>> validate_send_input("rm -rf /", confirm=True)  # bypassed — ok
    """
    if confirm:
        return

    if not is_safe_pattern(value):
        raise UnsafeInputError(value)


def validate_scenario_send_inputs(
    scenario: dict, confirm: bool = False
) -> list[str]:
    """Validate all send_input values in a parsed YAML scenario dict.

    Walks the ``scenario.steps`` list and checks every step whose
    ``action`` is ``send_input``.

    Args:
        scenario: Parsed YAML scenario dictionary (the top-level ``scenario``
                  sub-key, not the file root).
        confirm:  If True, bypass allow-list checks for all steps.

    Returns:
        List of unsafe input values found (empty if all safe or confirmed).

    Raises:
        UnsafeInputError: On the first unsafe value when *confirm* is False.
    """
    unsafe: list[str] = []
    steps = scenario.get("steps", [])

    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("action") != "send_input":
            continue

        value = step.get("value", "")
        if not isinstance(value, str):
            value = str(value)

        if not is_safe_pattern(value):
            if confirm:
                unsafe.append(value)
            else:
                raise UnsafeInputError(value)

    return unsafe


__all__ = [
    "DEFAULT_SAFE_PATTERNS",
    "ALLOWLIST_ENV_VAR",
    "UnsafeInputError",
    "get_safe_patterns",
    "is_safe_pattern",
    "validate_send_input",
    "validate_scenario_send_inputs",
]
