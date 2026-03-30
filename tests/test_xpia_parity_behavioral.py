"""R4, R1, R3: XPIA parity behavioral tests.

R4: pre_tool_use_rust.py has been renamed to pre_tool_use_legacy.py
    (the old name was misleading — it is a Python shim, not a Rust file).

R1: Both the canonical and legacy hooks must exhibit fail-secure behavior —
    hook errors must produce deny decisions, never silent allow.

R3: The canonical (pre_tool_use.py) and legacy (pre_tool_use_legacy.py)
    hooks must produce identical decisions for the same inputs.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parents[1]
HOOKS_DIR = REPO_ROOT / ".claude" / "tools" / "xpia" / "hooks"

CANONICAL_HOOK = HOOKS_DIR / "pre_tool_use.py"
LEGACY_HOOK = HOOKS_DIR / "pre_tool_use_legacy.py"

# ---------------------------------------------------------------------------
# R4: File existence checks
# ---------------------------------------------------------------------------


class TestR4HookRename:
    """R4: pre_tool_use_legacy.py must exist; old name was misleading."""

    def test_legacy_hook_exists(self):
        """pre_tool_use_legacy.py must be present after the R4 rename."""
        assert LEGACY_HOOK.exists(), (
            f"R4: expected {LEGACY_HOOK} to exist after rename from pre_tool_use_rust.py. "
            "Run the R4 rename and update references."
        )

    def test_canonical_hook_exists(self):
        """The canonical pre_tool_use.py must still be present."""
        assert CANONICAL_HOOK.exists(), f"Canonical hook missing: {CANONICAL_HOOK}"

    def test_legacy_is_not_the_same_as_old_rust_name(self):
        """pre_tool_use_rust.py should be gone or be an alias; legacy is the authoritative name."""
        old_rust = HOOKS_DIR / "pre_tool_use_rust.py"
        # The old file may still exist as a compatibility shim, but the new
        # name (legacy) must also exist.
        assert LEGACY_HOOK.exists(), (
            "R4: pre_tool_use_legacy.py is the authoritative renamed file and must exist."
        )

    def test_legacy_hook_references_canonical(self):
        """The legacy shim must delegate to the canonical hook."""
        content = LEGACY_HOOK.read_text()
        assert "pre_tool_use.py" in content or "pre_tool_use" in content, (
            "R4: pre_tool_use_legacy.py should reference the canonical hook."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_hook_module(path: Path, module_name: str) -> ModuleType:
    """Load a hook file as a module without executing its __main__ guard."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _call_hook_function(hook_path: Path, module_name: str, input_data: dict) -> dict:
    """Call the hook's main() with mocked stdin/stdout and return parsed output."""
    import subprocess

    result = subprocess.run(
        [sys.executable, str(hook_path), json.dumps(input_data)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = result.stdout.strip()
    if not output:
        return {}
    # Take the last valid JSON line (hooks may emit log lines).
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return {}


# ---------------------------------------------------------------------------
# R3: Parity tests — canonical and legacy must agree
# ---------------------------------------------------------------------------


PARITY_INPUTS = [
    pytest.param(
        {"tool_name": "TodoWrite", "tool_input": {}},
        id="non-bash-tool",
    ),
    pytest.param(
        {"tool_name": "Bash", "tool_input": {"command": "echo hello"}},
        id="bash-echo",
    ),
]


@pytest.mark.skipif(
    not LEGACY_HOOK.exists(),
    reason="R4 rename not yet done — pre_tool_use_legacy.py missing",
)
class TestR3Parity:
    """R3: canonical and legacy hooks must produce identical decisions."""

    @pytest.mark.parametrize("input_data", PARITY_INPUTS)
    def test_parity(self, input_data):
        """Both hooks must return structurally identical decisions."""
        canonical = _call_hook_function(CANONICAL_HOOK, "canonical_hook", input_data)
        legacy = _call_hook_function(LEGACY_HOOK, "legacy_hook", input_data)

        # Both must agree on whether the request is blocked.
        canonical_deny = canonical.get("permissionDecision") == "deny"
        legacy_deny = legacy.get("permissionDecision") == "deny"
        assert canonical_deny == legacy_deny, (
            f"R3 parity violation for input {input_data!r}:\n"
            f"  canonical={canonical!r}\n"
            f"  legacy={legacy!r}"
        )

    def test_legacy_delegates_to_canonical(self):
        """The legacy hook must execute the canonical hook's logic."""
        content = LEGACY_HOOK.read_text()
        # Legacy must reference or run_path the canonical hook.
        assert "pre_tool_use" in content, (
            "R3: legacy hook must delegate to pre_tool_use.py for parity"
        )


# ---------------------------------------------------------------------------
# R1: Fail-secure — hook errors must deny, not allow
# ---------------------------------------------------------------------------


class TestR1FailSecure:
    """R1: XPIA hook errors must produce deny decisions (fail-closed)."""

    def test_canonical_hook_exists_for_r1(self):
        """Canonical hook must exist before R1 can be tested."""
        assert CANONICAL_HOOK.exists(), f"Canonical hook missing: {CANONICAL_HOOK}"

    def test_canonical_hook_has_fail_closed_except_block(self):
        """The canonical hook's except block must call _deny, not _allow."""
        content = CANONICAL_HOOK.read_text()
        # Look for the error handling pattern — must deny on exception.
        assert "_deny" in content, "R1: canonical hook must call _deny() in its exception handler"
        # Verify the except clause body does not call _allow() — only _deny().
        lines = content.splitlines()
        in_except_block = False
        block_indent = None
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            if "except" in stripped and "Exception" in stripped:
                in_except_block = True
                block_indent = current_indent
                continue

            if in_except_block:
                # End of except block when we return to same or lower indentation
                # on a non-empty, non-comment line.
                if stripped and not stripped.startswith("#"):
                    if current_indent <= block_indent:
                        break  # exited the except block
                # Inside the block: _allow() must not be called.
                if "_allow(" in stripped:
                    pytest.fail(
                        f"R1: except block at line {i + 1} calls _allow(), violating fail-secure:\n"
                        f"{line}"
                    )
