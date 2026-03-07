#!/usr/bin/env python3
"""
Outside-in tests for skill_invocation power-steering check (from PR #2916).

Verifies that power-steering detects when a user requests a skill via
slash command but the agent bypasses it and responds directly.

Tests cover both Claude and Copilot session patterns.
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

hooks_dir = Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
sys.path.insert(0, str(hooks_dir))

from power_steering_checker.checks_workflow import ChecksWorkflowMixin


class FakeChecker(ChecksWorkflowMixin):
    """Minimal checker to test the mixin method."""

    def __init__(self):
        self._logs = []

    def _log(self, msg, level="INFO", **kwargs):
        self._logs.append((level, msg))


def _transcript_with_skill_requested_and_invoked(skill_name):
    """User requests skill via command-name tag, agent invokes it."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": f"<command-name>{skill_name}</command-name>\n<command-args>do something</command-args>",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Skill",
                        "input": {"skill": skill_name},
                    },
                ],
            },
        },
    ]


def _transcript_with_skill_requested_but_not_invoked(skill_name):
    """User requests skill but agent responds directly without invoking."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": f"<command-name>{skill_name}</command-name>\n<command-args>do something</command-args>",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "I'll help you with that directly without using the skill.",
            },
        },
    ]


def _transcript_without_skill_request():
    """Normal session with no skill request."""
    return [
        {
            "type": "user",
            "message": {"role": "user", "content": "What is the project structure?"},
        },
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": "The project has..."},
        },
    ]


class TestSkillInvocationCheckClaude:
    """Tests simulating Claude sessions."""

    def test_skill_requested_and_invoked_passes(self):
        """When skill is requested and invoked, check passes."""
        checker = FakeChecker()
        transcript = _transcript_with_skill_requested_and_invoked("dev-orchestrator")
        assert checker._check_skill_invocation(transcript, "test") is True

    def test_skill_requested_but_not_invoked_fails(self):
        """When skill is requested but bypassed, check fails."""
        checker = FakeChecker()
        transcript = _transcript_with_skill_requested_but_not_invoked("dev-orchestrator")
        assert checker._check_skill_invocation(transcript, "test") is False

    def test_no_skill_request_auto_passes(self):
        """When no skill is requested, check is not applicable (passes)."""
        checker = FakeChecker()
        transcript = _transcript_without_skill_request()
        assert checker._check_skill_invocation(transcript, "test") is True

    def test_pm_architect_skill_invoked(self):
        """PM-architect skill requested and invoked — should pass."""
        checker = FakeChecker()
        transcript = _transcript_with_skill_requested_and_invoked("pm-architect")
        assert checker._check_skill_invocation(transcript, "test") is True

    def test_pm_architect_skill_bypassed(self):
        """PM-architect requested but agent responds directly — should fail."""
        checker = FakeChecker()
        transcript = _transcript_with_skill_requested_but_not_invoked("pm-architect")
        assert checker._check_skill_invocation(transcript, "test") is False

    def test_command_name_with_leading_slash(self):
        """Command name with leading slash should still match."""
        checker = FakeChecker()
        transcript = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": "<command-name>/dev-orchestrator</command-name>",
                },
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Skill",
                            "input": {"skill": "dev-orchestrator"},
                        },
                    ],
                },
            },
        ]
        assert checker._check_skill_invocation(transcript, "test") is True


class TestSkillInvocationCheckCopilot:
    """Tests simulating Copilot CLI sessions."""

    def test_copilot_skill_invoked(self):
        """Copilot session with skill requested and invoked — passes."""
        checker = FakeChecker()
        transcript = _transcript_with_skill_requested_and_invoked("github-copilot-cli")
        assert checker._check_skill_invocation(transcript, "test") is True

    def test_copilot_skill_bypassed(self):
        """Copilot session with skill bypassed — fails."""
        checker = FakeChecker()
        transcript = _transcript_with_skill_requested_but_not_invoked("github-copilot-cli")
        assert checker._check_skill_invocation(transcript, "test") is False

    def test_copilot_no_skill_request(self):
        """Copilot session without skill request — auto-passes."""
        checker = FakeChecker()
        transcript = _transcript_without_skill_request()
        assert checker._check_skill_invocation(transcript, "test") is True


class TestSkillInvocationEdgeCases:
    """Edge case tests."""

    def test_empty_transcript(self):
        """Empty transcript should pass (no skill requested)."""
        checker = FakeChecker()
        assert checker._check_skill_invocation([], "test") is True

    def test_wrong_skill_invoked(self):
        """User requests skill A but agent invokes skill B — should fail."""
        checker = FakeChecker()
        transcript = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": "<command-name>pm-architect</command-name>",
                },
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Skill",
                            "input": {"skill": "dev-orchestrator"},
                        },
                    ],
                },
            },
        ]
        assert checker._check_skill_invocation(transcript, "test") is False

    def test_namespaced_skill(self):
        """Namespaced skill names (amplihack:dev) should work."""
        checker = FakeChecker()
        transcript = _transcript_with_skill_requested_and_invoked("amplihack:dev")
        assert checker._check_skill_invocation(transcript, "test") is True
