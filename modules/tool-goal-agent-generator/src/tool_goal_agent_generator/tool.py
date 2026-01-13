"""
Goal Agent Generator Tool - Amplifier tool wrapper.

Exposes the Goal Agent Generator functionality as an Amplifier tool
that can be invoked by agents to create specialized goal-seeking agents.
"""

from pathlib import Path
from typing import Any

from amplifier_core.tool import Tool, ToolParameter, ToolResult

from .agent_assembler import AgentAssembler
from .models import GoalAgentBundle
from .objective_planner import ObjectivePlanner
from .packager import GoalAgentPackager
from .prompt_analyzer import PromptAnalyzer
from .skill_synthesizer import SkillSynthesizer


class GoalAgentGeneratorTool(Tool):
    """
    Generate specialized goal-seeking agents from natural language prompts.

    This tool analyzes a goal description and generates a complete agent bundle
    including execution plan, required skills, and auto-mode configuration.
    """

    name = "goal-agent-generator"
    description = """Generate a specialized goal-seeking agent from a natural language goal description.

The tool will:
1. Analyze the goal to extract objectives, domain, and constraints
2. Generate a multi-phase execution plan
3. Select and synthesize required skills
4. Assemble a complete agent bundle

Use this when you need to create a new specialized agent for a complex task."""

    parameters = [
        ToolParameter(
            name="goal",
            type="string",
            description="Natural language description of the goal. Be specific about what you want to achieve.",
            required=True,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="Name for the generated agent (3-50 characters, alphanumeric and hyphens)",
            required=True,
        ),
        ToolParameter(
            name="skills_path",
            type="string",
            description="Path to directory containing available skills. Defaults to bundle skills.",
            required=False,
        ),
        ToolParameter(
            name="output_path",
            type="string",
            description="Path where the generated agent bundle should be saved.",
            required=False,
        ),
        ToolParameter(
            name="auto_mode",
            type="boolean",
            description="Whether to enable auto-mode configuration for autonomous execution. Default: true",
            required=False,
        ),
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the goal agent generator tool."""
        super().__init__(config)
        self.prompt_analyzer = PromptAnalyzer()
        self.objective_planner = ObjectivePlanner()
        self.agent_assembler = AgentAssembler()
        self.packager = GoalAgentPackager()

    async def execute(
        self,
        goal: str,
        name: str,
        skills_path: str | None = None,
        output_path: str | None = None,
        auto_mode: bool = True,
    ) -> ToolResult:
        """
        Generate a goal-seeking agent from a natural language goal.

        Args:
            goal: Natural language description of the goal
            name: Name for the generated agent
            skills_path: Path to skills directory (optional)
            output_path: Path to save the generated bundle (optional)
            auto_mode: Enable auto-mode configuration (default: True)

        Returns:
            ToolResult with the generated agent bundle information
        """
        try:
            # Step 1: Analyze the goal
            goal_definition = self.prompt_analyzer.analyze_text(goal)

            # Step 2: Generate execution plan
            execution_plan = self.objective_planner.generate_plan(goal_definition)

            # Step 3: Synthesize required skills
            skills_dir = Path(skills_path) if skills_path else self._get_default_skills_path()
            skill_synthesizer = SkillSynthesizer(skills_directory=skills_dir)
            skills = skill_synthesizer.synthesize_skills(execution_plan)

            # Step 4: Assemble the agent bundle
            bundle = self.agent_assembler.assemble(
                goal_definition=goal_definition,
                execution_plan=execution_plan,
                skills=skills,
                bundle_name=name,
            )

            # Configure auto-mode if requested
            if auto_mode and bundle.auto_mode_config:
                bundle.auto_mode_config["enabled"] = True

            # Step 5: Package if output path provided
            if output_path:
                output_dir = Path(output_path)
                packager = GoalAgentPackager(output_dir=output_dir)
                saved_path = packager.package(bundle)
                package_info = f"Bundle saved to: {saved_path}"
            else:
                package_info = "Bundle generated (not saved - provide output_path to save)"

            return ToolResult(
                success=True,
                output=self._format_bundle_summary(bundle, package_info),
                metadata={
                    "bundle_id": str(bundle.id),
                    "name": bundle.name,
                    "skill_count": bundle.skill_count,
                    "phase_count": bundle.execution_plan.phase_count
                    if bundle.execution_plan
                    else 0,
                    "domain": goal_definition.domain,
                    "complexity": goal_definition.complexity,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                output=f"Invalid input: {e}",
                error=str(e),
            )
        except FileNotFoundError as e:
            return ToolResult(
                success=False,
                output=f"File not found: {e}",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=f"Failed to generate agent: {e}",
                error=str(e),
            )

    def _get_default_skills_path(self) -> Path:
        """Get the default skills path from the amplihack bundle."""
        # Try to find skills in common locations
        possible_paths = [
            Path.cwd() / "skills",
            Path.home() / "src" / "amplifier-amplihack" / "skills",
            Path(__file__).parent.parent.parent.parent / "skills",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Return first option even if doesn't exist (will error later)
        return possible_paths[0]

    def _format_bundle_summary(self, bundle: GoalAgentBundle, package_info: str) -> str:
        """Format a summary of the generated bundle."""
        lines = [
            f"# Goal Agent Generated: {bundle.name}",
            "",
            f"**Status:** {bundle.status}",
            f"**Version:** {bundle.version}",
            "",
            "## Goal Definition",
        ]

        if bundle.goal_definition:
            lines.extend(
                [
                    f"- **Goal:** {bundle.goal_definition.goal}",
                    f"- **Domain:** {bundle.goal_definition.domain}",
                    f"- **Complexity:** {bundle.goal_definition.complexity}",
                ]
            )
            if bundle.goal_definition.constraints:
                lines.append(f"- **Constraints:** {', '.join(bundle.goal_definition.constraints)}")
            if bundle.goal_definition.success_criteria:
                lines.append("- **Success Criteria:**")
                for criterion in bundle.goal_definition.success_criteria:
                    lines.append(f"  - {criterion}")

        lines.append("")
        lines.append("## Execution Plan")

        if bundle.execution_plan:
            lines.append(f"- **Total Duration:** {bundle.execution_plan.total_estimated_duration}")
            lines.append(f"- **Phases:** {bundle.execution_plan.phase_count}")
            lines.append("")
            for i, phase in enumerate(bundle.execution_plan.phases, 1):
                lines.append(f"### Phase {i}: {phase.name}")
                lines.append(f"- {phase.description}")
                lines.append(f"- Duration: {phase.estimated_duration}")
                lines.append(f"- Capabilities: {', '.join(phase.required_capabilities)}")
                lines.append("")

        lines.append("## Skills")
        lines.append(f"- **Count:** {bundle.skill_count}")
        for skill in bundle.skills[:5]:  # Show first 5
            lines.append(f"- {skill.name} (match: {skill.match_score:.0%})")
        if bundle.skill_count > 5:
            lines.append(f"- ... and {bundle.skill_count - 5} more")

        lines.append("")
        lines.append("## Package")
        lines.append(package_info)

        return "\n".join(lines)
