"""
AI Skill Generator - Generates custom skills using Claude SDK.

Uses few-shot prompting with existing skills as examples to generate
high-quality skill markdown following amplihack format.
"""

import os
from pathlib import Path
from typing import List, Optional

from anthropic import Anthropic

from ..models import GeneratedSkillDefinition, ValidationResult
from .skill_validator import SkillValidator


class AISkillGenerator:
    """Generates custom skills using Claude AI."""

    # Default model to use for generation
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    # Maximum tokens for skill generation
    MAX_TOKENS = 4096

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        validator: Optional[SkillValidator] = None,
        example_skills_dir: Optional[Path] = None,
    ):
        """
        Initialize AI skill generator.

        Args:
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            model: Model to use for generation
            validator: SkillValidator instance (creates new if not provided)
            example_skills_dir: Directory with example skills for few-shot prompting
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required: provide api_key parameter or set ANTHROPIC_API_KEY env var"
            )

        self.model = model or self.DEFAULT_MODEL
        self.client = Anthropic(api_key=self.api_key)
        self.validator = validator or SkillValidator()
        self.example_skills_dir = example_skills_dir or self._find_example_skills_dir()

    def generate_skills(
        self,
        required_capabilities: List[str],
        domain: str,
        context: str = "",
        validate: bool = True,
    ) -> List[GeneratedSkillDefinition]:
        """
        Generate custom skills for required capabilities.

        Args:
            required_capabilities: List of capability names needed
            domain: Domain context (e.g., "data-processing", "security")
            context: Additional context about the goal
            validate: Whether to validate generated skills

        Returns:
            List of GeneratedSkillDefinition objects
        """
        # Load example skills for few-shot prompting
        examples = self._load_example_skills()

        # Generate skills for each required capability
        generated_skills = []

        for capability in required_capabilities:
            skill = self._generate_single_skill(
                capability=capability,
                domain=domain,
                context=context,
                examples=examples,
                validate=validate,
            )

            if skill:
                generated_skills.append(skill)

        return generated_skills

    def _generate_single_skill(
        self,
        capability: str,
        domain: str,
        context: str,
        examples: List[str],
        validate: bool,
    ) -> Optional[GeneratedSkillDefinition]:
        """
        Generate a single skill for a capability.

        Args:
            capability: The capability to generate skill for
            domain: Domain context
            context: Additional context
            examples: Example skills for few-shot learning
            validate: Whether to validate the generated skill

        Returns:
            GeneratedSkillDefinition or None if generation fails
        """
        # Build the generation prompt
        prompt = self._build_generation_prompt(capability, domain, context, examples)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract skill content from response
            skill_content = response.content[0].text

            # Validate if requested
            validation_result = None
            if validate:
                validation_result = self.validator.validate_skill(
                    skill_content, f"{capability}-skill"
                )

            # Create skill definition
            skill_name = self._generate_skill_name(capability)

            skill = GeneratedSkillDefinition(
                name=skill_name,
                source_path=Path("ai_generated") / f"{skill_name}.md",
                capabilities=[capability],
                description=self._extract_description(skill_content),
                content=skill_content,
                generation_prompt=prompt,
                generation_model=self.model,
                validation_result=validation_result,
                match_score=0.9 if validation_result and validation_result.passed else 0.7,
            )

            return skill

        except Exception as e:
            # Log error and return None
            print(f"Error generating skill for {capability}: {e}")
            return None

    def _build_generation_prompt(
        self,
        capability: str,
        domain: str,
        context: str,
        examples: List[str],
    ) -> str:
        """
        Build the prompt for skill generation.

        Args:
            capability: The capability to generate skill for
            domain: Domain context
            context: Additional context
            examples: Example skills

        Returns:
            Complete prompt string
        """
        # Select relevant examples (max 2 to stay within context)
        selected_examples = examples[:2] if len(examples) > 2 else examples

        example_section = ""
        if selected_examples:
            example_section = "\n\n## Example Skills\n\n"
            for i, example in enumerate(selected_examples, 1):
                example_section += f"### Example {i}\n\n```markdown\n{example}\n```\n\n"

        prompt = f"""You are a skill generator for the amplihack goal agent system. Your task is to create a high-quality skill definition in markdown format.

## Requirements

Generate a skill for the following capability:
- **Capability**: {capability}
- **Domain**: {domain}
- **Context**: {context if context else "General purpose"}

## Skill Format

The skill MUST follow this structure:

1. **YAML Front Matter** (required):
```yaml
---
name: skill-name
description: Clear one-line description
model: inherit
---
```

2. **Main Description**: 2-3 paragraphs explaining what this skill does

3. **Core Capabilities Section**: List of specific capabilities with clear descriptions

4. **Usage Section**: How to use this skill effectively

5. **Examples** (optional but recommended): Concrete examples of usage

## Quality Standards

- Write clear, professional documentation
- Use proper markdown formatting
- Include specific, actionable capabilities
- Provide concrete usage guidance
- NO placeholder text (TODO, FIXME, XXX, etc.)
- NO template variables like {{variable}}
- NO generic "fill this in" instructions

## Style Guidelines

- Use active voice
- Be specific and concrete
- Focus on practical applications
- Include bullet lists for clarity
- Use code blocks for examples
{example_section}
## Your Task

Generate a complete, production-ready skill definition for the "{capability}" capability in the {domain} domain.
The skill should be immediately usable without any modifications.

Output ONLY the skill markdown, starting with the YAML front matter (---).
"""

        return prompt

    def _load_example_skills(self) -> List[str]:
        """
        Load example skills for few-shot prompting.

        Returns:
            List of example skill contents
        """
        examples = []

        if not self.example_skills_dir or not self.example_skills_dir.exists():
            return examples

        # Load up to 3 example skills
        skill_files = list(self.example_skills_dir.glob("**/*.md"))[:3]

        for skill_file in skill_files:
            try:
                content = skill_file.read_text()
                # Only include if reasonably sized (not too long)
                if 200 <= len(content) <= 3000:
                    examples.append(content)
            except Exception:
                continue

        return examples

    def _find_example_skills_dir(self) -> Optional[Path]:
        """Find the .claude/agents directory with example skills."""
        # Start from current file and traverse up
        current = Path(__file__).resolve()

        for parent in [current] + list(current.parents):
            agents_dir = parent / ".claude" / "agents"
            if agents_dir.exists() and agents_dir.is_dir():
                return agents_dir

        return None

    def _generate_skill_name(self, capability: str) -> str:
        """
        Generate a skill name from capability.

        Args:
            capability: The capability name

        Returns:
            Formatted skill name
        """
        # Convert to kebab-case
        name = capability.lower().replace(" ", "-").replace("_", "-")

        # Add suffix if not present
        if not name.endswith("-skill") and not name.endswith("er"):
            name = f"{name}-skill"

        return name

    def _extract_description(self, skill_content: str) -> str:
        """
        Extract description from skill content.

        Args:
            skill_content: Full skill markdown

        Returns:
            Extracted description (first paragraph or from front matter)
        """
        # Try to extract from YAML front matter first
        if skill_content.strip().startswith("---"):
            lines = skill_content.split("\n")
            for line in lines[1:]:
                if line.startswith("description:"):
                    desc = line.replace("description:", "").strip()
                    if desc:
                        return desc

        # Fall back to first paragraph after headings
        lines = skill_content.split("\n")
        description_lines = []

        in_content = False
        for line in lines:
            stripped = line.strip()

            # Skip YAML front matter
            if stripped == "---":
                in_content = not in_content
                continue

            if in_content and stripped and not stripped.startswith("#"):
                description_lines.append(stripped)
                if len(description_lines) >= 2:
                    break

        if description_lines:
            return " ".join(description_lines)[:200]

        return "AI-generated skill"

    def regenerate_failed_skills(
        self, skills: List[GeneratedSkillDefinition]
    ) -> List[GeneratedSkillDefinition]:
        """
        Regenerate skills that failed validation.

        Args:
            skills: List of generated skills to check

        Returns:
            List of regenerated skills
        """
        regenerated = []

        for skill in skills:
            if skill.validation_result and not skill.validation_result.passed:
                # Extract capability from skill
                capability = skill.capabilities[0] if skill.capabilities else skill.name

                # Regenerate
                new_skill = self._generate_single_skill(
                    capability=capability,
                    domain="general",
                    context="",
                    examples=self._load_example_skills(),
                    validate=True,
                )

                if new_skill:
                    regenerated.append(new_skill)

        return regenerated
