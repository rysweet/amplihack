#!/usr/bin/env python3
"""
Outside-in end-to-end test for OPERATIONS session type (fixes #2913/#2914).

Tests that PM/planning sessions are correctly classified as OPERATIONS
and skip all power-steering checks, simulating real user sessions
with both Claude and Copilot launchers.

Usage:
    uv run pytest tests/outside_in/test_operations_session_e2e.py -v
    # Or standalone:
    python3 tests/outside_in/test_operations_session_e2e.py
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add the hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
sys.path.insert(0, str(hooks_dir))

from power_steering_checker import PowerSteeringChecker


def _make_pm_architect_transcript_claude():
    """Simulate a Claude session with /pm-architect (the actual bug scenario)."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "<command-name>/pm-architect</command-name>\n"
                "<command-args>please survey the project and help determine next steps</command-args>",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me survey the project state."},
                    {
                        "type": "tool_use",
                        "id": "toolu_01",
                        "name": "Bash",
                        "input": {"command": "git log --oneline -20"},
                    },
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_01",
                        "content": "abc123 feat: some feature\ndef456 fix: some fix",
                    }
                ],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Checking open issues and PRs."},
                    {
                        "type": "tool_use",
                        "id": "toolu_02",
                        "name": "Bash",
                        "input": {"command": "gh issue list --limit 20"},
                    },
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_02",
                        "content": "1\tOPEN\tfeat: some feature\n2\tOPEN\tbug: some bug",
                    }
                ],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Reading project structure."},
                    {
                        "type": "tool_use",
                        "id": "toolu_03",
                        "name": "Read",
                        "input": {"file_path": "CLAUDE.md"},
                    },
                    {
                        "type": "tool_use",
                        "id": "toolu_04",
                        "name": "Glob",
                        "input": {"pattern": "**/*.py"},
                    },
                ],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "## Project Health Dashboard\n\n"
                "### Recommended Next Steps\n\n"
                "1. Fix the critical bug\n"
                "2. Review pending PRs\n"
                "3. Update documentation",
            },
        },
    ]


def _make_pm_architect_transcript_copilot():
    """Simulate a Copilot CLI session doing PM work (backlog triage)."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Please triage the backlog and prioritize the open issues for the next sprint",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check the open issues."},
                    {
                        "type": "tool_use",
                        "id": "call_01",
                        "name": "Bash",
                        "input": {"command": "gh issue list --state open --json number,title,labels"},
                    },
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_01",
                        "content": '[{"number":1,"title":"Bug: auth fails","labels":["bug"]}]',
                    }
                ],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Reading project roadmap."},
                    {
                        "type": "tool_use",
                        "id": "call_02",
                        "name": "Read",
                        "input": {"file_path": "docs/ROADMAP.md"},
                    },
                    {
                        "type": "tool_use",
                        "id": "call_03",
                        "name": "Grep",
                        "input": {"pattern": "priority|urgent|blocker", "path": "."},
                    },
                ],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "## Sprint Triage Results\n\n"
                "### Priority 1 (Critical)\n- Bug: auth fails\n\n"
                "### Priority 2 (High)\n- Feature: add logging",
            },
        },
    ]


def _make_development_transcript():
    """Simulate a development session (should NOT be classified as OPERATIONS)."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Implement the JWT authentication module",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Implementing JWT auth."},
                    {
                        "type": "tool_use",
                        "id": "toolu_01",
                        "name": "Write",
                        "input": {"file_path": "src/auth.py", "content": "import jwt\n..."},
                    },
                ],
            },
        },
    ]


class TestOperationsSessionE2EClaude:
    """End-to-end tests simulating Claude sessions."""

    def test_pm_architect_session_classified_as_operations(self):
        """Full /pm-architect session should be OPERATIONS — the original bug."""
        with tempfile.TemporaryDirectory() as tmp:
            checker = PowerSteeringChecker(Path(tmp))
            transcript = _make_pm_architect_transcript_claude()
            session_type = checker.detect_session_type(transcript)
            assert session_type == "OPERATIONS", (
                f"PM session was classified as {session_type}, expected OPERATIONS. "
                "This is the original bug from #2913 — /pm-architect sessions "
                "were being classified as INVESTIGATION due to Read/Grep tool usage."
            )

    def test_pm_architect_session_skips_all_checks(self):
        """OPERATIONS session should have zero applicable considerations."""
        with tempfile.TemporaryDirectory() as tmp:
            checker = PowerSteeringChecker(Path(tmp))
            transcript = _make_pm_architect_transcript_claude()
            session_type = checker.detect_session_type(transcript)
            applicable = checker.get_applicable_considerations(session_type)
            assert len(applicable) == 0, (
                f"OPERATIONS session should skip ALL considerations but got {len(applicable)}: "
                f"{[c['id'] for c in applicable]}"
            )

    def test_pm_architect_full_check_flow(self):
        """Simulate the full check() flow with a PM transcript."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            checker = PowerSteeringChecker(tmp_path)
            transcript = _make_pm_architect_transcript_claude()

            # Write transcript to a file (as the real flow does)
            transcript_path = tmp_path / "transcript.jsonl"
            with open(transcript_path, "w") as f:
                for entry in transcript:
                    f.write(json.dumps(entry) + "\n")

            session_id = "test-pm-session"
            result = checker.check(transcript_path, session_id)

            # OPERATIONS session should approve (not block)
            assert result.decision == "approve", (
                f"PM session check returned {result.decision}, expected approve. "
                f"Reasons: {result.reasons}"
            )


class TestOperationsSessionE2ECopilot:
    """End-to-end tests simulating Copilot CLI sessions."""

    def test_copilot_backlog_triage_classified_as_operations(self):
        """Copilot session with backlog/prioritize keywords → OPERATIONS."""
        with tempfile.TemporaryDirectory() as tmp:
            checker = PowerSteeringChecker(Path(tmp))
            transcript = _make_pm_architect_transcript_copilot()
            session_type = checker.detect_session_type(transcript)
            assert session_type == "OPERATIONS", (
                f"Copilot backlog triage was classified as {session_type}, "
                "expected OPERATIONS"
            )

    def test_copilot_backlog_triage_skips_checks(self):
        """Copilot OPERATIONS session should skip all considerations."""
        with tempfile.TemporaryDirectory() as tmp:
            checker = PowerSteeringChecker(Path(tmp))
            transcript = _make_pm_architect_transcript_copilot()
            session_type = checker.detect_session_type(transcript)
            applicable = checker.get_applicable_considerations(session_type)
            assert len(applicable) == 0

    def test_copilot_backlog_full_check_flow(self):
        """Full check() flow with Copilot backlog triage transcript."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            checker = PowerSteeringChecker(tmp_path)
            transcript = _make_pm_architect_transcript_copilot()

            transcript_path = tmp_path / "transcript.jsonl"
            with open(transcript_path, "w") as f:
                for entry in transcript:
                    f.write(json.dumps(entry) + "\n")

            result = checker.check(transcript_path, "test-copilot-session")
            assert result.decision == "approve", (
                f"Copilot PM session returned {result.decision}. Reasons: {result.reasons}"
            )


class TestDevelopmentSessionNotAffected:
    """Verify development sessions still get full checks."""

    def test_development_session_not_classified_as_operations(self):
        """Pure development session should still be DEVELOPMENT."""
        with tempfile.TemporaryDirectory() as tmp:
            checker = PowerSteeringChecker(Path(tmp))
            transcript = _make_development_transcript()
            session_type = checker.detect_session_type(transcript)
            assert session_type == "DEVELOPMENT", (
                f"Development session was classified as {session_type}, "
                "expected DEVELOPMENT"
            )

    def test_development_session_has_considerations(self):
        """DEVELOPMENT sessions should still have applicable checks."""
        with tempfile.TemporaryDirectory() as tmp:
            checker = PowerSteeringChecker(Path(tmp))
            applicable = checker.get_applicable_considerations("DEVELOPMENT")
            assert len(applicable) > 5, (
                f"DEVELOPMENT should have many considerations, got {len(applicable)}"
            )


if __name__ == "__main__":
    # Run as standalone script for manual verification
    print("=" * 60)
    print("Outside-In Test: OPERATIONS Session Type (#2913/#2914)")
    print("=" * 60)

    failures = 0
    tests = [
        ("Claude /pm-architect → OPERATIONS", TestOperationsSessionE2EClaude().test_pm_architect_session_classified_as_operations),
        ("Claude /pm-architect skips checks", TestOperationsSessionE2EClaude().test_pm_architect_session_skips_all_checks),
        ("Claude full check() flow", TestOperationsSessionE2EClaude().test_pm_architect_full_check_flow),
        ("Copilot backlog triage → OPERATIONS", TestOperationsSessionE2ECopilot().test_copilot_backlog_triage_classified_as_operations),
        ("Copilot backlog triage skips checks", TestOperationsSessionE2ECopilot().test_copilot_backlog_triage_skips_checks),
        ("Copilot full check() flow", TestOperationsSessionE2ECopilot().test_copilot_backlog_full_check_flow),
        ("Dev session still DEVELOPMENT", TestDevelopmentSessionNotAffected().test_development_session_not_classified_as_operations),
        ("Dev session has considerations", TestDevelopmentSessionNotAffected().test_development_session_has_considerations),
    ]

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            print(f"  ❌ {name}: {e}")
            failures += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {len(tests) - failures}/{len(tests)} passed")
    if failures:
        print(f"FAILED: {failures} test(s)")
        sys.exit(1)
    else:
        print("ALL PASSED")
