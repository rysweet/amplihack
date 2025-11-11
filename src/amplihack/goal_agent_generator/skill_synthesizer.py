"""
Skill Synthesizer - Match existing skills to required capabilities.

Phase 1: Copies existing skills from .claude/agents directory.
Phase 2: AI-generate custom skills for gaps using Claude.
"""

from pathlib import Path
from typing import List, Optional

from .models import ExecutionPlan, SkillDefinition


class SkillSynthesizer:
    """Synthesize skills by matching existing skills to requirements."""

    # Skill matching keywords
    SKILL_KEYWORDS = {
        "data-processor": ["data", "process", "transform", "parse", "extract"],
        "security-analyzer": ["security", "vulnerability", "scan", "audit", "threat"],
        "tester": ["test", "validate", "verify", "check", "qa"],
        "deployer": ["deploy", "release", "publish", "ship"],
        "monitor": ["monitor", "alert", "track", "observe", "log"],
        "documenter": ["document", "report", "readme", "docs"],
        "analyzer": ["analyze", "review", "inspect", "examine"],
        "builder": ["build", "create", "generate", "implement"],
        "optimizer": ["optimize", "improve", "enhance", "performance"],
        "integrator": ["integrate", "connect", "api", "webhook"],
    }

    def __init__(
        self,
        skills_directory: Optional[Path] = None,
        enable_phase2: bool = False,
        phase2_coverage_threshold: float = 70.0,
    ):
        """
        Initialize skill synthesizer.

        Args:
            skills_directory: Path to existing skills directory
            enable_phase2: Enable Phase 2 AI skill generation
            phase2_coverage_threshold: Coverage % threshold to trigger Phase 2 (default 70%)
        """
        self.skills_directory = skills_directory or self._find_skills_directory()
        self.enable_phase2 = enable_phase2
        self.phase2_coverage_threshold = phase2_coverage_threshold

        # Phase 2 components (lazy loaded)
        self._gap_analyzer = None
        self._skill_generator = None
        self._skill_registry = None

    def synthesize_skills(
        self, execution_plan: ExecutionPlan, domain: str = "general"
    ) -> List[SkillDefinition]:
        """
        Synthesize skills needed for execution plan.

        Phase 1: Match existing skills
        Phase 2: Generate custom skills if coverage is insufficient

        Args:
            execution_plan: Plan requiring skills
            domain: Domain context for skill generation

        Returns:
            List of matched/generated skills with scores
        """
        # Phase 1: Find existing skills
        required_skills = set(execution_plan.required_skills)
        synthesized_skills = []

        for skill_name in required_skills:
            skill = self._find_matching_skill(skill_name)
            if skill:
                synthesized_skills.append(skill)

        # If no skills found, create fallback generic skill
        if not synthesized_skills:
            synthesized_skills.append(self._create_generic_skill())

        # Phase 2: Check if we need to generate custom skills
        if self.enable_phase2:
            synthesized_skills = self._apply_phase2(
                execution_plan, synthesized_skills, domain
            )

        return synthesized_skills

    def _apply_phase2(
        self,
        execution_plan: ExecutionPlan,
        existing_skills: List[SkillDefinition],
        domain: str,
    ) -> List[SkillDefinition]:
        """
        Apply Phase 2 AI skill generation if needed.

        Args:
            execution_plan: Execution plan
            existing_skills: Skills found in Phase 1
            domain: Domain context

        Returns:
            Combined list of existing + generated skills
        """
        try:
            # Lazy load Phase 2 components
            if not self._gap_analyzer:
                from .phase2 import (
                    SkillGapAnalyzer,
                    AISkillGenerator,
                    SkillRegistry,
                )

                self._gap_analyzer = SkillGapAnalyzer()
                self._skill_generator = AISkillGenerator()
                self._skill_registry = SkillRegistry()

            # Analyze gaps
            gap_report = self._gap_analyzer.analyze_gaps(execution_plan, existing_skills)

            # Check if we need to generate custom skills
            if gap_report.coverage_percentage < self.phase2_coverage_threshold:
                print(
                    f"Coverage {gap_report.coverage_percentage:.1f}% below threshold "
                    f"{self.phase2_coverage_threshold}%. Generating custom skills..."
                )

                # Generate skills for missing capabilities
                generated_skills = self._skill_generator.generate_skills(
                    required_capabilities=gap_report.missing_capabilities,
                    domain=domain,
                    context=f"Execution plan with {len(execution_plan.phases)} phases",
                    validate=True,
                )

                # Register all skills
                self._skill_registry.register_batch(existing_skills)
                self._skill_registry.register_batch(generated_skills)

                # Save registry
                self._skill_registry.save()

                print(
                    f"Generated {len(generated_skills)} custom skills. "
                    f"Total skills: {len(existing_skills) + len(generated_skills)}"
                )

                # Return combined list
                return existing_skills + generated_skills

            else:
                print(
                    f"Coverage {gap_report.coverage_percentage:.1f}% meets threshold. "
                    "Using existing skills only."
                )

        except Exception as e:
            print(f"Phase 2 skill generation failed: {e}")
            print("Falling back to Phase 1 skills only")

        return existing_skills

    def _find_skills_directory(self) -> Path:
        """Find the .claude/agents directory."""
        # Start from current file and traverse up
        current = Path(__file__).resolve()

        for parent in [current] + list(current.parents):
            agents_dir = parent / ".claude" / "agents" / "amplihack"
            if agents_dir.exists() and agents_dir.is_dir():
                return agents_dir

        # Fallback: create temp directory
        return Path.cwd() / ".skills_temp"

    def _find_matching_skill(self, skill_name: str) -> Optional[SkillDefinition]:
        """
        Find existing skill that matches the requirement.

        Args:
            skill_name: Name of required skill

        Returns:
            SkillDefinition if found, None otherwise
        """
        keywords = self.SKILL_KEYWORDS.get(skill_name, [skill_name.lower()])

        # Search for skill files in directory
        if not self.skills_directory.exists():
            return None

        best_match = None
        best_score = 0.0

        for skill_file in self.skills_directory.glob("**/*.md"):
            content = skill_file.read_text()
            content_lower = content.lower()

            # Calculate match score
            score = sum(1 for keyword in keywords if keyword in content_lower)
            score = score / len(keywords) if keywords else 0

            if score > best_score:
                best_score = score
                best_match = skill_file

        if best_match and best_score > 0.3:  # Threshold for acceptable match
            return self._load_skill(best_match, skill_name, best_score)

        return None

    def _load_skill(self, skill_path: Path, skill_name: str, match_score: float) -> SkillDefinition:
        """Load skill from file."""
        content = skill_path.read_text()

        # Extract description from first paragraph
        description = self._extract_description(content)

        # Extract capabilities from content
        capabilities = self._extract_capabilities(content, skill_name)

        # Extract dependencies
        dependencies = self._extract_dependencies(content)

        return SkillDefinition(
            name=skill_name,
            source_path=skill_path,
            capabilities=capabilities,
            description=description,
            content=content,
            dependencies=dependencies,
            match_score=match_score,
        )

    def _extract_description(self, content: str) -> str:
        """Extract description from skill markdown."""
        lines = content.split("\n")
        description_lines = []

        in_description = False
        for line in lines:
            stripped = line.strip()

            # Skip headings
            if stripped.startswith("#"):
                in_description = True
                continue

            # Collect description lines
            if in_description and stripped:
                description_lines.append(stripped)
                if len(description_lines) >= 3:  # First 3 lines
                    break

        return " ".join(description_lines[:200])  # Limit to 200 chars

    def _extract_capabilities(self, content: str, skill_name: str) -> List[str]:
        """Extract capabilities from skill content."""
        # Use keywords as capabilities
        keywords = self.SKILL_KEYWORDS.get(skill_name, [skill_name])

        # Look for additional capabilities in content
        content_lower = content.lower()
        capabilities = list(keywords)

        # Common capability patterns
        capability_words = [
            "analyze",
            "process",
            "transform",
            "validate",
            "generate",
            "deploy",
            "monitor",
            "report",
        ]

        for word in capability_words:
            if word in content_lower and word not in capabilities:
                capabilities.append(word)

        return capabilities[:5]  # Limit to top 5

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from skill content."""
        dependencies = []

        # Look for dependency patterns
        if "requires" in content.lower() or "depends on" in content.lower():
            # Simple extraction - look for other skill names
            for skill_name in self.SKILL_KEYWORDS.keys():
                if skill_name in content.lower():
                    dependencies.append(skill_name)

        return dependencies[:3]  # Limit to top 3

    def _create_generic_skill(self) -> SkillDefinition:
        """Create a generic fallback skill."""
        return SkillDefinition(
            name="generic-executor",
            source_path=Path("builtin"),
            capabilities=["execute", "generic-task"],
            description="Generic skill for executing tasks",
            content="""# Generic Executor

This is a generic skill for executing tasks when no specific skill matches.

## Capabilities

- Execute generic tasks
- Coordinate with other skills
- Report results

## Usage

Use this skill when no other specialized skill is available.
""",
            match_score=0.5,
        )
