"""Tests for AISkillGenerator."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ...phase2.ai_skill_generator import AISkillGenerator
from ...phase2.skill_validator import SkillValidator


class TestAISkillGenerator:
    """Tests for AISkillGenerator."""

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create mock Anthropic API response."""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = """---
name: test-analyzer
description: Analyzes test results and provides insights
model: inherit
---

You are a test analyzer skill that examines test results.

## Core Capabilities

- Analyze test results
- Identify failure patterns
- Suggest improvements
- Generate analysis reports

## Usage

Use this skill to analyze test suites:

1. Collect test results
2. Analyze patterns
3. Generate insights
4. Recommend actions

## Examples

```python
def analyze_results(test_data):
    return insights
```
"""
        mock_response.content = [mock_content]
        return mock_response

    @pytest.fixture
    def temp_examples_dir(self):
        """Create temporary directory with example skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            examples_dir = Path(tmpdir) / "examples"
            examples_dir.mkdir()

            # Create sample skill file
            (examples_dir / "sample.md").write_text("""---
name: sample-skill
description: Sample skill for testing
model: inherit
---

Sample skill content for few-shot learning.

## Capabilities

- Sample capability 1
- Sample capability 2
""")

            yield examples_dir

    @pytest.fixture
    def generator(self, temp_examples_dir):
        """Create generator instance with mocked API."""
        with patch("anthropic.Anthropic"):
            generator = AISkillGenerator(
                api_key="test_key",
                example_skills_dir=temp_examples_dir,
            )
            return generator

    def test_initialization_with_api_key(self, temp_examples_dir):
        """Test initialization with API key."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            generator = AISkillGenerator(
                api_key="test_key",
                example_skills_dir=temp_examples_dir,
            )

            assert generator.api_key == "test_key"
            assert generator.model == AISkillGenerator.DEFAULT_MODEL
            mock_anthropic.assert_called_once_with(api_key="test_key")

    def test_initialization_without_api_key_raises(self):
        """Test initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                AISkillGenerator()

    def test_initialization_with_env_api_key(self, temp_examples_dir):
        """Test initialization with environment variable API key."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env_key"}):
            with patch("anthropic.Anthropic") as mock_anthropic:
                generator = AISkillGenerator(example_skills_dir=temp_examples_dir)

                assert generator.api_key == "env_key"
                mock_anthropic.assert_called_once_with(api_key="env_key")

    def test_generate_skills(self, generator, mock_anthropic_response):
        """Test generating skills."""
        generator.client.messages.create = MagicMock(
            return_value=mock_anthropic_response
        )

        skills = generator.generate_skills(
            required_capabilities=["analyze"],
            domain="testing",
            validate=False,
        )

        assert len(skills) > 0
        assert skills[0].name
        assert skills[0].content
        assert "analyze" in skills[0].capabilities

    def test_generate_skills_with_validation(self, generator, mock_anthropic_response):
        """Test generating skills with validation."""
        generator.client.messages.create = MagicMock(
            return_value=mock_anthropic_response
        )

        skills = generator.generate_skills(
            required_capabilities=["analyze"],
            domain="testing",
            validate=True,
        )

        assert len(skills) > 0
        assert skills[0].validation_result is not None
        assert isinstance(skills[0].validation_result.passed, bool)

    def test_generate_single_skill(self, generator, mock_anthropic_response):
        """Test generating a single skill."""
        generator.client.messages.create = MagicMock(
            return_value=mock_anthropic_response
        )

        skill = generator._generate_single_skill(
            capability="analyze",
            domain="testing",
            context="Test context",
            examples=[],
            validate=False,
        )

        assert skill is not None
        assert skill.name
        assert skill.content
        assert skill.generation_model == generator.model

    def test_generate_single_skill_with_validation_pass(
        self, generator, mock_anthropic_response
    ):
        """Test generating skill that passes validation."""
        generator.client.messages.create = MagicMock(
            return_value=mock_anthropic_response
        )

        skill = generator._generate_single_skill(
            capability="analyze",
            domain="testing",
            context="",
            examples=[],
            validate=True,
        )

        assert skill is not None
        assert skill.validation_result is not None

    def test_generate_single_skill_api_error(self, generator):
        """Test handling API error during generation."""
        generator.client.messages.create = MagicMock(
            side_effect=Exception("API Error")
        )

        skill = generator._generate_single_skill(
            capability="analyze",
            domain="testing",
            context="",
            examples=[],
            validate=False,
        )

        assert skill is None

    def test_build_generation_prompt(self, generator):
        """Test building generation prompt."""
        prompt = generator._build_generation_prompt(
            capability="analyze",
            domain="testing",
            context="Test context",
            examples=["Example 1"],
        )

        assert "analyze" in prompt.lower()
        assert "testing" in prompt.lower()
        assert "Example 1" in prompt
        assert "---" in prompt  # YAML front matter
        assert "capabilities" in prompt.lower()

    def test_build_generation_prompt_no_examples(self, generator):
        """Test building prompt without examples."""
        prompt = generator._build_generation_prompt(
            capability="test",
            domain="general",
            context="",
            examples=[],
        )

        assert "test" in prompt.lower()
        assert "Example" not in prompt or "example" in prompt.lower()

    def test_load_example_skills(self, generator, temp_examples_dir):
        """Test loading example skills."""
        examples = generator._load_example_skills()

        assert len(examples) > 0
        assert all(isinstance(ex, str) for ex in examples)

    def test_load_example_skills_no_directory(self):
        """Test loading examples when directory doesn't exist."""
        with patch("anthropic.Anthropic"):
            generator = AISkillGenerator(
                api_key="test_key",
                example_skills_dir=Path("/nonexistent"),
            )

            examples = generator._load_example_skills()

            assert len(examples) == 0

    def test_load_example_skills_filters_by_size(self, temp_examples_dir):
        """Test that example loading filters by size."""
        # Create very large file
        (temp_examples_dir / "huge.md").write_text("x" * 10000)

        with patch("anthropic.Anthropic"):
            generator = AISkillGenerator(
                api_key="test_key",
                example_skills_dir=temp_examples_dir,
            )

            examples = generator._load_example_skills()

            # Should not include the huge file
            assert all(len(ex) <= 3000 for ex in examples)

    def test_generate_skill_name(self, generator):
        """Test generating skill names."""
        assert generator._generate_skill_name("analyze") == "analyze-skill"
        assert generator._generate_skill_name("processor") == "processor"
        assert generator._generate_skill_name("test analyzer") == "test-analyzer-skill"
        assert generator._generate_skill_name("data_processor") == "data-processor"

    def test_extract_description_from_frontmatter(self, generator):
        """Test extracting description from YAML front matter."""
        content = """---
name: test-skill
description: This is a test skill
model: inherit
---

Additional content here.
"""

        description = generator._extract_description(content)

        assert "test skill" in description.lower()

    def test_extract_description_from_content(self, generator):
        """Test extracting description from content body."""
        content = """# Test Skill

This is the description of the skill. It does testing.

## More sections

Content here.
"""

        description = generator._extract_description(content)

        assert len(description) > 0
        assert "testing" in description.lower() or "description" in description.lower()

    def test_extract_description_fallback(self, generator):
        """Test description extraction fallback."""
        content = "---\n---\n"

        description = generator._extract_description(content)

        assert description == "AI-generated skill"

    def test_regenerate_failed_skills(self, generator, mock_anthropic_response):
        """Test regenerating failed skills."""
        from ...models import GeneratedSkillDefinition, ValidationResult

        generator.client.messages.create = MagicMock(
            return_value=mock_anthropic_response
        )

        # Create failed skill
        failed_skill = GeneratedSkillDefinition(
            name="failed-skill",
            source_path=Path("test.md"),
            capabilities=["analyze"],
            description="Failed skill",
            content="# Failed",
            generation_model="test-model",
            validation_result=ValidationResult(
                passed=False,
                issues=["Issue 1"],
                quality_score=0.3,
            ),
        )

        regenerated = generator.regenerate_failed_skills([failed_skill])

        assert len(regenerated) > 0

    def test_regenerate_failed_skills_skips_passed(self, generator):
        """Test that regeneration skips already passed skills."""
        from ...models import GeneratedSkillDefinition, ValidationResult

        # Create passed skill
        passed_skill = GeneratedSkillDefinition(
            name="passed-skill",
            source_path=Path("test.md"),
            capabilities=["analyze"],
            description="Passed skill",
            content="# Passed",
            generation_model="test-model",
            validation_result=ValidationResult(
                passed=True,
                issues=[],
                quality_score=0.9,
            ),
        )

        regenerated = generator.regenerate_failed_skills([passed_skill])

        assert len(regenerated) == 0

    def test_generated_skill_definition_model(self):
        """Test GeneratedSkillDefinition model."""
        from ...models import GeneratedSkillDefinition, ValidationResult

        skill = GeneratedSkillDefinition(
            name="test-skill",
            source_path=Path("test.md"),
            capabilities=["test"],
            description="Test skill",
            content="# Test",
            generation_model="claude-3",
            generation_prompt="Generate a test skill",
            validation_result=ValidationResult(passed=True, quality_score=0.9),
        )

        assert skill.name == "test-skill"
        assert skill.generation_model == "claude-3"
        assert skill.provenance == "ai_generated"
        assert skill.validation_result.passed is True

    def test_generated_skill_requires_model(self):
        """Test that generated skill requires generation_model."""
        from ...models import GeneratedSkillDefinition

        with pytest.raises(ValueError, match="generation_model"):
            GeneratedSkillDefinition(
                name="test",
                source_path=Path("test.md"),
                capabilities=["test"],
                description="Test",
                content="# Test",
                generation_model="",  # Empty model
            )

    def test_generate_multiple_capabilities(self, generator, mock_anthropic_response):
        """Test generating skills for multiple capabilities."""
        generator.client.messages.create = MagicMock(
            return_value=mock_anthropic_response
        )

        skills = generator.generate_skills(
            required_capabilities=["analyze", "test", "document"],
            domain="general",
            validate=False,
        )

        # Should generate one skill per capability
        assert len(skills) == 3

    def test_api_call_parameters(self, generator, mock_anthropic_response):
        """Test that API is called with correct parameters."""
        generator.client.messages.create = MagicMock(
            return_value=mock_anthropic_response
        )

        generator.generate_skills(
            required_capabilities=["test"],
            domain="testing",
            validate=False,
        )

        # Verify API call
        generator.client.messages.create.assert_called()
        call_kwargs = generator.client.messages.create.call_args.kwargs

        assert call_kwargs["model"] == generator.model
        assert call_kwargs["max_tokens"] == AISkillGenerator.MAX_TOKENS
        assert "messages" in call_kwargs
