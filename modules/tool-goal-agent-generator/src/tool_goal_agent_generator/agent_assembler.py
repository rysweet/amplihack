"""
Agent Assembler - Assemble all components into complete goal agent.

Combines goal definition, execution plan, and skills into a runnable agent.
"""

import uuid

from .models import ExecutionPlan, GoalAgentBundle, GoalDefinition, SkillDefinition
from .utils import sanitize_bundle_name


class AgentAssembler:
    """Assemble goal agent bundles from components."""

    def assemble(
        self,
        goal_definition: GoalDefinition,
        execution_plan: ExecutionPlan,
        skills: list[SkillDefinition],
        bundle_name: str | None = None,
    ) -> GoalAgentBundle:
        """
        Assemble a complete goal agent bundle.

        Args:
            goal_definition: Goal extracted from prompt
            execution_plan: Execution plan for achieving goal
            skills: Skills needed for execution
            bundle_name: Optional custom bundle name

        Returns:
            Complete GoalAgentBundle ready for packaging
        """
        # Generate bundle name if not provided
        if not bundle_name:
            bundle_name = self._generate_bundle_name(goal_definition)

        # Create auto-mode configuration
        auto_mode_config = self._create_auto_mode_config(goal_definition, execution_plan)

        # Create metadata
        metadata = self._create_metadata(goal_definition, execution_plan, skills)

        # Create bundle
        bundle = GoalAgentBundle(
            id=uuid.uuid4(),
            name=bundle_name,
            version="1.0.0",
            goal_definition=goal_definition,
            execution_plan=execution_plan,
            skills=skills,
            auto_mode_config=auto_mode_config,
            metadata=metadata,
            status="ready",
        )

        return bundle

    def _generate_bundle_name(self, goal_definition: GoalDefinition) -> str:
        """
        Generate a bundle name from goal definition.

        The name is automatically sanitized to meet validation requirements:
        - 3-50 characters
        - Valid characters only (alphanumeric, hyphens)
        - Meaningful prefix preserved when truncating
        """
        # Extract key words from goal
        goal_words = goal_definition.goal.lower().split()

        # Filter out common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        key_words = [w for w in goal_words if w not in stop_words and len(w) > 2]

        # Take first 3-4 key words
        name_words = key_words[:3]

        # Add domain prefix
        domain_prefix = goal_definition.domain.split("-")[0]
        if domain_prefix not in name_words:
            name_words.insert(0, domain_prefix)

        # Join with hyphens
        raw_name = "-".join(name_words) if name_words else goal_definition.domain

        # Sanitize the name to ensure it meets all requirements
        # This handles truncation, character validation, and length constraints
        bundle_name = sanitize_bundle_name(raw_name, suffix="-agent")

        return bundle_name

    def _create_auto_mode_config(
        self, goal_definition: GoalDefinition, execution_plan: ExecutionPlan
    ) -> dict:
        """Create auto-mode configuration for autonomous execution."""
        # Determine max turns based on complexity and phase count
        complexity_turns = {
            "simple": 5,
            "moderate": 10,
            "complex": 15,
        }

        base_turns = complexity_turns.get(goal_definition.complexity, 10)
        phase_multiplier = 1 + (execution_plan.phase_count - 3) * 0.2  # Extra turns for more phases
        max_turns = int(base_turns * phase_multiplier)

        # Build initial prompt for auto-mode
        initial_prompt = self._build_initial_prompt(goal_definition, execution_plan)

        return {
            "max_turns": max_turns,
            "initial_prompt": initial_prompt,
            "working_dir": ".",  # Current directory
            "sdk": "claude",  # Default to Claude SDK
            "ui_mode": False,  # No UI for goal agents by default
            "success_criteria": goal_definition.success_criteria,
            "constraints": goal_definition.constraints,
        }

    def _build_initial_prompt(
        self, goal_definition: GoalDefinition, execution_plan: ExecutionPlan
    ) -> str:
        """Build initial prompt for auto-mode execution."""
        prompt_parts = [
            f"# Goal: {goal_definition.goal}",
            "",
            "## Objective",
            goal_definition.raw_prompt,
            "",
            "## Execution Plan",
        ]

        # Add phases
        for i, phase in enumerate(execution_plan.phases, 1):
            prompt_parts.append(f"\n### Phase {i}: {phase.name}")
            prompt_parts.append(phase.description)
            prompt_parts.append(f"**Estimated Duration**: {phase.estimated_duration}")
            prompt_parts.append(
                f"**Required Capabilities**: {', '.join(phase.required_capabilities)}"
            )

            if phase.dependencies:
                prompt_parts.append(f"**Dependencies**: {', '.join(phase.dependencies)}")

        # Add success criteria
        if goal_definition.success_criteria:
            prompt_parts.append("\n## Success Criteria")
            for criterion in goal_definition.success_criteria:
                prompt_parts.append(f"- {criterion}")

        # Add constraints
        if goal_definition.constraints:
            prompt_parts.append("\n## Constraints")
            for constraint in goal_definition.constraints:
                prompt_parts.append(f"- {constraint}")

        # Add instructions
        prompt_parts.append("\n## Instructions")
        prompt_parts.append("Execute the plan above autonomously:")
        prompt_parts.append("1. Follow each phase in sequence")
        prompt_parts.append("2. Use available skills and tools")
        prompt_parts.append("3. Verify success criteria are met")
        prompt_parts.append("4. Report progress and completion")

        return "\n".join(prompt_parts)

    def _create_metadata(
        self,
        goal_definition: GoalDefinition,
        execution_plan: ExecutionPlan,
        skills: list[SkillDefinition],
    ) -> dict:
        """Create bundle metadata."""
        return {
            "domain": goal_definition.domain,
            "complexity": goal_definition.complexity,
            "phase_count": execution_plan.phase_count,
            "skill_count": len(skills),
            "estimated_duration": execution_plan.total_estimated_duration,
            "required_capabilities": list(
                set(cap for phase in execution_plan.phases for cap in phase.required_capabilities)
            ),
            "skill_names": [skill.name for skill in skills],
            "parallel_opportunities": len(execution_plan.parallel_opportunities),
            "risk_factors": execution_plan.risk_factors,
        }
