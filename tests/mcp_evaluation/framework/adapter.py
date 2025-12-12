"""Tool adapter interface for MCP evaluation framework.

This module defines the abstract interface that all tool-specific adapters
must implement. Each adapter is responsible for enabling/disabling a tool
and collecting tool-specific metrics.
"""

from abc import ABC, abstractmethod
from typing import List

from .types import ToolCapability, ToolMetrics


class ToolAdapter(ABC):
    """Abstract interface for tool-specific adapters.

    Each MCP tool integration must implement this interface to work with
    the evaluation framework. The adapter handles:
    - Tool enablement/disablement
    - Tool availability checking
    - Tool-specific metrics collection
    - Capability reporting
    """

    @abstractmethod
    def enable(self) -> None:
        """Enable tool for Claude Code to use.

        This typically involves:
        - Setting environment variables
        - Starting tool servers
        - Configuring tool access
        """

    @abstractmethod
    def disable(self) -> None:
        """Disable tool (baseline mode).

        This should completely disable the tool so the baseline
        execution uses no tool-specific features.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if tool is available and working.

        Returns:
            True if tool is accessible and healthy, False otherwise
        """

    @abstractmethod
    def collect_tool_metrics(self) -> ToolMetrics:
        """Collect tool-specific metrics.

        Returns:
            ToolMetrics object with usage, performance, and value data
        """

    @abstractmethod
    def get_capabilities(self) -> List[ToolCapability]:
        """Return tool's capabilities.

        Returns:
            List of ToolCapability objects describing what the tool can do
        """


class MockToolAdapter(ToolAdapter):
    """Mock adapter for testing purposes.

    This adapter simulates a tool without requiring actual tool setup.
    Useful for framework testing and development.
    """

    def __init__(self):
        """Initialize mock adapter."""
        self.enabled = False
        self.call_count = 0

    def enable(self) -> None:
        """Enable mock tool."""
        self.enabled = True

    def disable(self) -> None:
        """Disable mock tool."""
        self.enabled = False

    def is_available(self) -> bool:
        """Mock is always available."""
        return True

    def collect_tool_metrics(self) -> ToolMetrics:
        """Return mock metrics."""
        return ToolMetrics(
            features_used=["mock_feature"],
            feature_effectiveness={"mock_feature": 1.0},
            tool_call_latency=[0.1] * self.call_count,
            tool_failures=0,
            fallback_count=0,
            unique_insights=5,
            time_saved_estimate=10.0,
        )

    def get_capabilities(self) -> List[ToolCapability]:
        """Return mock capabilities."""
        from .types import ExpectedImprovement, ScenarioCategory

        return [
            ToolCapability(
                id="mock_capability",
                name="Mock Capability",
                description="A mock capability for testing",
                relevant_scenarios=[ScenarioCategory.NAVIGATION],
                expected_improvement=ExpectedImprovement.BOTH,
                mcp_commands=["mock/command"],
            )
        ]
