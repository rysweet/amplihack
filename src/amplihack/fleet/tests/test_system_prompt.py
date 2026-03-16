"""Tests for fleet _system_prompt -- SYSTEM_PROMPT_BASE and strategy loading.

Tests the system prompt constants and the strategy dictionary loader.

Testing pyramid:
- 100% unit tests (fast, filesystem mocked where needed)
"""

from __future__ import annotations

from unittest.mock import patch

from amplihack.fleet._system_prompt import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_BASE,
    _load_strategy_dictionary,
)
from amplihack.utils.logging_utils import log_call

# ---------------------------------------------------------------------------
# SYSTEM_PROMPT_BASE
# ---------------------------------------------------------------------------


class TestSystemPromptBase:
    """Tests for the base system prompt constant."""

    @log_call
    def test_is_nonempty_string(self):
        """SYSTEM_PROMPT_BASE is a non-empty string."""
        assert isinstance(SYSTEM_PROMPT_BASE, str)
        assert len(SYSTEM_PROMPT_BASE) > 0

    @log_call
    def test_contains_fleet_admiral_section(self):
        """Prompt mentions 'Fleet Admiral' role."""
        assert "Fleet Admiral" in SYSTEM_PROMPT_BASE

    @log_call
    def test_contains_action_options(self):
        """Prompt lists the five action options."""
        assert "SEND_INPUT" in SYSTEM_PROMPT_BASE
        assert "WAIT" in SYSTEM_PROMPT_BASE
        assert "ESCALATE" in SYSTEM_PROMPT_BASE
        assert "MARK_COMPLETE" in SYSTEM_PROMPT_BASE
        assert "RESTART" in SYSTEM_PROMPT_BASE

    @log_call
    def test_contains_json_format(self):
        """Prompt includes the expected JSON response format."""
        assert '"action"' in SYSTEM_PROMPT_BASE
        assert '"reasoning"' in SYSTEM_PROMPT_BASE
        assert '"confidence"' in SYSTEM_PROMPT_BASE

    @log_call
    def test_contains_thinking_detection(self):
        """Prompt includes thinking-detection guidance."""
        assert "Thinking Detection" in SYSTEM_PROMPT_BASE

    @log_call
    def test_contains_safety_guidelines(self):
        """Prompt includes safety guidelines (no destructive operations)."""
        assert "destructive" in SYSTEM_PROMPT_BASE.lower()


# ---------------------------------------------------------------------------
# _load_strategy_dictionary
# ---------------------------------------------------------------------------


class TestLoadStrategyDictionary:
    """Tests for the strategy dictionary loader."""

    @log_call
    def test_returns_string(self):
        """_load_strategy_dictionary always returns a string."""
        result = _load_strategy_dictionary()
        assert isinstance(result, str)

    @log_call
    def test_returns_empty_when_file_missing(self, tmp_path):
        """Returns empty string when STRATEGY_DICTIONARY.md does not exist."""
        # Point _load_strategy_dictionary at a directory with no strategy file
        fake_module = tmp_path / "_system_prompt.py"
        fake_module.write_text("")
        with patch("amplihack.fleet._system_prompt.__file__", str(fake_module)):
            result = _load_strategy_dictionary()
            assert result == ""

    @log_call
    def test_extracts_strategy_index_section(self, tmp_path):
        """Extracts STRATEGY INDEX section from file content."""
        fake_content = (
            "# Strategy Dictionary\n"
            "## STRATEGY INDEX\n"
            "- S1: Wait patiently\n"
            "- S2: Send guidance\n"
            "## STRATEGIES\n"
            "### S1: Wait patiently\n"
            "Full details here...\n"
            "## DECISION QUICK-REFERENCE\n"
            "| Situation | Action |\n"
            "| stuck | escalate |\n"
        )
        strategy_file = tmp_path / "STRATEGY_DICTIONARY.md"
        strategy_file.write_text(fake_content)
        fake_module = tmp_path / "_system_prompt.py"
        fake_module.write_text("")
        with patch("amplihack.fleet._system_prompt.__file__", str(fake_module)):
            result = _load_strategy_dictionary()
            assert "STRATEGY INDEX" in result
            assert "S1: Wait patiently" in result
            assert "DECISION QUICK-REFERENCE" in result

    @log_call
    def test_excludes_full_strategy_details(self, tmp_path):
        """Excludes content between ## STRATEGIES and DECISION QUICK-REFERENCE."""
        fake_content = (
            "## STRATEGY INDEX\n"
            "- S1: Wait\n"
            "## STRATEGIES\n"
            "FULL DETAIL SHOULD NOT APPEAR\n"
            "## DECISION QUICK-REFERENCE\n"
            "Quick ref content\n"
        )
        strategy_file = tmp_path / "STRATEGY_DICTIONARY.md"
        strategy_file.write_text(fake_content)
        fake_module = tmp_path / "_system_prompt.py"
        fake_module.write_text("")
        with patch("amplihack.fleet._system_prompt.__file__", str(fake_module)):
            result = _load_strategy_dictionary()
            assert "FULL DETAIL SHOULD NOT APPEAR" not in result

    @log_call
    def test_returns_empty_when_no_sections_found(self, tmp_path):
        """Returns empty string when file exists but has no matching sections."""
        fake_content = "# Just some random content\nNo strategy sections here.\n"
        strategy_file = tmp_path / "STRATEGY_DICTIONARY.md"
        strategy_file.write_text(fake_content)
        fake_module = tmp_path / "_system_prompt.py"
        fake_module.write_text("")
        with patch("amplihack.fleet._system_prompt.__file__", str(fake_module)):
            result = _load_strategy_dictionary()
            assert result == ""


# ---------------------------------------------------------------------------
# SYSTEM_PROMPT (combined)
# ---------------------------------------------------------------------------


class TestSystemPromptCombined:
    """Tests for the final SYSTEM_PROMPT that combines base + strategy."""

    @log_call
    def test_is_nonempty_string(self):
        """SYSTEM_PROMPT is a non-empty string."""
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    @log_call
    def test_starts_with_base_prompt(self):
        """SYSTEM_PROMPT begins with the base prompt content."""
        assert SYSTEM_PROMPT.startswith(SYSTEM_PROMPT_BASE)

    @log_call
    def test_at_least_as_long_as_base(self):
        """SYSTEM_PROMPT is >= SYSTEM_PROMPT_BASE (may include strategy)."""
        assert len(SYSTEM_PROMPT) >= len(SYSTEM_PROMPT_BASE)
