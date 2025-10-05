"""
Tests for the philosophy-based decision framework.

Tests cover the core decision framework, scoring system, decision templates,
and integration with auto-mode orchestrator.
"""

import pytest

from src.amplihack.auto_mode.philosophy_decision import (
    CleanupTimingTemplate,
    CodeOrganizationTemplate,
    DecisionContext,
    DecisionOption,
    DecisionResult,
    FeatureScopeTemplate,
    ImplementationApproachTemplate,
    IntegrationStrategyTemplate,
    PhilosophyDecisionFramework,
    PhilosophyScores,
    PROrganizationTemplate,
    RefactoringTemplate,
    TestingStrategyTemplate,
    create_example_cleanup_timing_decision,
    create_example_feature_scope_decision,
    create_example_pr_decision,
)


class TestPhilosophyScores:
    """Test the PhilosophyScores dataclass"""

    def test_total_score_calculation(self):
        """Test that total score is calculated correctly"""
        scores = PhilosophyScores(
            quality=15.0, clarity=18.0, modularity=12.0, maintainability=16.0, regenerability=14.0
        )
        assert scores.total_score == 75.0

    def test_to_dict_conversion(self):
        """Test conversion to dictionary format"""
        scores = PhilosophyScores(
            quality=10.0, clarity=15.0, modularity=20.0, maintainability=12.0, regenerability=8.0
        )

        result = scores.to_dict()
        expected = {
            "quality": 10.0,
            "clarity": 15.0,
            "modularity": 20.0,
            "maintainability": 12.0,
            "regenerability": 8.0,
            "total": 65.0,
        }
        assert result == expected

    def test_zero_scores(self):
        """Test handling of zero scores"""
        scores = PhilosophyScores()
        assert scores.total_score == 0.0

    def test_maximum_scores(self):
        """Test maximum possible scores"""
        scores = PhilosophyScores(
            quality=20.0, clarity=20.0, modularity=20.0, maintainability=20.0, regenerability=20.0
        )
        assert scores.total_score == 100.0


class TestDecisionOption:
    """Test the DecisionOption dataclass"""

    def test_decision_option_creation(self):
        """Test creating a decision option"""
        scores = PhilosophyScores(
            quality=15, clarity=16, modularity=17, maintainability=18, regenerability=14
        )
        option = DecisionOption(
            id="test_option",
            description="Test option description",
            philosophy_scores=scores,
            rationale="Test rationale",
            estimated_effort="2-3 days",
            dependencies=["dep1", "dep2"],
            risks=["risk1", "risk2"],
        )

        assert option.id == "test_option"
        assert option.description == "Test option description"
        assert option.philosophy_scores.total_score == 80.0
        assert option.rationale == "Test rationale"
        assert option.estimated_effort == "2-3 days"
        assert option.dependencies == ["dep1", "dep2"]
        assert option.risks == ["risk1", "risk2"]

    def test_to_dict_conversion(self):
        """Test conversion to dictionary format"""
        scores = PhilosophyScores(
            quality=15, clarity=16, modularity=17, maintainability=18, regenerability=14
        )
        option = DecisionOption(
            id="test_option", description="Test option", philosophy_scores=scores
        )

        result = option.to_dict()
        assert result["id"] == "test_option"
        assert result["description"] == "Test option"
        assert result["philosophy_scores"]["total"] == 80.0


class TestPhilosophyDecisionFramework:
    """Test the core philosophy decision framework"""

    @pytest.fixture
    def framework(self):
        """Create a philosophy decision framework instance"""
        return PhilosophyDecisionFramework()

    def test_make_decision_with_explicit_scores(self, framework):
        """Test making a decision with explicitly provided scores"""
        options = [
            {
                "id": "option_a",
                "description": "First option",
                "philosophy_scores": {
                    "quality": 15,
                    "clarity": 16,
                    "modularity": 14,
                    "maintainability": 15,
                    "regenerability": 13,
                },
            },
            {
                "id": "option_b",
                "description": "Second option",
                "philosophy_scores": {
                    "quality": 18,
                    "clarity": 17,
                    "modularity": 19,
                    "maintainability": 16,
                    "regenerability": 15,
                },
            },
        ]

        result = framework.make_decision(
            context=DecisionContext.GENERAL, description="Test decision", options=options
        )

        assert result.selected_option.id == "option_b"
        assert result.selected_option.philosophy_scores.total_score == 85.0
        assert result.confidence > 0.0

    def test_make_decision_with_string_context(self, framework):
        """Test making a decision with string context"""
        options = [
            {"id": "simple", "description": "Simple approach"},
            {"id": "complex", "description": "Complex approach"},
        ]

        result = framework.make_decision(
            context="general", description="Test decision", options=options
        )

        assert result.context == DecisionContext.GENERAL
        assert result.selected_option is not None

    def test_make_decision_invalid_context(self, framework):
        """Test making a decision with invalid context string"""
        options = [{"id": "option1", "description": "First option"}]

        result = framework.make_decision(
            context="invalid_context", description="Test decision", options=options
        )

        assert result.context == DecisionContext.GENERAL

    def test_confidence_calculation(self, framework):
        """Test confidence calculation with different score separations"""
        # High separation should result in high confidence
        options_high_sep = [
            {
                "id": "low_score",
                "description": "Low scoring option",
                "philosophy_scores": {
                    "quality": 5,
                    "clarity": 5,
                    "modularity": 5,
                    "maintainability": 5,
                    "regenerability": 5,
                },
            },
            {
                "id": "high_score",
                "description": "High scoring option",
                "philosophy_scores": {
                    "quality": 20,
                    "clarity": 20,
                    "modularity": 20,
                    "maintainability": 20,
                    "regenerability": 20,
                },
            },
        ]

        result_high = framework.make_decision(
            context=DecisionContext.GENERAL,
            description="High separation test",
            options=options_high_sep,
        )

        # Low separation should result in lower confidence
        options_low_sep = [
            {
                "id": "option_a",
                "description": "Close option A",
                "philosophy_scores": {
                    "quality": 15,
                    "clarity": 15,
                    "modularity": 15,
                    "maintainability": 15,
                    "regenerability": 15,
                },
            },
            {
                "id": "option_b",
                "description": "Close option B",
                "philosophy_scores": {
                    "quality": 16,
                    "clarity": 15,
                    "modularity": 15,
                    "maintainability": 15,
                    "regenerability": 15,
                },
            },
        ]

        result_low = framework.make_decision(
            context=DecisionContext.GENERAL,
            description="Low separation test",
            options=options_low_sep,
        )

        assert result_high.confidence > result_low.confidence

    def test_single_option_confidence(self, framework):
        """Test confidence with single option"""
        options = [{"id": "only_option", "description": "Only available option"}]

        result = framework.make_decision(
            context=DecisionContext.GENERAL, description="Single option test", options=options
        )

        assert result.confidence == 1.0

    def test_default_scoring_heuristics(self, framework):
        """Test default scoring heuristics"""
        options = [
            {"id": "simple_clean", "description": "Simple clean focused approach"},
            {"id": "complex_mixed", "description": "Complex mixed combined solution"},
        ]

        result = framework.make_decision(
            context=DecisionContext.GENERAL, description="Heuristics test", options=options
        )

        # Simple/clean should score higher than complex/mixed
        assert result.selected_option.id == "simple_clean"


class TestDecisionTemplates:
    """Test the decision templates for specific contexts"""

    def test_pr_organization_template(self):
        """Test PR organization decision template"""
        template = PROrganizationTemplate()

        separate_scores = template.calculate_scores(
            {"id": "separate_pr", "description": "Create separate PR for improvements"}
        )

        combined_scores = template.calculate_scores(
            {"id": "same_pr", "description": "Include improvements in same PR"}
        )

        # Separate PRs should score higher
        assert separate_scores.total_score > combined_scores.total_score
        assert separate_scores.modularity > combined_scores.modularity
        assert separate_scores.clarity > combined_scores.clarity

    def test_feature_scope_template(self):
        """Test feature scope decision template"""
        template = FeatureScopeTemplate()

        minimal_scores = template.calculate_scores(
            {"description": "Minimal basic core functionality"}
        )

        comprehensive_scores = template.calculate_scores(
            {"description": "Comprehensive complete full solution"}
        )

        # Minimal should score higher on clarity and maintainability
        assert minimal_scores.clarity > comprehensive_scores.clarity
        assert minimal_scores.maintainability > comprehensive_scores.maintainability

    def test_refactoring_template(self):
        """Test refactoring approach decision template"""
        template = RefactoringTemplate()

        incremental_scores = template.calculate_scores(
            {"description": "Incremental gradual step-by-step refactoring"}
        )

        complete_scores = template.calculate_scores(
            {"description": "Complete rewrite of the entire system"}
        )

        # Incremental should score higher on maintainability
        assert incremental_scores.maintainability > complete_scores.maintainability

    def test_testing_strategy_template(self):
        """Test testing strategy decision template"""
        template = TestingStrategyTemplate()

        tdd_scores = template.calculate_scores({"description": "Test-driven development approach"})

        test_after_scores = template.calculate_scores(
            {"description": "Write tests after implementation"}
        )

        # TDD should score higher on quality and maintainability
        assert tdd_scores.quality > test_after_scores.quality
        assert tdd_scores.maintainability > test_after_scores.maintainability

    def test_implementation_approach_template(self):
        """Test implementation approach decision template"""
        template = ImplementationApproachTemplate()

        simple_scores = template.calculate_scores(
            {"description": "Simple straightforward minimal implementation"}
        )

        complex_scores = template.calculate_scores(
            {"description": "Complex advanced sophisticated solution"}
        )

        # Simple should score higher on clarity and regenerability
        assert simple_scores.clarity > complex_scores.clarity
        assert simple_scores.regenerability > complex_scores.regenerability

    def test_code_organization_template(self):
        """Test code organization decision template"""
        template = CodeOrganizationTemplate()

        modular_scores = template.calculate_scores(
            {"description": "Modular separate isolated components"}
        )

        monolithic_scores = template.calculate_scores(
            {"description": "Monolithic single combined structure"}
        )

        # Modular should score much higher on modularity
        assert modular_scores.modularity > monolithic_scores.modularity
        assert modular_scores.maintainability > monolithic_scores.maintainability

    def test_integration_strategy_template(self):
        """Test integration strategy decision template"""
        template = IntegrationStrategyTemplate()

        incremental_scores = template.calculate_scores(
            {"description": "Incremental phased step-by-step integration"}
        )

        big_bang_scores = template.calculate_scores(
            {"description": "Big-bang all-at-once complete integration"}
        )

        # Incremental should score higher on maintainability
        assert incremental_scores.maintainability > big_bang_scores.maintainability

    def test_cleanup_timing_template(self):
        """Test cleanup timing decision template"""
        template = CleanupTimingTemplate()

        separate_scores = template.calculate_scores(
            {"id": "separate_pr", "description": "Create separate cleanup PR"}
        )

        defer_scores = template.calculate_scores({"description": "Defer cleanup to later sprint"})

        # Separate cleanup should score much higher
        assert separate_scores.total_score > defer_scores.total_score
        assert separate_scores.quality > defer_scores.quality
        assert separate_scores.modularity > defer_scores.modularity


class TestExampleDecisions:
    """Test the example decision functions"""

    def test_example_pr_decision(self):
        """Test the example PR organization decision"""
        result = create_example_pr_decision()

        assert result.context == DecisionContext.PR_ORGANIZATION
        assert result.selected_option is not None
        assert len(result.options) == 2
        # Should select separate PR due to better philosophy alignment
        assert result.selected_option.id == "separate_pr"

    def test_example_feature_scope_decision(self):
        """Test the example feature scope decision"""
        result = create_example_feature_scope_decision()

        assert result.context == DecisionContext.FEATURE_SCOPE
        assert result.selected_option is not None
        assert len(result.options) == 2
        # Should prefer minimal approach for better clarity and maintainability
        assert result.selected_option.id == "minimal_mvp"

    def test_example_cleanup_timing_decision(self):
        """Test the example cleanup timing decision"""
        result = create_example_cleanup_timing_decision()

        assert result.context == DecisionContext.CLEANUP_TIMING
        assert result.selected_option is not None
        assert len(result.options) == 3
        # Should select separate PR for better modularity
        assert result.selected_option.id == "separate_pr"


class TestDecisionResult:
    """Test the DecisionResult dataclass"""

    def test_decision_result_to_dict(self):
        """Test conversion of decision result to dictionary"""
        scores = PhilosophyScores(
            quality=15, clarity=16, modularity=17, maintainability=18, regenerability=14
        )
        option = DecisionOption(
            id="test_option", description="Test option", philosophy_scores=scores
        )

        result = DecisionResult(
            context=DecisionContext.GENERAL,
            description="Test decision",
            options=[option],
            selected_option=option,
            decision_rationale="Test rationale",
            confidence=0.85,
        )

        result_dict = result.to_dict()

        assert result_dict["context"] == "general"
        assert result_dict["description"] == "Test decision"
        assert result_dict["confidence"] == 0.85
        assert len(result_dict["options"]) == 1
        assert result_dict["selected_option"]["id"] == "test_option"


class TestDecisionFrameworkIntegration:
    """Test integration scenarios with the decision framework"""

    def test_philosophy_score_preference_on_ties(self):
        """Test that simplicity is preferred when scores are close"""
        framework = PhilosophyDecisionFramework()

        options = [
            {
                "id": "complex_option",
                "description": "Complex comprehensive solution",
                "philosophy_scores": {
                    "quality": 16,
                    "clarity": 12,
                    "modularity": 16,
                    "maintainability": 14,
                    "regenerability": 13,
                },  # Total: 71
            },
            {
                "id": "simple_option",
                "description": "Simple clear focused approach",
                "philosophy_scores": {
                    "quality": 14,
                    "clarity": 18,
                    "modularity": 15,
                    "maintainability": 15,
                    "regenerability": 16,
                },  # Total: 78 (clearly better)
            },
        ]

        result = framework.make_decision(
            context=DecisionContext.GENERAL, description="Close scores test", options=options
        )

        # Should select the higher scoring option
        assert result.selected_option.id == "simple_option"

    def test_rationale_generation(self):
        """Test that decision rationale is generated correctly"""
        framework = PhilosophyDecisionFramework()

        options = [
            {
                "id": "low_quality",
                "description": "Low quality option",
                "philosophy_scores": {
                    "quality": 5,
                    "clarity": 10,
                    "modularity": 8,
                    "maintainability": 7,
                    "regenerability": 6,
                },
            },
            {
                "id": "high_quality",
                "description": "High quality option",
                "philosophy_scores": {
                    "quality": 19,
                    "clarity": 17,
                    "modularity": 18,
                    "maintainability": 16,
                    "regenerability": 15,
                },
                "rationale": "Custom rationale for this option",
            },
        ]

        result = framework.make_decision(
            context=DecisionContext.GENERAL, description="Rationale test", options=options
        )

        assert result.selected_option.id == "high_quality"
        assert "High quality option" in result.decision_rationale
        assert "quality (19.0/20)" in result.decision_rationale
        assert "Custom rationale for this option" in result.decision_rationale

    def test_decision_context_handling(self):
        """Test handling of different decision contexts"""
        framework = PhilosophyDecisionFramework()

        # Test each decision context type
        contexts = [
            DecisionContext.PR_ORGANIZATION,
            DecisionContext.FEATURE_SCOPE,
            DecisionContext.REFACTORING_APPROACH,
            DecisionContext.TESTING_STRATEGY,
            DecisionContext.IMPLEMENTATION_APPROACH,
            DecisionContext.CODE_ORGANIZATION,
            DecisionContext.INTEGRATION_STRATEGY,
            DecisionContext.CLEANUP_TIMING,
            DecisionContext.GENERAL,
        ]

        for context in contexts:
            options = [
                {"id": "option1", "description": "First option"},
                {"id": "option2", "description": "Second option"},
            ]

            result = framework.make_decision(
                context=context, description=f"Test {context.value} decision", options=options
            )

            assert result.context == context
            assert result.selected_option is not None


if __name__ == "__main__":
    # Run with: python -m pytest tests/auto_mode/test_philosophy_decision.py -v
    pytest.main([__file__, "-v"])
