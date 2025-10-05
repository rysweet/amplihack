"""
Philosophy-Based Decision Framework

Implements the core decision framework that automatically chooses options
most compatible with amplihack philosophy principles:
- Quality and Cleanliness over Speed
- Simplicity and Clarity
- Ruthless Simplicity
- Modular Design (Bricks & Studs)
- Zero-BS Implementation
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class DecisionContext(Enum):
    """Common decision contexts in development workflow"""

    PR_ORGANIZATION = "pr_organization"
    FEATURE_SCOPE = "feature_scope"
    REFACTORING_APPROACH = "refactoring_approach"
    TESTING_STRATEGY = "testing_strategy"
    IMPLEMENTATION_APPROACH = "implementation_approach"
    CODE_ORGANIZATION = "code_organization"
    INTEGRATION_STRATEGY = "integration_strategy"
    CLEANUP_TIMING = "cleanup_timing"
    GENERAL = "general"


@dataclass
class PhilosophyScores:
    """Philosophy alignment scores for a decision option"""

    quality: float = 0.0  # Quality & Cleanliness (0-20)
    clarity: float = 0.0  # Simplicity & Clarity (0-20)
    modularity: float = 0.0  # Modular Design (0-20)
    maintainability: float = 0.0  # Maintainability (0-20)
    regenerability: float = 0.0  # Regenerability (0-20)

    @property
    def total_score(self) -> float:
        """Calculate total philosophy score (0-100)"""
        return (
            self.quality
            + self.clarity
            + self.modularity
            + self.maintainability
            + self.regenerability
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization"""
        return {
            "quality": self.quality,
            "clarity": self.clarity,
            "modularity": self.modularity,
            "maintainability": self.maintainability,
            "regenerability": self.regenerability,
            "total": self.total_score,
        }


@dataclass
class DecisionOption:
    """A single option in a decision scenario"""

    id: str
    description: str
    philosophy_scores: PhilosophyScores
    rationale: str = ""
    estimated_effort: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "description": self.description,
            "philosophy_scores": self.philosophy_scores.to_dict(),
            "rationale": self.rationale,
            "estimated_effort": self.estimated_effort,
            "dependencies": self.dependencies,
            "risks": self.risks,
        }


@dataclass
class DecisionResult:
    """Result of philosophy-based decision making"""

    context: DecisionContext
    description: str
    options: List[DecisionOption]
    selected_option: DecisionOption
    decision_rationale: str
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "context": self.context.value,
            "description": self.description,
            "options": [opt.to_dict() for opt in self.options],
            "selected_option": self.selected_option.to_dict(),
            "decision_rationale": self.decision_rationale,
            "confidence": self.confidence,
        }


class PhilosophyDecisionFramework:
    """
    Core framework for making philosophy-aligned decisions.

    Automatically chooses options that best align with amplihack
    philosophy principles using a scoring system.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.decision_templates = self._load_decision_templates()

    def make_decision(
        self, context: Union[DecisionContext, str], description: str, options: List[Dict[str, Any]]
    ) -> DecisionResult:
        """
        Make a philosophy-aligned decision between multiple options.

        Args:
            context: Decision context (enum or string)
            description: Description of the decision being made
            options: List of option dictionaries with id, description, and optional scores

        Returns:
            DecisionResult: The decision result with selected option and rationale
        """
        # Normalize context
        if isinstance(context, str):
            try:
                context = DecisionContext(context)
            except ValueError:
                context = DecisionContext.GENERAL

        # Convert options to DecisionOption objects
        decision_options = []
        for opt_data in options:
            # Extract philosophy scores if provided, otherwise calculate
            if "philosophy_scores" in opt_data:
                scores_data = opt_data["philosophy_scores"]
                if isinstance(scores_data, dict):
                    scores = PhilosophyScores(**scores_data)
                else:
                    scores = scores_data
            else:
                scores = self._calculate_philosophy_scores(context, opt_data)

            option = DecisionOption(
                id=opt_data["id"],
                description=opt_data["description"],
                philosophy_scores=scores,
                rationale=opt_data.get("rationale", ""),
                estimated_effort=opt_data.get("estimated_effort"),
                dependencies=opt_data.get("dependencies", []),
                risks=opt_data.get("risks", []),
            )
            decision_options.append(option)

        # Select the highest scoring option
        selected_option = max(decision_options, key=lambda opt: opt.philosophy_scores.total_score)

        # Calculate confidence based on score separation
        confidence = self._calculate_confidence(decision_options, selected_option)

        # Generate decision rationale
        rationale = self._generate_decision_rationale(selected_option, decision_options, context)

        result = DecisionResult(
            context=context,
            description=description,
            options=decision_options,
            selected_option=selected_option,
            decision_rationale=rationale,
            confidence=confidence,
        )

        self.logger.info(
            f"Philosophy decision made for {context.value}: "
            f"Selected '{selected_option.id}' with score {selected_option.philosophy_scores.total_score:.1f}/100"
        )

        return result

    def _calculate_philosophy_scores(
        self, context: DecisionContext, option_data: Dict[str, Any]
    ) -> PhilosophyScores:
        """
        Calculate philosophy scores for an option using context-specific heuristics.

        Args:
            context: Decision context
            option_data: Option data dictionary

        Returns:
            PhilosophyScores: Calculated scores
        """
        # Check if we have a template for this context
        if context in self.decision_templates:
            template = self.decision_templates[context]
            return template.calculate_scores(option_data)

        # Default scoring heuristics
        return self._default_scoring_heuristics(option_data)

    def _default_scoring_heuristics(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Default scoring heuristics when no specific template exists"""

        description = option_data.get("description", "").lower()
        id_str = option_data.get("id", "").lower()
        combined = f"{description} {id_str}"

        scores = PhilosophyScores()

        # Quality heuristics
        if any(word in combined for word in ["separate", "focused", "clean", "quality"]):
            scores.quality += 5
        if any(word in combined for word in ["mixed", "combined", "quick", "hack"]):
            scores.quality -= 3
        scores.quality = max(0, min(20, scores.quality + 10))  # Base score 10

        # Clarity heuristics
        if any(word in combined for word in ["clear", "simple", "single", "focused"]):
            scores.clarity += 5
        if any(word in combined for word in ["complex", "multiple", "mixed", "combined"]):
            scores.clarity -= 3
        scores.clarity = max(0, min(20, scores.clarity + 10))  # Base score 10

        # Modularity heuristics
        if any(word in combined for word in ["separate", "modular", "independent", "isolated"]):
            scores.modularity += 5
        if any(word in combined for word in ["combined", "mixed", "coupled", "together"]):
            scores.modularity -= 3
        scores.modularity = max(0, min(20, scores.modularity + 10))  # Base score 10

        # Maintainability heuristics
        if any(word in combined for word in ["maintainable", "extensible", "flexible", "future"]):
            scores.maintainability += 5
        if any(word in combined for word in ["rigid", "hardcoded", "fixed", "temporary"]):
            scores.maintainability -= 3
        scores.maintainability = max(0, min(20, scores.maintainability + 10))  # Base score 10

        # Regenerability heuristics
        if any(
            word in combined for word in ["documented", "clear", "specification", "reproducible"]
        ):
            scores.regenerability += 5
        if any(word in combined for word in ["undocumented", "magic", "unclear", "complex"]):
            scores.regenerability -= 3
        scores.regenerability = max(0, min(20, scores.regenerability + 10))  # Base score 10

        return scores

    def _calculate_confidence(
        self, options: List[DecisionOption], selected: DecisionOption
    ) -> float:
        """Calculate confidence in the decision based on score separation"""

        if len(options) < 2:
            return 1.0

        scores = [opt.philosophy_scores.total_score for opt in options]
        scores.sort(reverse=True)

        best_score = scores[0]
        second_best = scores[1] if len(scores) > 1 else 0

        # Confidence based on separation (0-1 scale)
        if best_score == 0:
            return 0.5

        separation = (best_score - second_best) / best_score
        confidence = min(1.0, max(0.1, separation))

        return confidence

    def _generate_decision_rationale(
        self, selected: DecisionOption, all_options: List[DecisionOption], context: DecisionContext
    ) -> str:
        """Generate human-readable rationale for the decision"""

        scores = selected.philosophy_scores
        total = scores.total_score

        # Find the strongest philosophy principle
        principle_scores = {
            "quality": scores.quality,
            "clarity": scores.clarity,
            "modularity": scores.modularity,
            "maintainability": scores.maintainability,
            "regenerability": scores.regenerability,
        }

        strongest = max(principle_scores.items(), key=lambda x: x[1])

        rationale_parts = [
            f"Selected '{selected.description}' with philosophy score {total:.1f}/100.",
            f"This option best aligns with amplihack principles, particularly {strongest[0]} ({strongest[1]:.1f}/20).",
        ]

        # Add comparison to alternatives
        if len(all_options) > 1:
            other_scores = [
                opt.philosophy_scores.total_score for opt in all_options if opt != selected
            ]
            best_alternative = max(other_scores) if other_scores else 0

            if best_alternative > 0:
                improvement = total - best_alternative
                rationale_parts.append(
                    f"This choice scores {improvement:.1f} points higher than the best alternative, "
                    "prioritizing quality and cleanliness over speed."
                )

        # Add specific rationale if provided
        if selected.rationale:
            rationale_parts.append(f"Additional context: {selected.rationale}")

        return " ".join(rationale_parts)

    def _load_decision_templates(self) -> Dict[DecisionContext, "DecisionTemplate"]:
        """Load decision templates for common scenarios"""

        templates = {}

        # PR Organization template
        templates[DecisionContext.PR_ORGANIZATION] = PROrganizationTemplate()

        # Feature Scope template
        templates[DecisionContext.FEATURE_SCOPE] = FeatureScopeTemplate()

        # Refactoring Approach template
        templates[DecisionContext.REFACTORING_APPROACH] = RefactoringTemplate()

        # Testing Strategy template
        templates[DecisionContext.TESTING_STRATEGY] = TestingStrategyTemplate()

        # Implementation Approach template
        templates[DecisionContext.IMPLEMENTATION_APPROACH] = ImplementationApproachTemplate()

        # Code Organization template
        templates[DecisionContext.CODE_ORGANIZATION] = CodeOrganizationTemplate()

        # Integration Strategy template
        templates[DecisionContext.INTEGRATION_STRATEGY] = IntegrationStrategyTemplate()

        # Cleanup Timing template
        templates[DecisionContext.CLEANUP_TIMING] = CleanupTimingTemplate()

        return templates


class DecisionTemplate:
    """Base class for decision templates"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Calculate philosophy scores for this specific decision context"""
        raise NotImplementedError("Subclasses must implement calculate_scores")


class PROrganizationTemplate(DecisionTemplate):
    """Template for PR organization decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score PR organization options"""

        option_id = option_data.get("id", "").lower()
        description = option_data.get("description", "").lower()

        scores = PhilosophyScores()

        if "separate" in option_id or "separate" in description:
            # Separate PRs score higher on all principles
            scores.quality = 18  # Better review quality
            scores.clarity = 17  # Single concern is clearer
            scores.modularity = 19  # Perfect separation of concerns
            scores.maintainability = 16
            scores.regenerability = 15
        elif "same" in option_id or "combined" in description:
            # Combined PRs score lower due to mixed concerns
            scores.quality = 12  # Mixed concerns reduce quality
            scores.clarity = 10  # Harder to review
            scores.modularity = 8  # Violates separation
            scores.maintainability = 11
            scores.regenerability = 10
        else:
            # Default middle scores
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


class FeatureScopeTemplate(DecisionTemplate):
    """Template for feature scope decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score feature scope options"""

        description = option_data.get("description", "").lower()

        scores = PhilosophyScores()

        if any(word in description for word in ["minimal", "simple", "basic", "core"]):
            # Minimal implementations score higher on simplicity
            scores.quality = 16
            scores.clarity = 18  # Simpler is clearer
            scores.modularity = 17
            scores.maintainability = 18  # Easier to maintain
            scores.regenerability = 16
        elif any(word in description for word in ["comprehensive", "complete", "full", "advanced"]):
            # Comprehensive implementations can score high if well-designed
            scores.quality = 17
            scores.clarity = 14  # More complex
            scores.modularity = 15
            scores.maintainability = 14  # More to maintain
            scores.regenerability = 13  # Harder to regenerate
        else:
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


class RefactoringTemplate(DecisionTemplate):
    """Template for refactoring approach decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score refactoring approach options"""

        description = option_data.get("description", "").lower()

        scores = PhilosophyScores()

        if any(word in description for word in ["incremental", "gradual", "step"]):
            # Incremental refactoring scores higher on maintainability
            scores.quality = 16
            scores.clarity = 17
            scores.modularity = 16
            scores.maintainability = 19  # Much safer to maintain
            scores.regenerability = 17
        elif any(word in description for word in ["complete", "rewrite", "full"]):
            # Complete rewrites can be good but riskier
            scores.quality = 17
            scores.clarity = 18
            scores.modularity = 18
            scores.maintainability = 12  # Higher risk
            scores.regenerability = 14
        else:
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


class TestingStrategyTemplate(DecisionTemplate):
    """Template for testing strategy decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score testing strategy options"""

        description = option_data.get("description", "").lower()

        scores = PhilosophyScores()

        if "tdd" in description or "test-driven" in description:
            # TDD scores higher on quality and maintainability
            scores.quality = 19  # Better design quality
            scores.clarity = 16
            scores.modularity = 17
            scores.maintainability = 18  # Better long-term maintenance
            scores.regenerability = 16
        elif "test-after" in description or "after" in description:
            # Test-after can work but scores lower
            scores.quality = 14
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 14
            scores.regenerability = 15
        else:
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


class ImplementationApproachTemplate(DecisionTemplate):
    """Template for implementation approach decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score implementation approach options"""

        description = option_data.get("description", "").lower()

        scores = PhilosophyScores()

        if any(word in description for word in ["simple", "straightforward", "minimal", "direct"]):
            # Simple approaches score higher on simplicity and clarity
            scores.quality = 16
            scores.clarity = 19  # Very clear
            scores.modularity = 15
            scores.maintainability = 17
            scores.regenerability = 18
        elif any(
            word in description for word in ["robust", "comprehensive", "extensible", "flexible"]
        ):
            # Robust approaches can score high if well-designed
            scores.quality = 18
            scores.clarity = 14  # More complex
            scores.modularity = 17
            scores.maintainability = 16
            scores.regenerability = 14
        elif any(word in description for word in ["complex", "advanced", "sophisticated"]):
            # Complex approaches score lower on clarity
            scores.quality = 15
            scores.clarity = 11  # Harder to understand
            scores.modularity = 14
            scores.maintainability = 13
            scores.regenerability = 12
        else:
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


class CodeOrganizationTemplate(DecisionTemplate):
    """Template for code organization decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score code organization options"""

        description = option_data.get("description", "").lower()

        scores = PhilosophyScores()

        if any(word in description for word in ["modular", "separate", "isolated", "independent"]):
            # Modular organization scores highest on modularity
            scores.quality = 17
            scores.clarity = 16
            scores.modularity = 19  # Excellent modularity
            scores.maintainability = 18
            scores.regenerability = 17
        elif any(word in description for word in ["monolithic", "single", "combined", "unified"]):
            # Monolithic can be simple but less modular
            scores.quality = 14
            scores.clarity = 17  # Can be clearer if simple
            scores.modularity = 10  # Poor modularity
            scores.maintainability = 12
            scores.regenerability = 14
        elif any(word in description for word in ["layered", "hierarchical", "structured"]):
            # Structured approaches balance all concerns
            scores.quality = 16
            scores.clarity = 15
            scores.modularity = 17
            scores.maintainability = 16
            scores.regenerability = 16
        else:
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


class IntegrationStrategyTemplate(DecisionTemplate):
    """Template for integration strategy decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score integration strategy options"""

        description = option_data.get("description", "").lower()

        scores = PhilosophyScores()

        if any(
            word in description for word in ["incremental", "gradual", "phased", "step-by-step"]
        ):
            # Incremental integration scores higher on maintainability
            scores.quality = 17
            scores.clarity = 16
            scores.modularity = 17
            scores.maintainability = 19  # Much safer
            scores.regenerability = 16
        elif any(
            word in description for word in ["big-bang", "all-at-once", "complete", "simultaneous"]
        ):
            # Big-bang integration is riskier
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 11  # Higher risk
            scores.regenerability = 13
        elif any(
            word in description for word in ["isolated", "sandboxed", "parallel", "independent"]
        ):
            # Isolated integration can be very clean
            scores.quality = 18
            scores.clarity = 17
            scores.modularity = 18
            scores.maintainability = 17
            scores.regenerability = 17
        else:
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


class CleanupTimingTemplate(DecisionTemplate):
    """Template for cleanup timing decisions"""

    def calculate_scores(self, option_data: Dict[str, Any]) -> PhilosophyScores:
        """Score cleanup timing options"""

        description = option_data.get("description", "").lower()
        option_id = option_data.get("id", "").lower()

        scores = PhilosophyScores()

        if "separate" in option_id or "separate" in description:
            # Separate cleanup PRs align with philosophy
            scores.quality = 18  # Better focused review
            scores.clarity = 17  # Single purpose
            scores.modularity = 19  # Perfect separation
            scores.maintainability = 16
            scores.regenerability = 15
        elif "immediate" in description or "inline" in description:
            # Immediate cleanup can be good if minimal
            scores.quality = 15
            scores.clarity = 14
            scores.modularity = 13  # Mixed concerns
            scores.maintainability = 14
            scores.regenerability = 13
        elif "defer" in description or "later" in description:
            # Deferred cleanup scores lower on quality
            scores.quality = 11  # Technical debt accumulates
            scores.clarity = 12
            scores.modularity = 12
            scores.maintainability = 10  # Harder to maintain
            scores.regenerability = 11
        else:
            scores.quality = 15
            scores.clarity = 15
            scores.modularity = 15
            scores.maintainability = 15
            scores.regenerability = 15

        return scores


# Example usage and demo functions
def create_example_pr_decision() -> DecisionResult:
    """Create an example PR organization decision"""

    framework = PhilosophyDecisionFramework()

    options = [
        {
            "id": "same_pr",
            "description": "Include quality improvements in same PR as feature",
            "rationale": "Faster delivery, single review process",
        },
        {
            "id": "separate_pr",
            "description": "Create separate PR for quality improvements",
            "rationale": "Better separation of concerns, focused reviews",
        },
    ]

    return framework.make_decision(
        context=DecisionContext.PR_ORGANIZATION,
        description="Quality improvements discovered during feature development",
        options=options,
    )


def create_example_feature_scope_decision() -> DecisionResult:
    """Create an example feature scope decision"""

    framework = PhilosophyDecisionFramework()

    options = [
        {
            "id": "minimal_mvp",
            "description": "Implement minimal viable product with core functionality",
            "estimated_effort": "2-3 days",
        },
        {
            "id": "comprehensive",
            "description": "Implement comprehensive solution with all edge cases",
            "estimated_effort": "1-2 weeks",
        },
    ]

    return framework.make_decision(
        context=DecisionContext.FEATURE_SCOPE,
        description="Authentication system implementation scope",
        options=options,
    )


def create_example_cleanup_timing_decision() -> DecisionResult:
    """Create an example cleanup timing decision"""

    framework = PhilosophyDecisionFramework()

    options = [
        {
            "id": "separate_pr",
            "description": "Create separate PR for code cleanup and quality improvements",
            "rationale": "Maintains separation of concerns, enables focused review",
        },
        {
            "id": "inline_cleanup",
            "description": "Include cleanup in current feature PR",
            "rationale": "Faster delivery, single review cycle",
        },
        {
            "id": "defer_cleanup",
            "description": "Defer cleanup to future sprint",
            "rationale": "Focus on feature delivery deadline",
        },
    ]

    return framework.make_decision(
        context=DecisionContext.CLEANUP_TIMING,
        description="Quality improvements discovered during feature development",
        options=options,
    )


def create_example_implementation_approach_decision() -> DecisionResult:
    """Create an example implementation approach decision"""

    framework = PhilosophyDecisionFramework()

    options = [
        {
            "id": "simple_approach",
            "description": "Simple straightforward implementation using existing patterns",
            "estimated_effort": "3-5 days",
            "risks": ["May need refactoring later for edge cases"],
        },
        {
            "id": "robust_approach",
            "description": "Robust extensible implementation with comprehensive error handling",
            "estimated_effort": "1-2 weeks",
            "risks": ["Higher complexity", "Longer development time"],
        },
        {
            "id": "complex_approach",
            "description": "Complex advanced implementation with sophisticated architecture",
            "estimated_effort": "2-3 weeks",
            "risks": ["High complexity", "Difficult to maintain", "Over-engineering"],
        },
    ]

    return framework.make_decision(
        context=DecisionContext.IMPLEMENTATION_APPROACH,
        description="API endpoint implementation strategy",
        options=options,
    )


def create_example_integration_strategy_decision() -> DecisionResult:
    """Create an example integration strategy decision"""

    framework = PhilosophyDecisionFramework()

    options = [
        {
            "id": "incremental_integration",
            "description": "Incremental phased integration with existing systems",
            "dependencies": ["System A migration", "API versioning"],
            "risks": ["Longer timeline", "Multiple deployment cycles"],
        },
        {
            "id": "big_bang_integration",
            "description": "Complete simultaneous integration with all systems",
            "dependencies": ["Full system downtime", "Coordinated deployment"],
            "risks": ["High risk", "Difficult rollback", "Complex testing"],
        },
        {
            "id": "isolated_integration",
            "description": "Isolated parallel integration with gradual traffic migration",
            "dependencies": ["Traffic routing infrastructure", "Monitoring setup"],
            "risks": ["Infrastructure complexity", "Data synchronization"],
        },
    ]

    return framework.make_decision(
        context=DecisionContext.INTEGRATION_STRATEGY,
        description="Third-party service integration approach",
        options=options,
    )


def demonstrate_philosophy_framework():
    """Demonstrate the philosophy decision framework with various scenarios"""

    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("=== Philosophy-Based Decision Framework Demo ===")

    # Example 1: PR Organization
    logger.info("1. PR Organization Decision:")
    pr_decision = create_example_pr_decision()
    logger.info(f"   Selected: {pr_decision.selected_option.description}")
    logger.info(f"   Score: {pr_decision.selected_option.philosophy_scores.total_score:.1f}/100")
    logger.info(f"   Rationale: {pr_decision.decision_rationale}")

    # Example 2: Feature Scope
    logger.info("2. Feature Scope Decision:")
    scope_decision = create_example_feature_scope_decision()
    logger.info(f"   Selected: {scope_decision.selected_option.description}")
    logger.info(f"   Score: {scope_decision.selected_option.philosophy_scores.total_score:.1f}/100")
    logger.info(f"   Rationale: {scope_decision.decision_rationale}")

    # Example 3: Cleanup Timing
    logger.info("3. Cleanup Timing Decision:")
    cleanup_decision = create_example_cleanup_timing_decision()
    logger.info(f"   Selected: {cleanup_decision.selected_option.description}")
    logger.info(f"   Score: {cleanup_decision.selected_option.philosophy_scores.total_score:.1f}/100")
    logger.info(f"   Rationale: {cleanup_decision.decision_rationale}")

    # Example 4: Implementation Approach
    logger.info("4. Implementation Approach Decision:")
    impl_decision = create_example_implementation_approach_decision()
    logger.info(f"   Selected: {impl_decision.selected_option.description}")
    logger.info(f"   Score: {impl_decision.selected_option.philosophy_scores.total_score:.1f}/100")
    logger.info(f"   Rationale: {impl_decision.decision_rationale}")

    # Example 5: Integration Strategy
    logger.info("5. Integration Strategy Decision:")
    integration_decision = create_example_integration_strategy_decision()
    logger.info(f"   Selected: {integration_decision.selected_option.description}")
    logger.info(f"   Score: {integration_decision.selected_option.philosophy_scores.total_score:.1f}/100")
    logger.info(f"   Rationale: {integration_decision.decision_rationale}")


if __name__ == "__main__":
    demonstrate_philosophy_framework()
