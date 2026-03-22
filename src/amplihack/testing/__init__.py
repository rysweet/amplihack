"""Simple TUI testing for AmplIHack"""

from .send_input_allowlist import (
    ALLOWLIST_ENV_VAR,
    DEFAULT_SAFE_PATTERNS,
    UnsafeInputError,
    get_safe_patterns,
    is_safe_pattern,
    validate_scenario_send_inputs,
    validate_send_input,
)
from .simple_tui import (
    SimpleTUITester,
    TestResult,
    TUITestCase,
    create_amplihack_test,
    create_tui_tester,
    run_amplihack_basics,
)

__all__ = [
    "SimpleTUITester",
    "TUITestCase",
    "TestResult",
    "create_tui_tester",
    "create_amplihack_test",
    "run_amplihack_basics",
    # send_input allow-list
    "DEFAULT_SAFE_PATTERNS",
    "ALLOWLIST_ENV_VAR",
    "UnsafeInputError",
    "get_safe_patterns",
    "is_safe_pattern",
    "validate_send_input",
    "validate_scenario_send_inputs",
]
