#!/usr/bin/env python3
"""
Comprehensive test suite for session workflow and context preservation.

This test module validates the end-to-end workflow of context capture,
preservation, and transfer across different agents.
"""

import sys
from pathlib import Path

import pytest

# Add project paths
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))

from context_preservation import ContextPreserver
from session_start import SessionStartHook


class TestSessionWorkflow:
    """
    Validates the complete session workflow for context preservation.

    Test Scenarios:
    1. End-to-end requirement tracking
    2. Context transfer between agents
    3. Original requirement preservation
    4. Performance and reliability checks
    """

    @pytest.fixture
    def preserver(self):
        """Create a ContextPreserver for each test."""
        session_id = f"test_session_{hash(self)}"
        return ContextPreserver(session_id)

    def test_complete_workflow_requirement_preservation(self, preserver):
        """
        Validate complete workflow from initial request to agent processing.

        Simulates:
        1. Initial user request
        2. Session start hook processing
        3. Context extraction
        4. Agent workflow transfer
        """
        original_request = """
        Implement a comprehensive context preservation system for the Microsoft Hackathon 2025 project.

        **Target**: Context Preservation Mechanism
        **Requirements**:
        - Capture 100% of original user requirements
        - Preserve context across agent workflows
        - Zero requirement degradation

        **Constraints**:
        - Performance overhead < 3%
        - Simple, non-intrusive implementation
        """

        # Simulate session start hook
        hook = SessionStartHook()
        hook_result = hook.process({"prompt": original_request})

        # Verify hook result
        assert hook_result is not None, "Session start hook failed"
        assert "additionalContext" in hook_result, "No context generated"

        # Extract original request
        extracted_request = preserver.extract_original_request(original_request)

        # Verify extraction details
        assert extracted_request["target"] == "Context Preservation Mechanism"
        assert len(extracted_request["requirements"]) > 0
        assert len(extracted_request["constraints"]) > 0

        # Format for agent context
        agent_context = preserver.format_agent_context(extracted_request)

        # Verify agent context
        assert "🎯 ORIGINAL USER REQUEST" in agent_context
        assert "Context Preservation Mechanism" in agent_context
        assert "Requirements" in agent_context
        assert "Constraints" in agent_context

    def test_context_transfer_between_agents(self, preserver):
        """
        Validate context transfer between different agents.

        Simulates passing context from one agent to another without loss.
        """
        original_request = """
        Build a multi-agent coordination system for agentic coding.

        **Target**: Agent Workflow Orchestration
        **Requirements**:
        - Support parallel agent execution
        - Maintain context integrity
        - Dynamically route tasks
        """

        # First agent: Extract context
        first_agent_context = preserver.extract_original_request(original_request)
        first_agent_formatted = preserver.format_agent_context(first_agent_context)

        # Simulate second agent receiving context
        hook = SessionStartHook()
        result = hook.process({"prompt": first_agent_formatted})

        # Verify context preservation
        assert result is not None, "Context transfer failed"
        assert "Agent Workflow Orchestration" in result["additionalContext"]
        assert "Requirements" in result["additionalContext"]

    def test_extensive_agent_workflow_preservation(self, preserver):
        """
        Comprehensive test of context preservation through multiple agent transitions.

        Simulates:
        1. Initial requirement
        2. Multiple agent workflow stages
        3. Consistent context preservation
        """
        workflow_stages = [
            "Initial Design",
            "Architectural Planning",
            "Implementation Strategy",
            "Detailed Development",
            "Testing and Validation",
        ]

        original_request = """
        Develop an advanced agentic coding framework with comprehensive automation.

        **Target**: Next-Generation Development Tools
        **Requirements**:
        - Support end-to-end software development lifecycle
        - Intelligent task decomposition
        - Adaptive agent coordination
        """

        # Store original context
        original_context = preserver.extract_original_request(original_request)

        # Simulate multi-stage agent workflow
        current_context = original_context
        for stage in workflow_stages:
            # Format context for each stage
            stage_context = preserver.format_agent_context(current_context)

            # Simulate hook processing (as if new agent picks up work)
            hook = SessionStartHook()
            result = hook.process({"prompt": stage_context})

            # Verify context consistency
            assert result is not None, f"Context lost at stage: {stage}"
            assert "Next-Generation Development Tools" in result["additionalContext"]

            # Simulate minimal context update (e.g., new requirements discovered)
            current_context["requirements"].append(f"Stage-specific requirement for {stage}")

    def test_performance_under_extensive_transfers(self, preserver):
        """
        Performance test for context preservation during extensive agent transfers.

        Validates:
        - Context transfer overhead
        - Memory efficiency
        - Processing speed
        """
        import time
        import tracemalloc

        original_request = "Build a high-performance context preservation system."

        # Start memory tracking
        tracemalloc.start()
        start_time = time.time()

        # Simulate 100 agent workflow transfers
        for _ in range(100):
            context = preserver.extract_original_request(original_request)
            formatted_context = preserver.format_agent_context(context)

            hook = SessionStartHook()
            hook.process({"prompt": formatted_context})

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Performance assertions
        transfer_time = end_time - start_time
        assert transfer_time < 5, f"Context transfers too slow: {transfer_time}s"
        assert peak < 10 * 1024 * 1024, f"Excessive memory usage: {peak} bytes"

    def test_requirement_degradation_prevention(self, preserver):
        """
        Validate zero requirement degradation through agent workflows.

        Ensures that:
        - Original requirements are not lost
        - Critical keywords are preserved
        - Context remains intact
        """
        original_request = """
        Implement context preservation with ZERO requirement loss.

        **Target**: Absolute Requirement Fidelity
        **Requirements**:
        - CAPTURE ALL user intentions
        - NO requirement degradation
        - ENSURE complete context transfer

        **Constraints**:
        - CANNOT lose ANY part of the original request
        """

        context = preserver.extract_original_request(original_request)
        formatted_context = preserver.format_agent_context(context)

        # Critical preservation checks
        keywords_to_preserve = ["ZERO", "ALL", "NO", "CANNOT"]
        for keyword in keywords_to_preserve:
            assert keyword in formatted_context, f"Critical keyword {keyword} was lost"

        # Verify complete context preservation
        hook = SessionStartHook()
        result = hook.process({"prompt": formatted_context})

        # Detailed context verification
        assert "Absolute Requirement Fidelity" in result["additionalContext"]
        assert all(kw in result["additionalContext"] for kw in keywords_to_preserve)


if __name__ == "__main__":
    pytest.main([__file__])
