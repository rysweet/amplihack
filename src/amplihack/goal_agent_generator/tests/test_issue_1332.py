"""
Test for issue #1332: Bundle name validation fails for certain scenarios.

This test verifies that the Multi-Container Application scenario and similar
edge cases now work correctly with the sanitized bundle name generation.
"""

import pytest
from ..models import GoalDefinition
from ..agent_assembler import AgentAssembler
from ..utils import sanitize_bundle_name


class TestIssue1332:
    """Test cases specifically for issue #1332."""

    def test_multi_container_application_scenario(self):
        """
        Test the specific failing scenario from issue #1332.

        The scenario "Multi-Container Application" was generating a bundle name
        that failed validation. This should now work correctly.
        """
        # Simulate what would come from the scenario file
        goal_def = GoalDefinition(
            raw_prompt="Deploy and manage a multi-container application",
            goal="Deploy multi-container application to Kubernetes",
            domain="deployment",
            complexity="moderate",
        )

        assembler = AgentAssembler()
        bundle_name = assembler._generate_bundle_name(goal_def)

        # Should generate a valid name
        assert bundle_name is not None
        assert 3 <= len(bundle_name) <= 50
        assert bundle_name.endswith("-agent")

    def test_direct_sanitization_of_scenario_name(self):
        """Test direct sanitization of 'Multi-Container Application'."""
        result = sanitize_bundle_name("Multi-Container Application", suffix="-agent")

        # Should be valid
        assert result == "multi-container-application-agent"
        assert 3 <= len(result) <= 50

    def test_various_problematic_scenario_names(self):
        """Test various scenario names that might cause issues."""
        problematic_names = [
            "Multi-Container Application",
            "CI/CD Pipeline Automation",
            "Data Processing & ETL",
            "Security Vulnerability Scanning!",
            "Real-time Monitoring System (24/7)",
            "A",  # Too short
            "Very Long Scenario Name That Exceeds Maximum Length Requirements" * 2,  # Too long
            "___special___characters___",
            "123 Numeric Start",
        ]

        for scenario_name in problematic_names:
            # Each should generate a valid name
            result = sanitize_bundle_name(scenario_name, suffix="-agent")
            assert 3 <= len(result) <= 50, f"Failed for: {scenario_name}"
            assert not result.startswith("-")
            assert not result.endswith("--")

    def test_assembler_integration_with_edge_case_goals(self):
        """Test assembler with edge case goal definitions."""
        edge_cases = [
            {
                "goal": "Deploy Multi-Container Application",
                "domain": "deployment",
            },
            {
                "goal": "a",  # Minimal goal
                "domain": "testing",
            },
            {
                "goal": "Very complex goal with many words that should be truncated properly",
                "domain": "automation-testing-deployment-monitoring",
            },
        ]

        assembler = AgentAssembler()

        for case in edge_cases:
            goal_def = GoalDefinition(
                raw_prompt=case["goal"],
                goal=case["goal"],
                domain=case["domain"],
                complexity="moderate",
            )

            # Should not raise ValueError
            bundle_name = assembler._generate_bundle_name(goal_def)

            # Should be valid
            assert bundle_name is not None
            assert 3 <= len(bundle_name) <= 50
