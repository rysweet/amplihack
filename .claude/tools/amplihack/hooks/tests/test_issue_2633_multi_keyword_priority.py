#!/usr/bin/env python3
"""
Tests for Issue #2633: detect_session_type keyword priority for multi-keyword inputs.

Documents and verifies the implicit priority order when a user message contains
keywords from multiple session types. The priority order in detect_session_type is:

    1. Environment override (AMPLIHACK_SESSION_TYPE env var)
    2. SIMPLE keywords (cleanup, fetch, sync, workspace) - highest keyword priority
    3. DEVELOPMENT signals (code file modifications, test executions, PR create/edit)
    4. INVESTIGATION keywords (investigate, analyze, debug, etc.) - only without code mods
    5. INFORMATIONAL indicators (questions without tool usage)
    6. INVESTIGATION tool patterns (Read/Grep without Write/Edit)
    7. MAINTENANCE indicators (doc/config-only modifications)
    8. Default: INFORMATIONAL (fail-open)

Key insight: SIMPLE keywords are checked BEFORE tool analysis, so they always win.
DEVELOPMENT is determined by tool usage (code changes), not keywords.
INVESTIGATION keywords only apply when there are NO code modifications.
"""

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_msg(content: str) -> dict:
    """Create a user message dict for transcripts."""
    return {"type": "user", "message": {"content": content}}


def _assistant_text(text: str) -> dict:
    """Create an assistant text-only message (no tool use)."""
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _assistant_write_code(file_path: str) -> dict:
    """Create an assistant message with a Write tool call to a code file."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {"file_path": file_path},
                }
            ]
        },
    }


def _assistant_edit_code(file_path: str) -> dict:
    """Create an assistant message with an Edit tool call to a code file."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Edit",
                    "input": {
                        "file_path": file_path,
                        "old_string": "old",
                        "new_string": "new",
                    },
                }
            ]
        },
    }


def _assistant_write_doc(file_path: str) -> dict:
    """Create an assistant message with a Write tool call to a doc file."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {"file_path": file_path},
                }
            ]
        },
    }


def _assistant_read(file_path: str) -> dict:
    """Create an assistant message with a Read tool call."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": file_path},
                }
            ]
        },
    }


def _assistant_test(command: str = "pytest tests/") -> dict:
    """Create an assistant message with a Bash test execution."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Bash",
                    "input": {"command": command},
                }
            ]
        },
    }


@pytest.fixture
def checker():
    """Create a PowerSteeringChecker instance for testing."""
    return PowerSteeringChecker()


# ===========================================================================
# Test Class: Multi-Keyword Priority
# ===========================================================================

class TestMultiKeywordPriority:
    """Tests that verify priority ordering when messages contain keywords
    from multiple session types.

    Priority (highest to lowest):
        SIMPLE > DEVELOPMENT (tool-based) > INVESTIGATION (keyword) >
        INFORMATIONAL > MAINTENANCE > INFORMATIONAL (default)
    """

    # -----------------------------------------------------------------------
    # SIMPLE keyword priority (highest among keyword-based checks)
    # -----------------------------------------------------------------------

    def test_simple_keyword_beats_investigation_keyword(self, checker):
        """SIMPLE keywords take priority over INVESTIGATION keywords.

        Message contains both 'cleanup' (SIMPLE) and 'investigate' (INVESTIGATION).
        SIMPLE is checked first in detect_session_type, so it wins.
        """
        transcript = [
            _user_msg("cleanup the workspace and investigate the failing tests"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", (
            f"Expected SIMPLE (cleanup keyword has highest keyword priority), "
            f"got {session_type}"
        )

    def test_simple_keyword_beats_development_keywords(self, checker):
        """SIMPLE keywords take priority even when development-like language is present.

        'git pull' is a SIMPLE keyword; 'implement' is development language.
        Without actual code-modifying tool usage, SIMPLE wins.
        """
        transcript = [
            _user_msg("git pull and then implement the new feature"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", (
            f"Expected SIMPLE ('git pull' is a SIMPLE keyword checked before tool analysis), "
            f"got {session_type}"
        )

    def test_simple_keyword_beats_question_marks(self, checker):
        """SIMPLE keywords take priority over question indicators.

        A question containing a SIMPLE keyword should still classify as SIMPLE,
        not INFORMATIONAL.
        """
        transcript = [
            _user_msg("can you cleanup the workspace?"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", (
            f"Expected SIMPLE ('cleanup' keyword overrides question indicator), "
            f"got {session_type}"
        )

    # -----------------------------------------------------------------------
    # DEVELOPMENT priority (tool-based, overrides investigation keywords)
    # -----------------------------------------------------------------------

    def test_code_changes_beat_investigation_keywords(self, checker):
        """Code modifications override investigation keywords.

        User says 'investigate' but assistant actually modifies code files.
        Tool evidence (code changes) is stronger than keywords.
        """
        transcript = [
            _user_msg("investigate the bug and fix it"),
            _assistant_edit_code("src/module.py"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"Expected DEVELOPMENT (code modifications override investigation keywords), "
            f"got {session_type}"
        )

    def test_test_execution_beats_investigation_keywords(self, checker):
        """Test execution signals DEVELOPMENT even with investigation keywords.

        Running pytest is a DEVELOPMENT signal that overrides 'analyze' keyword.
        """
        transcript = [
            _user_msg("analyze the test failures and debug them"),
            _assistant_test("pytest tests/ -v"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"Expected DEVELOPMENT (test execution overrides investigation keywords), "
            f"got {session_type}"
        )

    def test_pr_creation_beats_investigation_keywords(self, checker):
        """PR creation signals DEVELOPMENT even with investigation keywords.

        'gh pr create' is a development operation that overrides 'research' keyword.
        """
        transcript = [
            _user_msg("research the issue and create a PR with the fix"),
            _assistant_text("I'll research and create the PR."),
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "gh pr create --title 'Fix issue'"},
                        }
                    ]
                },
            },
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"Expected DEVELOPMENT (PR creation overrides investigation keywords), "
            f"got {session_type}"
        )

    # -----------------------------------------------------------------------
    # INVESTIGATION keyword priority (when no code modifications)
    # -----------------------------------------------------------------------

    def test_investigation_keyword_without_code_changes(self, checker):
        """Investigation keywords classify as INVESTIGATION when no code is modified.

        Pure investigation with only Read/text responses.
        """
        transcript = [
            _user_msg("investigate why the auth module is slow"),
            _assistant_text("I'll investigate the auth module performance."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"Expected INVESTIGATION (keyword present, no code modifications), "
            f"got {session_type}"
        )

    def test_investigation_keyword_with_doc_changes_stays_investigation(self, checker):
        """Investigation keywords win even if docs are modified.

        Writing investigation notes to a markdown file is still INVESTIGATION,
        not MAINTENANCE, because the investigation keyword takes priority.
        """
        transcript = [
            _user_msg("investigate the memory leak and document findings"),
            _assistant_write_doc("docs/investigation-notes.md"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"Expected INVESTIGATION (keyword priority over doc-only maintenance), "
            f"got {session_type}"
        )

    def test_multiple_investigation_keywords(self, checker):
        """Multiple investigation keywords still classify as INVESTIGATION."""
        transcript = [
            _user_msg("analyze and debug the root cause of the failure"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"Expected INVESTIGATION (multiple investigation keywords), "
            f"got {session_type}"
        )

    # -----------------------------------------------------------------------
    # Default / no-keyword classification
    # -----------------------------------------------------------------------

    def test_no_keywords_with_code_changes_is_development(self, checker):
        """Without classification keywords, code changes -> DEVELOPMENT."""
        transcript = [
            _user_msg("add a new endpoint for user profiles"),
            _assistant_write_code("src/endpoints/profile.py"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"Expected DEVELOPMENT (code modifications without keywords), "
            f"got {session_type}"
        )

    def test_no_keywords_no_tools_defaults_to_informational(self, checker):
        """Without keywords or tool usage, defaults to INFORMATIONAL."""
        transcript = [
            _user_msg("tell me about the architecture"),
            _assistant_text("The architecture is based on modular design."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INFORMATIONAL", (
            f"Expected INFORMATIONAL (no keywords, no tool usage, default), "
            f"got {session_type}"
        )

    def test_empty_transcript_is_informational(self, checker):
        """Empty transcript defaults to INFORMATIONAL (fail-open)."""
        session_type = checker.detect_session_type([])
        assert session_type == "INFORMATIONAL", (
            f"Expected INFORMATIONAL (empty transcript, fail-open default), "
            f"got {session_type}"
        )

    # -----------------------------------------------------------------------
    # Environment override (highest overall priority)
    # -----------------------------------------------------------------------

    def test_env_override_beats_all_keywords(self, checker, monkeypatch):
        """Environment variable AMPLIHACK_SESSION_TYPE overrides all heuristics.

        Even with SIMPLE keywords present, env var takes precedence.
        """
        monkeypatch.setenv("AMPLIHACK_SESSION_TYPE", "INVESTIGATION")
        transcript = [
            _user_msg("cleanup the workspace"),  # Would be SIMPLE normally
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"Expected INVESTIGATION (env override), got {session_type}"
        )

    def test_env_override_development(self, checker, monkeypatch):
        """Env override to DEVELOPMENT works regardless of message content."""
        monkeypatch.setenv("AMPLIHACK_SESSION_TYPE", "DEVELOPMENT")
        transcript = [
            _user_msg("explain how the auth module works?"),  # Would be INFORMATIONAL
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"Expected DEVELOPMENT (env override), got {session_type}"
        )

    # -----------------------------------------------------------------------
    # Combined multi-keyword edge cases
    # -----------------------------------------------------------------------

    def test_simple_and_investigation_and_question(self, checker):
        """Message with SIMPLE + INVESTIGATION keywords + question mark.

        SIMPLE has the highest keyword priority.
        """
        transcript = [
            _user_msg("can you cleanup and investigate why tests fail?"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", (
            f"Expected SIMPLE (highest keyword priority even with investigation + question), "
            f"got {session_type}"
        )

    def test_investigation_keyword_overridden_by_subsequent_code_changes(self, checker):
        """Investigation keyword in first message, but code changes happen later.

        Code modifications are checked after SIMPLE keywords but take priority
        over investigation keywords because they represent concrete evidence.
        """
        transcript = [
            _user_msg("investigate the auth bug"),
            _assistant_read("src/auth.py"),
            _user_msg("ok fix it"),
            _assistant_edit_code("src/auth.py"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"Expected DEVELOPMENT (code changes override earlier investigation keyword), "
            f"got {session_type}"
        )

    def test_investigation_keyword_with_only_read_operations(self, checker):
        """Investigation keyword + Read-only tool usage -> INVESTIGATION.

        Read operations without modifications are investigation signals, not development.
        """
        transcript = [
            _user_msg("analyze the codebase structure"),
            _assistant_read("src/main.py"),
            _assistant_read("src/config.py"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"Expected INVESTIGATION (keywords + Read-only tools), "
            f"got {session_type}"
        )

    def test_development_language_without_tools_not_development(self, checker):
        """Development-like language without tool usage does not classify as DEVELOPMENT.

        Words like 'implement', 'build', 'create' are not checked as keywords.
        Without actual code-modifying tools, the classification falls through.
        """
        transcript = [
            _user_msg("implement a new caching layer"),
            _assistant_text("I'll implement the caching layer."),
        ]
        session_type = checker.detect_session_type(transcript)
        # Without tool usage and without investigation keywords,
        # this falls through to INFORMATIONAL (the default)
        assert session_type == "INFORMATIONAL", (
            f"Expected INFORMATIONAL (no tool usage, no matching keywords -> default), "
            f"got {session_type}"
        )


# ===========================================================================
# Test Class: Individual Keyword Helper Methods
# ===========================================================================

class TestKeywordHelperMethods:
    """Tests for _has_simple_task_keywords and _has_investigation_keywords
    helper methods directly."""

    def test_has_simple_task_keywords_finds_cleanup(self, checker):
        """_has_simple_task_keywords detects 'cleanup' in user messages."""
        transcript = [_user_msg("cleanup the workspace")]
        assert checker._has_simple_task_keywords(transcript) is True

    def test_has_simple_task_keywords_finds_git_pull(self, checker):
        """_has_simple_task_keywords detects 'git pull' in user messages."""
        transcript = [_user_msg("git pull from upstream")]
        assert checker._has_simple_task_keywords(transcript) is True

    def test_has_simple_task_keywords_negative(self, checker):
        """_has_simple_task_keywords returns False for non-simple messages."""
        transcript = [_user_msg("implement a new feature")]
        assert checker._has_simple_task_keywords(transcript) is False

    def test_has_simple_task_keywords_empty_transcript(self, checker):
        """_has_simple_task_keywords returns False for empty transcript."""
        assert checker._has_simple_task_keywords([]) is False

    def test_has_investigation_keywords_finds_investigate(self, checker):
        """_has_investigation_keywords detects 'investigate' in user messages."""
        transcript = [_user_msg("investigate the failing CI pipeline")]
        assert checker._has_investigation_keywords(transcript) is True

    def test_has_investigation_keywords_finds_debug(self, checker):
        """_has_investigation_keywords detects 'debug' in user messages."""
        transcript = [_user_msg("debug the memory leak")]
        assert checker._has_investigation_keywords(transcript) is True

    def test_has_investigation_keywords_finds_analyze(self, checker):
        """_has_investigation_keywords detects 'analyze' in user messages."""
        transcript = [_user_msg("analyze the performance bottleneck")]
        assert checker._has_investigation_keywords(transcript) is True

    def test_has_investigation_keywords_finds_partial_match(self, checker):
        """_has_investigation_keywords uses substring matching for 'diagnos'."""
        transcript = [_user_msg("diagnosing the network issue")]
        assert checker._has_investigation_keywords(transcript) is True

    def test_has_investigation_keywords_negative(self, checker):
        """_has_investigation_keywords returns False for non-investigation messages."""
        transcript = [_user_msg("add a new REST endpoint")]
        assert checker._has_investigation_keywords(transcript) is False

    def test_has_investigation_keywords_empty_transcript(self, checker):
        """_has_investigation_keywords returns False for empty transcript."""
        assert checker._has_investigation_keywords([]) is False

    def test_simple_keywords_case_insensitive(self, checker):
        """Keyword matching is case-insensitive (content is lowered)."""
        transcript = [_user_msg("CLEANUP the workspace")]
        assert checker._has_simple_task_keywords(transcript) is True

    def test_investigation_keywords_case_insensitive(self, checker):
        """Investigation keyword matching is case-insensitive."""
        transcript = [_user_msg("INVESTIGATE the issue")]
        assert checker._has_investigation_keywords(transcript) is True


# ===========================================================================
# Test Class: Priority Documentation Verification
# ===========================================================================

class TestPriorityDocumentation:
    """Verify that the documented priority in detect_session_type docstring
    matches the actual implementation behavior.

    The docstring states (Issue #2196 update):
        1. Environment override (AMPLIHACK_SESSION_TYPE)
        2. Simple task keywords - highest priority heuristic
        3. Tool usage patterns (code changes, tests) - CONCRETE EVIDENCE
        4. Investigation keywords - TIEBREAKER ONLY (when no code changes)

    These tests confirm each priority level.
    """

    def test_priority_1_env_override(self, checker, monkeypatch):
        """Priority 1: Environment override beats everything."""
        monkeypatch.setenv("AMPLIHACK_SESSION_TYPE", "MAINTENANCE")
        # Transcript has SIMPLE keyword + code changes + investigation keyword
        transcript = [
            _user_msg("cleanup and investigate the bugs"),
            _assistant_write_code("src/fix.py"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "MAINTENANCE", (
            f"Priority 1 violated: env override should beat all heuristics, got {session_type}"
        )

    def test_priority_2_simple_keywords(self, checker):
        """Priority 2: SIMPLE keywords beat tool patterns and investigation keywords."""
        # Has investigation keyword AND would have tool-based signals
        transcript = [
            _user_msg("fetch the latest and investigate the failures"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "SIMPLE", (
            f"Priority 2 violated: SIMPLE keywords should beat investigation keywords, "
            f"got {session_type}"
        )

    def test_priority_3_tool_patterns_beat_investigation_keywords(self, checker):
        """Priority 3: Code modification tools beat investigation keywords."""
        transcript = [
            _user_msg("analyze and fix the authentication bug"),
            _assistant_edit_code("src/auth.py"),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "DEVELOPMENT", (
            f"Priority 3 violated: tool patterns should beat investigation keywords, "
            f"got {session_type}"
        )

    def test_priority_4_investigation_keywords_as_tiebreaker(self, checker):
        """Priority 4: Investigation keywords apply only without code changes."""
        transcript = [
            _user_msg("analyze the system architecture"),
            _assistant_text("The architecture uses a modular design."),
        ]
        session_type = checker.detect_session_type(transcript)
        assert session_type == "INVESTIGATION", (
            f"Priority 4 violated: investigation keywords should classify when "
            f"no code changes present, got {session_type}"
        )
