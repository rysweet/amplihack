"""Tests for prompt analyzer."""

import tempfile
from pathlib import Path

import pytest

from ..models import GoalDefinition
from ..prompt_analyzer import PromptAnalyzer


class TestPromptAnalyzer:
    """Tests for PromptAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return PromptAnalyzer()

    def test_analyze_simple_prompt(self, analyzer):
        """Test analyzing simple prompt."""
        prompt = "Automate code review process"
        result = analyzer.analyze_text(prompt)

        assert isinstance(result, GoalDefinition)
        assert "automate" in result.goal.lower() or "code review" in result.goal.lower()
        assert result.domain in analyzer.DOMAIN_KEYWORDS
        assert result.complexity in ["simple", "moderate", "complex"]

    def test_analyze_complex_prompt(self, analyzer):
        """Test analyzing complex prompt with multiple sections."""
        prompt = """
        # Goal: Automate Security Analysis

        Objective: Create an automated security scanning pipeline

        Constraints:
        - Must complete within 30 minutes
        - Cannot modify existing code
        - Should not require manual intervention

        Success Criteria:
        - All vulnerabilities detected
        - Report generated automatically
        - Alerts sent to team
        """

        result = analyzer.analyze_text(prompt)

        assert "security" in result.goal.lower() or "automate" in result.goal.lower()
        assert result.domain == "security-analysis"
        assert len(result.constraints) > 0
        assert len(result.success_criteria) > 0

    def test_extract_goal_from_heading(self, analyzer):
        """Test extracting goal from markdown heading."""
        prompt = "# Automate deployment process\n\nSome details here"
        goal = analyzer._extract_goal(prompt)

        assert "deployment" in goal.lower()

    def test_extract_goal_from_explicit_marker(self, analyzer):
        """Test extracting goal with explicit Goal: marker."""
        prompt = "Goal: Build automated testing framework"
        goal = analyzer._extract_goal(prompt)

        assert "testing" in goal.lower() or "automated" in goal.lower()

    def test_classify_domain_data_processing(self, analyzer):
        """Test domain classification for data processing."""
        prompt = "Process and transform large datasets"
        domain = analyzer._classify_domain(prompt)

        assert domain == "data-processing"

    def test_classify_domain_security(self, analyzer):
        """Test domain classification for security."""
        prompt = "Scan codebase for security vulnerabilities"
        domain = analyzer._classify_domain(prompt)

        assert domain == "security-analysis"

    def test_classify_domain_automation(self, analyzer):
        """Test domain classification for automation."""
        prompt = "Automate workflow execution and scheduling"
        domain = analyzer._classify_domain(prompt)

        assert domain == "automation"

    def test_extract_constraints(self, analyzer):
        """Test extracting constraints."""
        prompt = """
        Requirement: Must complete in under 10 minutes
        Constraint: Cannot access external APIs
        Must not modify existing files
        """

        constraints = analyzer._extract_constraints(prompt)

        assert len(constraints) > 0
        assert any("10 minutes" in c.lower() for c in constraints)

    def test_extract_success_criteria(self, analyzer):
        """Test extracting success criteria."""
        prompt = """
        Success when: All tests pass
        Should produce: Detailed report
        Output: JSON file with results
        """

        criteria = analyzer._extract_success_criteria(prompt)

        assert len(criteria) > 0
        assert any("test" in c.lower() or "report" in c.lower() for c in criteria)

    def test_determine_complexity_simple(self, analyzer):
        """Test complexity determination for simple tasks."""
        prompt = "Single quick task"
        complexity = analyzer._determine_complexity(prompt)

        assert complexity == "simple"

    def test_determine_complexity_complex(self, analyzer):
        """Test complexity determination for complex tasks."""
        prompt = """
        Complex multi-stage distributed processing pipeline
        with sophisticated error handling and advanced features.
        Step 1: Setup
        Step 2: Process
        Step 3: Validate
        Step 4: Deploy
        """

        complexity = analyzer._determine_complexity(prompt)

        assert complexity == "complex"

    def test_extract_context_timeframe(self, analyzer):
        """Test extracting timeframe from context."""
        prompt = "Complete within 30 minutes"
        context = analyzer._extract_context(prompt)

        assert "timeframe" in context
        assert "30" in context["timeframe"]

    def test_extract_context_priority(self, analyzer):
        """Test extracting priority from context."""
        prompt_urgent = "Urgent: Fix critical bug immediately"
        context_urgent = analyzer._extract_context(prompt_urgent)

        assert context_urgent["priority"] == "high"

        prompt_low = "Eventually add this feature when possible"
        context_low = analyzer._extract_context(prompt_low)

        assert context_low["priority"] == "low"

    def test_extract_context_scale(self, analyzer):
        """Test extracting scale from context."""
        prompt_large = "Enterprise-scale production deployment"
        context_large = analyzer._extract_context(prompt_large)

        assert context_large["scale"] == "large"

        prompt_small = "Small simple utility script"
        context_small = analyzer._extract_context(prompt_small)

        assert context_small["scale"] == "small"

    def test_analyze_from_file(self, analyzer):
        """Test analyzing prompt from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Automate Testing\n\nCreate automated test suite")
            temp_path = Path(f.name)

        try:
            result = analyzer.analyze(temp_path)

            assert isinstance(result, GoalDefinition)
            assert "test" in result.goal.lower()
            assert result.domain in ("testing", "automation")  # "Automate" keyword triggers automation
        finally:
            temp_path.unlink()

    def test_analyze_missing_file_raises_error(self, analyzer):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            analyzer.analyze(Path("/nonexistent/file.md"))

    def test_analyze_empty_text_raises_error(self, analyzer):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            analyzer.analyze_text("")

    def test_analyze_whitespace_only_raises_error(self, analyzer):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            analyzer.analyze_text("   \n\n   \t  ")
