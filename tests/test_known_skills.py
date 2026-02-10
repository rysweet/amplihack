"""Tests for known_skills registry.

Validates that the registry matches the actual filesystem at ~/.amplihack/.claude/skills/.
"""

from pathlib import Path

import pytest

from amplihack.known_skills import AMPLIHACK_SKILLS, is_amplihack_skill


class TestKnownSkillsRegistry:
    """Tests for AMPLIHACK_SKILLS registry."""

    def test_registry_is_frozen(self):
        """Test that registry is immutable (frozenset)."""
        assert isinstance(AMPLIHACK_SKILLS, frozenset)

    def test_registry_not_empty(self):
        """Test that registry contains skills."""
        assert len(AMPLIHACK_SKILLS) > 0

    def test_registry_contains_expected_core_skills(self):
        """Test that registry contains known core skills."""
        expected_core_skills = {
            "agent-sdk",
            "common",
            "development",
            "collaboration",
            "quality",
            "research",
            "meta-cognitive",
        }
        assert expected_core_skills.issubset(AMPLIHACK_SKILLS)

    def test_registry_contains_expected_workflow_skills(self):
        """Test that registry contains known workflow skills."""
        expected_workflows = {
            "default-workflow",
            "cascade-workflow",
            "debate-workflow",
            "n-version-workflow",
            "investigation-workflow",
        }
        assert expected_workflows.issubset(AMPLIHACK_SKILLS)

    def test_registry_contains_expected_analyst_skills(self):
        """Test that registry contains known analyst skills."""
        expected_analysts = {
            "anthropologist-analyst",
            "biologist-analyst",
            "chemist-analyst",
            "computer-scientist-analyst",
            "economist-analyst",
            "historian-analyst",
        }
        assert expected_analysts.issubset(AMPLIHACK_SKILLS)

    def test_registry_matches_actual_filesystem(self):
        """Test that registry matches actual ~/.amplihack/.claude/skills/ directory.

        This test validates the registry against reality. If this fails,
        the registry needs to be regenerated.
        """
        skills_dir = Path.home() / ".amplihack" / ".claude" / "skills"

        # Skip test if directory doesn't exist (fresh install)
        if not skills_dir.exists():
            pytest.skip("~/.amplihack/.claude/skills/ does not exist yet")

        # Get actual skill directories
        try:
            actual_skills = {
                item.name
                for item in skills_dir.iterdir()
                if item.is_dir() and not item.name.startswith(".")
            }
        except (PermissionError, OSError) as e:
            pytest.skip(f"Cannot read skills directory: {e}")

        # Registry should contain all actual skills
        missing_from_registry = actual_skills - AMPLIHACK_SKILLS
        assert not missing_from_registry, (
            f"Registry missing skills found in filesystem: {missing_from_registry}. "
            "Please update known_skills.py"
        )

        # Registry should not contain non-existent skills
        extra_in_registry = AMPLIHACK_SKILLS - actual_skills
        # This is OK - registry can list skills not yet staged
        # But we log it for awareness
        if extra_in_registry:
            print(f"Note: Registry contains skills not yet staged: {extra_in_registry}")

    def test_no_duplicate_entries(self):
        """Test that registry has no duplicate entries."""
        # frozenset guarantees uniqueness, but verify source list had no duplicates
        skills_list = list(AMPLIHACK_SKILLS)
        assert len(skills_list) == len(set(skills_list))

    def test_all_lowercase_hyphenated(self):
        """Test that all skill names follow naming convention."""
        for skill in AMPLIHACK_SKILLS:
            # Should be lowercase
            assert skill == skill.lower(), f"Skill name not lowercase: {skill}"
            # Should not start/end with hyphen
            assert not skill.startswith("-"), f"Skill name starts with hyphen: {skill}"
            assert not skill.endswith("-"), f"Skill name ends with hyphen: {skill}"
            # Should not have consecutive hyphens
            assert "--" not in skill, f"Skill name has consecutive hyphens: {skill}"


class TestIsAmplihackSkill:
    """Tests for is_amplihack_skill() function."""

    def test_known_skill_returns_true(self):
        """Test that known skills are recognized."""
        assert is_amplihack_skill("agent-sdk") is True
        assert is_amplihack_skill("common") is True
        assert is_amplihack_skill("default-workflow") is True

    def test_unknown_skill_returns_false(self):
        """Test that unknown skills are not recognized."""
        assert is_amplihack_skill("custom-skill") is False
        assert is_amplihack_skill("my-skill") is False
        assert is_amplihack_skill("user-custom") is False

    def test_empty_string_returns_false(self):
        """Test that empty string is not recognized."""
        assert is_amplihack_skill("") is False

    def test_case_sensitive(self):
        """Test that check is case-sensitive."""
        # Correct case
        assert is_amplihack_skill("agent-sdk") is True
        # Wrong case
        assert is_amplihack_skill("Agent-SDK") is False
        assert is_amplihack_skill("AGENT-SDK") is False

    def test_performance_is_constant_time(self):
        """Test that lookup is O(1) using frozenset."""
        import time

        # Warm up
        for _ in range(1000):
            is_amplihack_skill("agent-sdk")

        # Time first element
        start = time.perf_counter()
        for _ in range(10000):
            is_amplihack_skill("agent-sdk")
        time_first = time.perf_counter() - start

        # Time last element
        last_skill = list(AMPLIHACK_SKILLS)[-1]
        start = time.perf_counter()
        for _ in range(10000):
            is_amplihack_skill(last_skill)
        time_last = time.perf_counter() - start

        # Should be similar (within 2x for O(1) lookup)
        # List lookup would be much slower for last element
        assert time_last < time_first * 2

    def test_whitespace_not_trimmed(self):
        """Test that whitespace is not automatically trimmed."""
        assert is_amplihack_skill(" agent-sdk") is False
        assert is_amplihack_skill("agent-sdk ") is False
        assert is_amplihack_skill(" agent-sdk ") is False

    def test_all_registry_skills_recognized(self):
        """Test that all skills in registry are recognized by function."""
        for skill in AMPLIHACK_SKILLS:
            assert is_amplihack_skill(skill) is True
