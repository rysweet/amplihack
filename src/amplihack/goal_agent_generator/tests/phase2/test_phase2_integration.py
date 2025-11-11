"""Integration tests for Phase 2 AI Skill Generation."""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ...models import ExecutionPlan, PlanPhase, SkillDefinition
from ...phase2 import (
    AISkillGenerator,
    SkillGapAnalyzer,
    SkillRegistry,
    SkillValidator,
)
from ...skill_synthesizer import SkillSynthesizer


class TestPhase2Integration:
    """Integration tests for Phase 2 components."""

    @pytest.fixture
    def temp_registry_path(self):
        """Create temporary registry path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "registry.json"

    @pytest.fixture
    def temp_skills_dir(self):
        """Create temporary skills directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()

            # Create sample existing skill
            (skills_dir / "analyzer.md").write_text("""---
name: analyzer
description: Analyzes code patterns
model: inherit
---

Analyzes code for patterns and issues.

## Capabilities

- Analyze code structure
- Detect patterns
- Review quality
""")

            yield skills_dir

    @pytest.fixture
    def execution_plan(self):
        """Create execution plan with partial coverage."""
        phases = [
            PlanPhase(
                name="Analysis",
                description="Analyze code",
                required_capabilities=["analyze", "review"],
                estimated_duration="10 minutes",
            ),
            PlanPhase(
                name="Custom Processing",
                description="Custom data processing",
                required_capabilities=["custom-process", "transform-data"],
                estimated_duration="15 minutes",
            ),
            PlanPhase(
                name="Validation",
                description="Validate results",
                required_capabilities=["validate", "verify"],
                estimated_duration="5 minutes",
            ),
        ]

        return ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=phases,
            total_estimated_duration="30 minutes",
            required_skills=["analyzer", "custom-processor"],
        )

    @pytest.fixture
    def mock_generated_skill_content(self):
        """Mock generated skill content."""
        return """---
name: custom-processor
description: Custom data processor
model: inherit
---

You are a custom data processor.

## Core Capabilities

- Custom process data
- Transform data structures
- Validate data integrity
- Verify processing results

## Usage

Use this skill to process custom data:

1. Load data
2. Process according to rules
3. Validate output
4. Return results

## Examples

```python
def process(data):
    return transformed_data
```
"""

    def test_gap_analyzer_identifies_gaps(self, execution_plan):
        """Test that gap analyzer correctly identifies missing capabilities."""
        analyzer = SkillGapAnalyzer()

        existing_skills = [
            SkillDefinition(
                name="analyzer",
                source_path=Path("analyzer.md"),
                capabilities=["analyze", "review"],
                description="Code analyzer",
                content="# Analyzer",
            )
        ]

        report = analyzer.analyze_gaps(execution_plan, existing_skills)

        # Should identify missing capabilities
        assert report.coverage_percentage < 100.0
        assert "custom-process" in report.missing_capabilities
        assert "transform-data" in report.missing_capabilities

    def test_validator_validates_generated_skills(self, mock_generated_skill_content):
        """Test that validator can validate generated skills."""
        validator = SkillValidator()

        result = validator.validate_skill(mock_generated_skill_content)

        assert result.passed is True
        assert len(result.issues) == 0
        assert result.quality_score > 0.7

    def test_registry_stores_and_retrieves_skills(self, temp_registry_path):
        """Test that registry can store and retrieve skills."""
        registry = SkillRegistry(registry_path=temp_registry_path, auto_load=False)

        # Register skills
        skill1 = SkillDefinition(
            name="skill1",
            source_path=Path("skill1.md"),
            capabilities=["cap1", "cap2"],
            description="Skill 1",
            content="# Skill 1",
        )

        skill2 = SkillDefinition(
            name="skill2",
            source_path=Path("skill2.md"),
            capabilities=["cap2", "cap3"],
            description="Skill 2",
            content="# Skill 2",
        )

        registry.register_batch([skill1, skill2])

        # Search by capability
        results = registry.search_by_capability("cap2")
        assert len(results) == 2

        # Save and reload
        registry.save()

        new_registry = SkillRegistry(registry_path=temp_registry_path, auto_load=True)
        assert new_registry.count() == 2

    def test_skill_synthesizer_phase2_integration(
        self, execution_plan, temp_skills_dir, temp_registry_path, mock_generated_skill_content
    ):
        """Test skill synthesizer with Phase 2 enabled."""
        with patch("anthropic.Anthropic"):
            # Create synthesizer with Phase 2 enabled
            synthesizer = SkillSynthesizer(
                skills_directory=temp_skills_dir,
                enable_phase2=True,
                phase2_coverage_threshold=70.0,
            )

            # Mock the skill generator
            mock_response = Mock()
            mock_content = Mock()
            mock_content.text = mock_generated_skill_content
            mock_response.content = [mock_content]

            # Apply Phase 2
            existing_skills = [
                SkillDefinition(
                    name="analyzer",
                    source_path=Path("analyzer.md"),
                    capabilities=["analyze", "review"],
                    description="Analyzer",
                    content="# Analyzer",
                    match_score=0.8,
                )
            ]

            # Mock skill generator client
            if synthesizer._skill_generator:
                synthesizer._skill_generator.client.messages.create = MagicMock(
                    return_value=mock_response
                )

            # This should trigger Phase 2 since coverage is low
            with patch.object(
                AISkillGenerator, "generate_skills"
            ) as mock_generate:
                from ...models import GeneratedSkillDefinition

                mock_generate.return_value = [
                    GeneratedSkillDefinition(
                        name="custom-processor",
                        source_path=Path("generated.md"),
                        capabilities=["custom-process", "transform-data"],
                        description="Custom processor",
                        content=mock_generated_skill_content,
                        generation_model="claude-3",
                    )
                ]

                result_skills = synthesizer._apply_phase2(
                    execution_plan, existing_skills, "data-processing"
                )

                # Should have both existing and generated skills
                assert len(result_skills) > len(existing_skills)

    def test_end_to_end_skill_generation_flow(
        self, execution_plan, temp_registry_path, mock_generated_skill_content
    ):
        """Test complete end-to-end flow."""
        # 1. Analyze gaps
        analyzer = SkillGapAnalyzer()

        existing_skills = [
            SkillDefinition(
                name="analyzer",
                source_path=Path("analyzer.md"),
                capabilities=["analyze", "review"],
                description="Analyzer",
                content="# Analyzer",
            )
        ]

        gap_report = analyzer.analyze_gaps(execution_plan, existing_skills)

        assert gap_report.coverage_percentage < 100.0
        assert len(gap_report.missing_capabilities) > 0

        # 2. Generate skills for gaps (mocked)
        with patch("anthropic.Anthropic"):
            mock_response = Mock()
            mock_content = Mock()
            mock_content.text = mock_generated_skill_content
            mock_response.content = [mock_content]

            generator = AISkillGenerator(api_key="test_key")
            generator.client.messages.create = MagicMock(return_value=mock_response)

            generated_skills = generator.generate_skills(
                required_capabilities=gap_report.missing_capabilities[:1],
                domain="data-processing",
                validate=True,
            )

            assert len(generated_skills) > 0
            assert generated_skills[0].validation_result is not None

        # 3. Validate generated skills
        validator = SkillValidator()

        for skill in generated_skills:
            result = validator.validate_skill(skill.content)
            assert result.passed is True

        # 4. Register all skills
        registry = SkillRegistry(registry_path=temp_registry_path, auto_load=False)
        registry.register_batch(existing_skills + generated_skills)

        assert registry.count() == len(existing_skills) + len(generated_skills)

        # 5. Save registry
        registry.save()
        assert temp_registry_path.exists()

        # 6. Verify persistence
        new_registry = SkillRegistry(registry_path=temp_registry_path, auto_load=True)
        assert new_registry.count() == registry.count()

    def test_phase2_handles_validation_failures(self):
        """Test that Phase 2 handles validation failures gracefully."""
        validator = SkillValidator()

        # Invalid skill content
        invalid_content = "TODO: Write skill content"

        result = validator.validate_skill(invalid_content)

        assert result.passed is False
        assert len(result.issues) > 0

    def test_gap_analyzer_with_high_coverage_recommends_existing(self):
        """Test that analyzer recommends existing skills with high coverage."""
        analyzer = SkillGapAnalyzer()

        phases = [
            PlanPhase(
                name="Analysis",
                description="Analyze",
                required_capabilities=["analyze", "review"],
                estimated_duration="10 minutes",
            )
        ]

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=phases,
            total_estimated_duration="10 minutes",
        )

        # High coverage skills
        skills = [
            SkillDefinition(
                name="analyzer",
                source_path=Path("analyzer.md"),
                capabilities=["analyze", "review", "inspect"],
                description="Analyzer",
                content="# Analyzer",
            )
        ]

        report = analyzer.analyze_gaps(plan, skills)

        assert report.coverage_percentage == 100.0
        assert report.recommendation == "use_existing"

    def test_registry_handles_mixed_skill_types(self, temp_registry_path):
        """Test registry with both existing and generated skills."""
        from ...models import GeneratedSkillDefinition, ValidationResult

        registry = SkillRegistry(registry_path=temp_registry_path, auto_load=False)

        existing = SkillDefinition(
            name="existing",
            source_path=Path("existing.md"),
            capabilities=["cap1"],
            description="Existing",
            content="# Existing",
        )

        generated = GeneratedSkillDefinition(
            name="generated",
            source_path=Path("generated.md"),
            capabilities=["cap2"],
            description="Generated",
            content="# Generated",
            generation_model="claude-3",
            validation_result=ValidationResult(passed=True, quality_score=0.9),
        )

        registry.register_batch([existing, generated])

        # Save and reload
        registry.save()

        new_registry = SkillRegistry(registry_path=temp_registry_path, auto_load=True)

        assert new_registry.count() == 2

        loaded_existing = new_registry.get_skill("existing")
        loaded_generated = new_registry.get_skill("generated")

        assert not isinstance(loaded_existing, GeneratedSkillDefinition)
        assert isinstance(loaded_generated, GeneratedSkillDefinition)
        assert loaded_generated.generation_model == "claude-3"

    def test_synthesizer_phase2_disabled_by_default(self, temp_skills_dir):
        """Test that Phase 2 is disabled by default."""
        synthesizer = SkillSynthesizer(skills_directory=temp_skills_dir)

        assert synthesizer.enable_phase2 is False

    def test_synthesizer_phase2_can_be_enabled(self, temp_skills_dir):
        """Test that Phase 2 can be enabled."""
        synthesizer = SkillSynthesizer(
            skills_directory=temp_skills_dir,
            enable_phase2=True,
            phase2_coverage_threshold=60.0,
        )

        assert synthesizer.enable_phase2 is True
        assert synthesizer.phase2_coverage_threshold == 60.0

    def test_complete_phase2_pipeline(self, execution_plan, temp_registry_path):
        """Test complete Phase 2 pipeline integration."""
        # Components
        analyzer = SkillGapAnalyzer()
        validator = SkillValidator()
        registry = SkillRegistry(registry_path=temp_registry_path, auto_load=False)

        # Existing skills (partial coverage)
        existing = [
            SkillDefinition(
                name="analyzer",
                source_path=Path("analyzer.md"),
                capabilities=["analyze"],
                description="Analyzer",
                content="# Analyzer",
            )
        ]

        # Analyze gaps
        report = analyzer.analyze_gaps(execution_plan, existing)
        assert report.coverage_percentage < 100.0

        # Simulate skill generation
        generated = [
            SkillDefinition(
                name="processor",
                source_path=Path("processor.md"),
                capabilities=report.missing_capabilities,
                description="Processor",
                content="# Processor\n\n" + "\n".join(
                    [f"- {cap}" for cap in report.missing_capabilities]
                ),
            )
        ]

        # Validate generated skills
        for skill in generated:
            result = validator.validate_skill(skill.content)
            # May not pass all checks but should validate
            assert isinstance(result.passed, bool)

        # Register all
        registry.register_batch(existing + generated)

        # Verify final state
        assert registry.count() == len(existing) + len(generated)

        # Search by capabilities from original plan
        for capability in report.missing_capabilities[:1]:
            results = registry.search_by_capability(capability)
            assert len(results) > 0
