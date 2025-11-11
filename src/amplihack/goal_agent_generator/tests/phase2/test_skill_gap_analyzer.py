"""Tests for SkillGapAnalyzer."""

import uuid
from pathlib import Path

import pytest

from ...models import ExecutionPlan, PlanPhase, SkillDefinition
from ...phase2.skill_gap_analyzer import SkillGapAnalyzer


class TestSkillGapAnalyzer:
    """Tests for SkillGapAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return SkillGapAnalyzer()

    @pytest.fixture
    def execution_plan(self):
        """Create sample execution plan."""
        phases = [
            PlanPhase(
                name="Data Collection",
                description="Collect data from sources",
                required_capabilities=["collect", "parse", "validate"],
                estimated_duration="10 minutes",
            ),
            PlanPhase(
                name="Data Processing",
                description="Process and transform data",
                required_capabilities=["transform", "analyze"],
                estimated_duration="15 minutes",
            ),
            PlanPhase(
                name="Testing",
                description="Test results",
                required_capabilities=["test", "verify"],
                estimated_duration="5 minutes",
            ),
        ]

        return ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=phases,
            total_estimated_duration="30 minutes",
            required_skills=["data-processor", "tester"],
        )

    @pytest.fixture
    def full_coverage_skills(self):
        """Skills that fully cover requirements."""
        return [
            SkillDefinition(
                name="data-processor",
                source_path=Path("test.md"),
                capabilities=["collect", "parse", "validate", "transform", "analyze"],
                description="Data processing skill",
                content="# Data Processor",
                match_score=0.9,
            ),
            SkillDefinition(
                name="tester",
                source_path=Path("test.md"),
                capabilities=["test", "verify"],
                description="Testing skill",
                content="# Tester",
                match_score=0.8,
            ),
        ]

    @pytest.fixture
    def partial_coverage_skills(self):
        """Skills that partially cover requirements."""
        return [
            SkillDefinition(
                name="data-collector",
                source_path=Path("test.md"),
                capabilities=["collect", "parse"],
                description="Data collection skill",
                content="# Data Collector",
                match_score=0.7,
            ),
        ]

    def test_analyze_gaps_with_full_coverage(
        self, analyzer, execution_plan, full_coverage_skills
    ):
        """Test gap analysis with full coverage."""
        report = analyzer.analyze_gaps(execution_plan, full_coverage_skills)

        assert report.execution_plan_id == execution_plan.goal_id
        assert report.coverage_percentage == 100.0
        assert len(report.missing_capabilities) == 0
        assert report.recommendation == "use_existing"

    def test_analyze_gaps_with_partial_coverage(
        self, analyzer, execution_plan, partial_coverage_skills
    ):
        """Test gap analysis with partial coverage."""
        report = analyzer.analyze_gaps(execution_plan, partial_coverage_skills)

        assert report.execution_plan_id == execution_plan.goal_id
        assert report.coverage_percentage < 100.0
        assert len(report.missing_capabilities) > 0
        assert "validate" in report.missing_capabilities
        assert "transform" in report.missing_capabilities

    def test_analyze_gaps_with_no_coverage(self, analyzer, execution_plan):
        """Test gap analysis with no coverage."""
        report = analyzer.analyze_gaps(execution_plan, [])

        assert report.coverage_percentage == 0.0
        assert len(report.missing_capabilities) > 0
        assert report.recommendation in ["generate_custom", "mixed"]

    def test_collect_required_capabilities(self, analyzer, execution_plan):
        """Test collecting required capabilities."""
        capabilities = analyzer._collect_required_capabilities(execution_plan)

        assert "collect" in capabilities
        assert "parse" in capabilities
        assert "validate" in capabilities
        assert "transform" in capabilities
        assert "analyze" in capabilities
        assert "test" in capabilities
        assert "verify" in capabilities

    def test_collect_available_capabilities(self, analyzer, full_coverage_skills):
        """Test collecting available capabilities."""
        capabilities = analyzer._collect_available_capabilities(full_coverage_skills)

        assert "collect" in capabilities
        assert "parse" in capabilities
        assert "validate" in capabilities
        assert "test" in capabilities
        assert "verify" in capabilities

    def test_calculate_coverage(self, analyzer):
        """Test coverage calculation."""
        required = ["a", "b", "c", "d"]
        available = ["a", "b"]

        coverage = analyzer._calculate_coverage(required, available)

        assert coverage == 50.0

    def test_calculate_coverage_full(self, analyzer):
        """Test coverage calculation with full coverage."""
        required = ["a", "b", "c"]
        available = ["a", "b", "c", "d", "e"]

        coverage = analyzer._calculate_coverage(required, available)

        assert coverage == 100.0

    def test_calculate_coverage_empty_required(self, analyzer):
        """Test coverage calculation with empty required."""
        coverage = analyzer._calculate_coverage([], ["a", "b"])

        assert coverage == 100.0

    def test_organize_gaps_by_phase(
        self, analyzer, execution_plan, partial_coverage_skills
    ):
        """Test organizing gaps by phase."""
        available = analyzer._collect_available_capabilities(partial_coverage_skills)
        gaps = analyzer._organize_gaps_by_phase(execution_plan, available)

        # Should have gaps in Data Collection and Data Processing phases
        assert "Data Collection" in gaps
        assert "Data Processing" in gaps

        # Testing phase should have gaps too
        assert "Testing" in gaps

    def test_rank_by_criticality(self, analyzer):
        """Test ranking capabilities by criticality."""
        missing = ["test", "document", "execute", "optimize"]

        ranked = analyzer._rank_by_criticality(missing)

        # Should be list of tuples (capability, score)
        assert len(ranked) == 4
        assert all(isinstance(item, tuple) for item in ranked)
        assert all(len(item) == 2 for item in ranked)

        # Scores should be descending
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_categorize_capability_core(self, analyzer):
        """Test categorizing core capabilities."""
        assert analyzer._categorize_capability("execute") == "core"
        assert analyzer._categorize_capability("process") == "core"
        assert analyzer._categorize_capability("build") == "core"

    def test_categorize_capability_validation(self, analyzer):
        """Test categorizing validation capabilities."""
        assert analyzer._categorize_capability("test") == "validation"
        assert analyzer._categorize_capability("validate") == "validation"
        assert analyzer._categorize_capability("verify") == "validation"

    def test_categorize_capability_documentation(self, analyzer):
        """Test categorizing documentation capabilities."""
        assert analyzer._categorize_capability("document") == "documentation"
        assert analyzer._categorize_capability("report") == "documentation"

    def test_categorize_capability_unknown(self, analyzer):
        """Test categorizing unknown capabilities defaults to core."""
        assert analyzer._categorize_capability("unknown-thing") == "core"

    def test_determine_recommendation_full_coverage(self, analyzer):
        """Test recommendation with full coverage."""
        recommendation = analyzer._determine_recommendation(100.0, [], [])

        assert recommendation == "use_existing"

    def test_determine_recommendation_very_low_coverage(self, analyzer):
        """Test recommendation with very low coverage."""
        recommendation = analyzer._determine_recommendation(
            30.0, ["cap1", "cap2"], [("cap1", 0.5)]
        )

        assert recommendation == "generate_custom"

    def test_determine_recommendation_high_coverage(self, analyzer):
        """Test recommendation with high coverage."""
        recommendation = analyzer._determine_recommendation(
            75.0, ["cap1"], [("cap1", 0.3)]
        )

        assert recommendation == "use_existing"

    def test_determine_recommendation_critical_gaps(self, analyzer):
        """Test recommendation with critical gaps."""
        recommendation = analyzer._determine_recommendation(
            60.0, ["execute"], [("execute", 1.0)]
        )

        assert recommendation == "generate_custom"

    def test_gap_report_validation(self):
        """Test gap report validation."""
        from ...models import SkillGapReport

        # Valid report
        report = SkillGapReport(
            execution_plan_id=uuid.uuid4(),
            coverage_percentage=75.0,
            missing_capabilities=["test"],
            gaps_by_phase={"Phase1": ["test"]},
            criticality_ranking=[("test", 0.8)],
            recommendation="use_existing",
        )

        assert report.coverage_percentage == 75.0

        # Invalid coverage
        with pytest.raises(ValueError):
            SkillGapReport(
                execution_plan_id=uuid.uuid4(),
                coverage_percentage=150.0,  # Invalid
                missing_capabilities=[],
                gaps_by_phase={},
                criticality_ranking=[],
                recommendation="use_existing",
            )
