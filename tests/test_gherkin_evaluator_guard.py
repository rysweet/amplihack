"""Tests for gherkin_agent_evaluator Anthropic guard behaviour.

Covers:
- ANTHROPIC_DISABLED=true causes _has_anthropic_api_key to return False
- Key present + not disabled returns True
- Disabled flag emits a log.warning containing the flag name

The module is loaded directly via importlib to avoid triggering
amplihack.eval.__init__, which requires the optional amplihack-agent-eval
sibling package.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Direct-file loader (avoids amplihack.eval.__init__ ImportError)
# ---------------------------------------------------------------------------

_GHE_PATH = (
    Path(__file__).parents[1]
    / "src/amplihack/eval/gherkin_agent_evaluator.py"
)


def _load_ghe():
    """Load gherkin_agent_evaluator without going through the package __init__."""
    mod_key = "amplihack.eval.gherkin_agent_evaluator"
    sys.modules.pop(mod_key, None)

    # Stub amplihack.eval so Python doesn't execute its __init__
    eval_pkg_key = "amplihack.eval"
    if eval_pkg_key not in sys.modules:
        sys.modules[eval_pkg_key] = MagicMock()

    # Stub tla_prompt_experiment so the module-level import resolves
    tla_key = "amplihack.eval.tla_prompt_experiment"
    if tla_key not in sys.modules:
        tla_stub = MagicMock()
        tla_stub.ConditionMetrics = MagicMock(return_value=MagicMock(to_dict=lambda: {}))
        sys.modules[tla_key] = tla_stub

    spec = importlib.util.spec_from_file_location(mod_key, str(_GHE_PATH))
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Register BEFORE exec so @dataclass can look up cls.__module__
    sys.modules[mod_key] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHasAnthropicApiKey:
    """Tests for the _has_anthropic_api_key helper."""

    def test_returns_true_when_key_present(self, monkeypatch):
        """Returns True when ANTHROPIC_API_KEY is set and not disabled."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        monkeypatch.delenv("ANTHROPIC_DISABLED", raising=False)
        ghe = _load_ghe()
        assert ghe._has_anthropic_api_key() is True

    def test_returns_false_when_key_absent(self, monkeypatch):
        """Returns False when ANTHROPIC_API_KEY is unset."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_DISABLED", raising=False)
        ghe = _load_ghe()
        assert ghe._has_anthropic_api_key() is False

    def test_returns_false_when_disabled_flag_set(self, monkeypatch):
        """Returns False when ANTHROPIC_DISABLED=true even if key is present."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        monkeypatch.setenv("ANTHROPIC_DISABLED", "true")
        ghe = _load_ghe()
        assert ghe._has_anthropic_api_key() is False

    def test_disabled_flag_case_insensitive(self, monkeypatch):
        """ANTHROPIC_DISABLED=TRUE also disables Anthropic."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        monkeypatch.setenv("ANTHROPIC_DISABLED", "TRUE")
        ghe = _load_ghe()
        assert ghe._has_anthropic_api_key() is False

    def test_disabled_flag_emits_warning(self, monkeypatch, caplog):
        """ANTHROPIC_DISABLED=true emits a log.warning with the flag name."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        monkeypatch.setenv("ANTHROPIC_DISABLED", "true")
        ghe = _load_ghe()
        with caplog.at_level(logging.WARNING):
            ghe._has_anthropic_api_key()
        assert "ANTHROPIC_DISABLED" in caplog.text
