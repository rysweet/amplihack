"""Tests for the SkillInjector."""

from __future__ import annotations

import pytest

from amplihack.agents.domain_agents.skill_injector import (
    SkillInjector,
    code_smell_detector_tool,
    email_draft_tool,
    meeting_notes_tool,
    pr_review_tool,
)


class TestSkillInjector:
    """Test the SkillInjector registry."""

    def test_register_and_retrieve(self):
        injector = SkillInjector()
        injector.register("code_review", "code-smell-detector", lambda x: x)
        skills = injector.get_skills_for_domain("code_review")
        assert "code-smell-detector" in skills

    def test_register_multiple_skills(self):
        injector = SkillInjector()
        injector.register("code_review", "skill-1", lambda: "a")
        injector.register("code_review", "skill-2", lambda: "b")
        skills = injector.get_skills_for_domain("code_review")
        assert len(skills) == 2

    def test_register_different_domains(self):
        injector = SkillInjector()
        injector.register("code_review", "skill-a", lambda: "a")
        injector.register("meeting", "skill-b", lambda: "b")

        cr_skills = injector.get_skills_for_domain("code_review")
        mt_skills = injector.get_skills_for_domain("meeting")
        assert len(cr_skills) == 1
        assert len(mt_skills) == 1
        assert "skill-a" in cr_skills
        assert "skill-b" in mt_skills

    def test_empty_domain_returns_empty(self):
        injector = SkillInjector()
        skills = injector.get_skills_for_domain("")
        assert skills == {}

    def test_nonexistent_domain_returns_empty(self):
        injector = SkillInjector()
        skills = injector.get_skills_for_domain("nonexistent")
        assert skills == {}

    def test_register_empty_domain_raises(self):
        injector = SkillInjector()
        with pytest.raises(ValueError, match="domain cannot be empty"):
            injector.register("", "skill", lambda: None)

    def test_register_empty_skill_name_raises(self):
        injector = SkillInjector()
        with pytest.raises(ValueError, match="skill_name cannot be empty"):
            injector.register("domain", "", lambda: None)

    def test_register_non_callable_raises(self):
        injector = SkillInjector()
        with pytest.raises(ValueError, match="must be callable"):
            injector.register("domain", "skill", "not_callable")

    def test_get_all_domains(self):
        injector = SkillInjector()
        injector.register("code_review", "s1", lambda: None)
        injector.register("meeting", "s2", lambda: None)
        domains = injector.get_all_domains()
        assert set(domains) == {"code_review", "meeting"}

    def test_has_skill(self):
        injector = SkillInjector()
        injector.register("code_review", "detector", lambda: None)
        assert injector.has_skill("code_review", "detector") is True
        assert injector.has_skill("code_review", "other") is False
        assert injector.has_skill("nonexistent", "detector") is False


class TestDefaultSkillTools:
    """Test the default skill tool implementations."""

    def test_code_smell_detector_short_code(self):
        result = code_smell_detector_tool("x = 1\ny = 2\n")
        assert result["smell_count"] == 0

    def test_code_smell_detector_long_function(self):
        long_code = "\n".join([f"    line_{i} = {i}" for i in range(60)])
        code = f"def long_func():\n{long_code}\n"
        result = code_smell_detector_tool(code)
        assert result["smell_count"] >= 1
        smells = result["smells"]
        assert any(s["type"] == "long_function" for s in smells)

    def test_pr_review_tool(self):
        diff = "--- a/file.py\n+++ b/file.py\n+print('debug')\n+x = 1\n-y = 2\n"
        result = pr_review_tool(diff)
        assert result["lines_added"] == 2
        assert result["lines_removed"] == 1
        assert any(f["type"] == "debug_statement" for f in result["findings"])

    def test_meeting_notes_tool(self):
        transcript = "Alice: Hello\nBob: Hi\nAlice: Let's discuss.\n"
        result = meeting_notes_tool(transcript)
        assert result["speaker_count"] == 2
        assert "Alice" in result["speakers"]
        assert "Bob" in result["speakers"]

    def test_email_draft_tool(self):
        result = email_draft_tool("Q1 budget review", "finance team", "formal")
        assert result["to"] == "finance team"
        assert "budget" in result["subject"].lower()
        assert result["tone"] == "formal"
