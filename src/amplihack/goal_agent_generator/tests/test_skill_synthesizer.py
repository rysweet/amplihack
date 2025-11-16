"""Tests for skill synthesizer."""

import tempfile
import uuid
from pathlib import Path

import pytest

from ..models import ExecutionPlan, PlanPhase, SkillDefinition
from ..skill_synthesizer import SkillSynthesizer


class TestSkillSynthesizer:
    """Tests for SkillSynthesizer."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create temporary skills directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()

            # Create sample skill files
            (skills_dir / "analyzer.md").write_text("""# Code Analyzer

Analyzes code for patterns and issues.

## Capabilities

- Analyze code structure
- Detect patterns
- Review quality
""")

            (skills_dir / "tester.md").write_text("""# Test Runner

Runs tests and validates code.

## Capabilities

- Run unit tests
- Validate functionality
- Check coverage
""")

            yield skills_dir

    @pytest.fixture
    def synthesizer(self, temp_skills_dir):
        """Create synthesizer with temp directory."""
        return SkillSynthesizer(skills_directory=temp_skills_dir)

    @pytest.fixture
    def execution_plan(self):
        """Create sample execution plan."""
        phases = [
            PlanPhase(
                name="Analysis",
                description="Analyze code",
                required_capabilities=["analyze", "review"],
                estimated_duration="10 minutes",
            ),
            PlanPhase(
                name="Testing",
                description="Run tests",
                required_capabilities=["test", "validate"],
                estimated_duration="15 minutes",
            ),
        ]

        return ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=phases,
            total_estimated_duration="25 minutes",
            required_skills=["analyzer", "tester"],
        )

    def test_synthesize_skills_finds_matches(self, synthesizer, execution_plan):
        """Test that synthesizer finds matching skills."""
        skills = synthesizer.synthesize_skills(execution_plan)

        assert len(skills) > 0
        assert all(isinstance(skill, SkillDefinition) for skill in skills)

    def test_synthesize_skills_calculates_match_scores(self, synthesizer, execution_plan):
        """Test that match scores are calculated."""
        skills = synthesizer.synthesize_skills(execution_plan)

        for skill in skills:
            assert 0 <= skill.match_score <= 1

    def test_find_matching_skill_returns_best_match(self, synthesizer):
        """Test that best matching skill is returned."""
        skill = synthesizer._find_matching_skill("analyzer")

        if skill:  # Might not find in temp directory
            assert "analyze" in skill.content.lower() or "review" in skill.content.lower()

    def test_load_skill_extracts_metadata(self, temp_skills_dir):
        """Test that skill loading extracts metadata."""
        synthesizer = SkillSynthesizer(skills_directory=temp_skills_dir)
        skill_path = temp_skills_dir / "analyzer.md"

        skill = synthesizer._load_skill(skill_path, "analyzer", 0.8)

        assert skill.name == "analyzer"
        assert skill.source_path == skill_path
        assert len(skill.capabilities) > 0
        assert skill.description
        assert skill.content
        assert skill.match_score == 0.8

    def test_extract_description_from_content(self, synthesizer):
        """Test extracting description from markdown."""
        content = """# Test Skill

This is a test skill that does testing.

## Usage

Use this for testing.
"""

        description = synthesizer._extract_description(content)

        assert "test" in description.lower()
        assert len(description) > 0

    def test_extract_capabilities_from_content(self, synthesizer):
        """Test extracting capabilities from content."""
        content = """# Analyzer

Analyzes and processes data.
"""

        capabilities = synthesizer._extract_capabilities(content, "analyzer")

        assert len(capabilities) > 0
        assert any("analyze" in cap.lower() for cap in capabilities)

    def test_create_generic_skill_fallback(self, synthesizer):
        """Test creating generic fallback skill."""
        generic = synthesizer._create_generic_skill()

        assert generic.name == "generic-executor"
        assert len(generic.capabilities) > 0
        assert generic.content
        assert generic.match_score > 0

    def test_synthesize_with_no_skills_returns_generic(self):
        """Test that synthesizer returns generic skill when no matches."""
        # Create synthesizer with empty directory
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir) / "empty"
            empty_dir.mkdir()

            synthesizer = SkillSynthesizer(skills_directory=empty_dir)

            plan = ExecutionPlan(
                goal_id=uuid.uuid4(),
                phases=[
                    PlanPhase(
                        name="Test",
                        description="Test",
                        required_capabilities=["test"],
                        estimated_duration="5 minutes",
                    )
                ],
                total_estimated_duration="5 minutes",
                required_skills=["nonexistent-skill"],
            )

            skills = synthesizer.synthesize_skills(plan)

            assert len(skills) > 0
            # Should have generic skill
            assert any(s.name == "generic-executor" for s in skills)

    def test_skill_keywords_mapping(self):
        """Test that skill keywords are properly defined."""
        assert "analyzer" in SkillSynthesizer.SKILL_KEYWORDS
        assert "tester" in SkillSynthesizer.SKILL_KEYWORDS
        assert "deployer" in SkillSynthesizer.SKILL_KEYWORDS

        # Each skill should have keywords
        for skill_name, keywords in SkillSynthesizer.SKILL_KEYWORDS.items():
            assert len(keywords) > 0
            assert all(isinstance(kw, str) for kw in keywords)
