"""Tests for Issue #1929 - Fix command integration with DEFAULT_WORKFLOW.

These tests verify that /fix command and fix-agent have been properly integrated
with DEFAULT_WORKFLOW.md, removing mode-based execution in favor of workflow orchestration.

All 21 tests validate the completed implementation and should PASS.
"""

import re
from pathlib import Path

import pytest


class TestFixCommandWorkflowIntegration:
    """Test suite for fix.md DEFAULT_WORKFLOW integration"""

    @pytest.fixture
    def fix_command_path(self):
        """Path to fix command file"""
        return Path(__file__).parent.parent / ".claude" / "commands" / "amplihack" / "fix.md"

    @pytest.fixture
    def fix_command_content(self, fix_command_path):
        """Read fix command content"""
        return fix_command_path.read_text()

    def test_fix_command_file_exists(self, fix_command_path):
        """Test that fix.md exists"""
        assert fix_command_path.exists(), f"Fix command file not found at {fix_command_path}"

    def test_fix_command_version_2_0_0(self, fix_command_content):
        """Test fix.md has version 2.0.0 in frontmatter"""
        version_match = re.search(r'version:\s*"?2\.0\.0"?', fix_command_content)
        assert version_match is not None, "fix.md should have version 2.0.0 in frontmatter"

    def test_fix_command_no_mode_selection(self, fix_command_content):
        """Test fix.md does NOT contain mode selection logic (QUICK, DIAGNOSTIC, COMPREHENSIVE)"""
        mode_keywords = ["QUICK mode", "DIAGNOSTIC mode", "COMPREHENSIVE mode", "mode selection"]

        for keyword in mode_keywords:
            assert keyword not in fix_command_content, (
                f"fix.md should NOT contain '{keyword}' - modes should be removed"
            )

    def test_fix_command_has_workflow_integration(self, fix_command_content):
        """Test fix.md DOES contain DEFAULT_WORKFLOW integration"""
        workflow_indicators = [
            "DEFAULT_WORKFLOW",
            "workflow orchestration",
            "22 steps",
            "Step 1",
            "Step 22",
        ]

        found_indicators = [ind for ind in workflow_indicators if ind in fix_command_content]
        assert len(found_indicators) >= 3, (
            f"fix.md should reference DEFAULT_WORKFLOW integration. Found: {found_indicators}"
        )

    def test_fix_command_patterns_as_context(self, fix_command_content):
        """Test fix.md describes patterns as context (not modes)"""
        context_indicators = [
            "pattern detection",
            "context",
            "specialized agent",
            "pattern-specific",
        ]

        found_indicators = [ind for ind in context_indicators if ind in fix_command_content]
        assert len(found_indicators) >= 2, (
            f"fix.md should describe patterns as context. Found: {found_indicators}"
        )

    def test_fix_command_single_workflow_path(self, fix_command_content):
        """Test fix.md emphasizes 'single workflow path' (ruthless simplicity)"""
        simplicity_indicators = ["single workflow", "one path", "standard workflow", "no branching"]

        found_indicators = [ind for ind in simplicity_indicators if ind in fix_command_content]
        assert len(found_indicators) >= 1, (
            f"fix.md should emphasize single workflow path. Found: {found_indicators}"
        )

    def test_fix_command_references_all_22_steps(self, fix_command_content):
        """Test fix.md references all 22 workflow steps"""
        # Check for reference to 22 steps
        step_count_match = re.search(r"22\s+steps?", fix_command_content, re.IGNORECASE)
        assert step_count_match is not None, "fix.md should reference all 22 workflow steps"

    def test_fix_command_workflow_invocation(self, fix_command_content):
        """Test fix.md has correct frontmatter for workflow invocation"""
        # Check for invokes or invoked_by in frontmatter
        frontmatter_match = re.search(
            r"(?:invokes|invoked_by):\s*(?:DEFAULT_WORKFLOW|workflow)",
            fix_command_content,
            re.IGNORECASE,
        )
        assert frontmatter_match is not None, (
            "fix.md should have workflow invocation in frontmatter"
        )


class TestFixAgentWorkflowIntegration:
    """Test suite for fix-agent.md DEFAULT_WORKFLOW integration"""

    @pytest.fixture
    def fix_agent_path(self):
        """Path to fix agent file"""
        return (
            Path(__file__).parent.parent
            / ".claude"
            / "agents"
            / "amplihack"
            / "specialized"
            / "fix-agent.md"
        )

    @pytest.fixture
    def fix_agent_content(self, fix_agent_path):
        """Read fix agent content"""
        return fix_agent_path.read_text()

    def test_fix_agent_file_exists(self, fix_agent_path):
        """Test that fix-agent.md exists"""
        assert fix_agent_path.exists(), f"Fix agent file not found at {fix_agent_path}"

    def test_fix_agent_version_2_0_0(self, fix_agent_content):
        """Test fix-agent.md has version 2.0.0 in frontmatter"""
        version_match = re.search(r'version:\s*"?2\.0\.0"?', fix_agent_content)
        assert version_match is not None, "fix-agent.md should have version 2.0.0 in frontmatter"

    def test_fix_agent_no_mode_execution(self, fix_agent_content):
        """Test fix-agent.md does NOT contain mode-based execution logic"""
        mode_keywords = [
            "QUICK mode",
            "DIAGNOSTIC mode",
            "COMPREHENSIVE mode",
            "if mode ==",
            "switch mode",
        ]

        for keyword in mode_keywords:
            assert keyword not in fix_agent_content, (
                f"fix-agent.md should NOT contain '{keyword}' - mode execution should be removed"
            )

    def test_fix_agent_orchestrator_role(self, fix_agent_content):
        """Test fix-agent.md defines role as 'workflow orchestrator'"""
        orchestrator_indicators = [
            "workflow orchestrator",
            "orchestrate",
            "coordinate workflow",
            "execute workflow",
        ]

        found_indicators = [ind for ind in orchestrator_indicators if ind in fix_agent_content]
        assert len(found_indicators) >= 1, (
            f"fix-agent.md should define role as workflow orchestrator. Found: {found_indicators}"
        )

    def test_fix_agent_workflow_compliance(self, fix_agent_content):
        """Test fix-agent.md emphasizes '100% workflow compliance'"""
        compliance_indicators = [
            "100% workflow",
            "workflow compliance",
            "follow all steps",
            "complete workflow",
        ]

        found_indicators = [ind for ind in compliance_indicators if ind in fix_agent_content]
        assert len(found_indicators) >= 1, (
            f"fix-agent.md should emphasize 100% workflow compliance. Found: {found_indicators}"
        )

    def test_fix_agent_references_all_22_steps(self, fix_agent_content):
        """Test fix-agent.md references all 22 workflow steps"""
        # Check for reference to 22 steps
        step_count_match = re.search(r"22\s+steps?", fix_agent_content, re.IGNORECASE)
        assert step_count_match is not None, "fix-agent.md should reference all 22 workflow steps"

    def test_fix_agent_orchestrator_frontmatter(self, fix_agent_content):
        """Test fix-agent.md has correct frontmatter (orchestrator role)"""
        # Check for role in frontmatter
        role_match = re.search(
            r"role:\s*(?:workflow\s+)?orchestrator", fix_agent_content, re.IGNORECASE
        )
        assert role_match is not None, "fix-agent.md should have orchestrator role in frontmatter"


class TestFixWorkflowPhilosophyCompliance:
    """Test suite for philosophy compliance in fix command and agent"""

    @pytest.fixture
    def fix_command_path(self):
        """Path to fix command file"""
        return Path(__file__).parent.parent / ".claude" / "commands" / "amplihack" / "fix.md"

    @pytest.fixture
    def fix_agent_path(self):
        """Path to fix agent file"""
        return (
            Path(__file__).parent.parent
            / ".claude"
            / "agents"
            / "amplihack"
            / "specialized"
            / "fix-agent.md"
        )

    @pytest.fixture
    def fix_command_content(self, fix_command_path):
        """Read fix command content"""
        return fix_command_path.read_text()

    @pytest.fixture
    def fix_agent_content(self, fix_agent_path):
        """Read fix agent content"""
        return fix_agent_path.read_text()

    def test_ruthless_simplicity_single_path(self, fix_command_content):
        """Test fix.md emphasizes ruthless simplicity (single workflow path)"""
        simplicity_indicators = [
            "ruthless simplicity",
            "single path",
            "no branching",
            "one workflow",
        ]

        found_indicators = [ind for ind in simplicity_indicators if ind in fix_command_content]
        assert len(found_indicators) >= 1, (
            f"fix.md should emphasize ruthless simplicity. Found: {found_indicators}"
        )

    def test_no_mode_complexity(self, fix_command_content, fix_agent_content):
        """Test that mode-based complexity has been removed from both files"""
        # Allow "mode" in certain contexts (like "accommodate different modes")
        # but not in execution logic contexts
        execution_contexts = ["if mode", "switch mode", "mode ==", "select mode", "mode selection"]

        for context in execution_contexts:
            assert context not in fix_command_content, (
                f"fix.md should not contain mode execution logic: '{context}'"
            )
            assert context not in fix_agent_content, (
                f"fix-agent.md should not contain mode execution logic: '{context}'"
            )

    def test_workflow_as_single_source_of_truth(self, fix_command_content, fix_agent_content):
        """Test that both files reference DEFAULT_WORKFLOW as single source of truth"""
        workflow_refs = ["DEFAULT_WORKFLOW", "workflow"]

        fix_cmd_has_workflow = any(ref in fix_command_content for ref in workflow_refs)
        fix_agent_has_workflow = any(ref in fix_agent_content for ref in workflow_refs)

        assert fix_cmd_has_workflow, "fix.md should reference DEFAULT_WORKFLOW"
        assert fix_agent_has_workflow, "fix-agent.md should reference DEFAULT_WORKFLOW"


class TestFixPatternDetection:
    """Test suite for pattern detection as context (not mode selection)"""

    @pytest.fixture
    def fix_command_path(self):
        """Path to fix command file"""
        return Path(__file__).parent.parent / ".claude" / "commands" / "amplihack" / "fix.md"

    @pytest.fixture
    def fix_command_content(self, fix_command_path):
        """Read fix command content"""
        return fix_command_path.read_text()

    def test_patterns_listed(self, fix_command_content):
        """Test fix.md lists the 6 common error patterns"""
        patterns = ["import", "ci", "test", "config", "quality", "logic"]

        found_patterns = [p for p in patterns if p in fix_command_content.lower()]
        assert len(found_patterns) >= 4, (
            f"fix.md should list common error patterns. Found: {found_patterns}"
        )

    def test_pattern_context_not_branching(self, fix_command_content):
        """Test patterns provide context but don't create workflow branches"""
        # Should NOT have conditional workflow logic based on patterns
        branching_indicators = [
            "if pattern == 'import'",
            "switch pattern",
            "pattern-specific workflow",
            "different steps for",
        ]

        for indicator in branching_indicators:
            assert indicator not in fix_command_content, (
                f"fix.md should not have pattern-based branching: '{indicator}'"
            )

    def test_pattern_informs_specialized_agents(self, fix_command_content):
        """Test patterns inform which specialized agents to invoke"""
        agent_indicators = [
            "specialized agent",
            "pattern-specific agent",
            "agent selection",
            "invoke agent",
        ]

        found_indicators = [ind for ind in agent_indicators if ind in fix_command_content]
        assert len(found_indicators) >= 1, (
            f"fix.md should show how patterns inform agent selection. Found: {found_indicators}"
        )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
