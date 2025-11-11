"""
Skill Gap Analyzer - Analyzes which capabilities need custom skills vs existing skills.

Calculates coverage percentage, ranks gaps by criticality, and recommends action.
"""

import uuid
from typing import Dict, List, Tuple

from ..models import ExecutionPlan, SkillDefinition, SkillGapReport


class SkillGapAnalyzer:
    """Analyzes gaps between required and available capabilities."""

    # Criticality weights for different capability categories
    CRITICALITY_WEIGHTS = {
        "core": 1.0,  # Core functionality
        "validation": 0.8,  # Testing and validation
        "integration": 0.7,  # Integration with external systems
        "optimization": 0.5,  # Performance optimization
        "documentation": 0.3,  # Documentation and reporting
    }

    # Capability categorization keywords
    CAPABILITY_CATEGORIES = {
        "core": ["execute", "process", "transform", "parse", "analyze", "build", "create"],
        "validation": ["test", "validate", "verify", "check", "audit", "scan"],
        "integration": ["integrate", "connect", "api", "webhook", "deploy", "publish"],
        "optimization": ["optimize", "improve", "enhance", "performance", "cache"],
        "documentation": ["document", "report", "readme", "log", "monitor"],
    }

    def analyze_gaps(
        self,
        execution_plan: ExecutionPlan,
        existing_skills: List[SkillDefinition],
    ) -> SkillGapReport:
        """
        Analyze gaps between required and available capabilities.

        Args:
            execution_plan: The execution plan with required capabilities
            existing_skills: List of existing skills that were matched

        Returns:
            SkillGapReport with coverage analysis and recommendations
        """
        # Collect all required capabilities from plan phases
        required_capabilities = self._collect_required_capabilities(execution_plan)

        # Collect all available capabilities from existing skills
        available_capabilities = self._collect_available_capabilities(existing_skills)

        # Calculate coverage
        coverage_percentage = self._calculate_coverage(
            required_capabilities, available_capabilities
        )

        # Identify missing capabilities
        missing_capabilities = [
            cap for cap in required_capabilities if cap not in available_capabilities
        ]

        # Organize gaps by phase
        gaps_by_phase = self._organize_gaps_by_phase(execution_plan, available_capabilities)

        # Rank gaps by criticality
        criticality_ranking = self._rank_by_criticality(missing_capabilities)

        # Determine recommendation
        recommendation = self._determine_recommendation(
            coverage_percentage, missing_capabilities, criticality_ranking
        )

        return SkillGapReport(
            execution_plan_id=execution_plan.goal_id,
            coverage_percentage=coverage_percentage,
            missing_capabilities=missing_capabilities,
            gaps_by_phase=gaps_by_phase,
            criticality_ranking=criticality_ranking,
            recommendation=recommendation,
        )

    def _collect_required_capabilities(self, execution_plan: ExecutionPlan) -> List[str]:
        """Collect all unique required capabilities from plan phases."""
        capabilities = set()

        for phase in execution_plan.phases:
            for capability in phase.required_capabilities:
                capabilities.add(capability.lower())

        return list(capabilities)

    def _collect_available_capabilities(self, skills: List[SkillDefinition]) -> List[str]:
        """Collect all unique available capabilities from skills."""
        capabilities = set()

        for skill in skills:
            for capability in skill.capabilities:
                capabilities.add(capability.lower())

        return list(capabilities)

    def _calculate_coverage(
        self, required: List[str], available: List[str]
    ) -> float:
        """
        Calculate coverage percentage.

        Args:
            required: List of required capabilities
            available: List of available capabilities

        Returns:
            Coverage percentage (0-100)
        """
        if not required:
            return 100.0

        # Count how many required capabilities are covered
        covered_count = sum(1 for cap in required if cap in available)

        return (covered_count / len(required)) * 100.0

    def _organize_gaps_by_phase(
        self, execution_plan: ExecutionPlan, available_capabilities: List[str]
    ) -> Dict[str, List[str]]:
        """
        Organize missing capabilities by plan phase.

        Args:
            execution_plan: The execution plan
            available_capabilities: List of available capabilities

        Returns:
            Dictionary mapping phase names to missing capabilities
        """
        gaps_by_phase = {}

        for phase in execution_plan.phases:
            missing_in_phase = [
                cap
                for cap in phase.required_capabilities
                if cap.lower() not in available_capabilities
            ]

            if missing_in_phase:
                gaps_by_phase[phase.name] = missing_in_phase

        return gaps_by_phase

    def _rank_by_criticality(self, missing_capabilities: List[str]) -> List[Tuple[str, float]]:
        """
        Rank missing capabilities by criticality.

        Args:
            missing_capabilities: List of missing capability names

        Returns:
            List of (capability, criticality_score) tuples, sorted by score descending
        """
        ranked = []

        for capability in missing_capabilities:
            # Determine category and get weight
            category = self._categorize_capability(capability)
            weight = self.CRITICALITY_WEIGHTS.get(category, 0.5)

            ranked.append((capability, weight))

        # Sort by criticality score descending
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def _categorize_capability(self, capability: str) -> str:
        """
        Categorize a capability based on keywords.

        Args:
            capability: Capability name

        Returns:
            Category name (core, validation, integration, optimization, documentation)
        """
        capability_lower = capability.lower()

        # Check each category's keywords
        for category, keywords in self.CAPABILITY_CATEGORIES.items():
            if any(keyword in capability_lower for keyword in keywords):
                return category

        # Default to core if no match
        return "core"

    def _determine_recommendation(
        self,
        coverage_percentage: float,
        missing_capabilities: List[str],
        criticality_ranking: List[Tuple[str, float]],
    ) -> str:
        """
        Determine recommendation based on gap analysis.

        Args:
            coverage_percentage: Coverage percentage
            missing_capabilities: List of missing capabilities
            criticality_ranking: Ranked list of missing capabilities with scores

        Returns:
            Recommendation: "use_existing", "generate_custom", or "mixed"
        """
        # If coverage is 100%, use existing only
        if coverage_percentage >= 100.0:
            return "use_existing"

        # If coverage is very low, need custom generation
        if coverage_percentage < 40.0:
            return "generate_custom"

        # If coverage is high (>=70%), use existing
        if coverage_percentage >= 70.0:
            return "use_existing"

        # For medium coverage, check criticality of gaps
        # If critical capabilities are missing, generate custom
        if criticality_ranking:
            highest_criticality = criticality_ranking[0][1]
            if highest_criticality >= 0.8:  # High criticality threshold
                return "generate_custom"

        # If gaps are low criticality, mixed approach
        return "mixed"
