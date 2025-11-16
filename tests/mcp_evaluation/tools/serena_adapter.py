"""Serena MCP Server adapter for evaluation framework.

This adapter provides integration with the Serena MCP server,
enabling/disabling the tool and collecting Serena-specific metrics.
"""

import os
import time
from collections import defaultdict
from typing import Dict, List
import requests

from tests.mcp_evaluation.framework.adapter import ToolAdapter
from tests.mcp_evaluation.framework.types import ToolCapability, ToolMetrics, ToolConfiguration


class SerenaToolAdapter(ToolAdapter):
    """Adapter for Serena MCP Server.

    This adapter manages Serena server integration by:
    - Setting environment variables to enable/disable Serena
    - Checking server health and availability
    - Tracking MCP call metrics
    - Collecting tool-specific usage data
    """

    def __init__(self, config: ToolConfiguration):
        """Initialize Serena adapter.

        Args:
            config: Tool configuration for Serena
        """
        self.config = config
        self.server_url = config.environment_variables.get(
            "SERENA_MCP_URL",
            "http://localhost:8080"
        )
        self.enabled = False
        self.call_log: List[Dict] = []

    def enable(self) -> None:
        """Enable Serena for Claude Code to use.

        Sets environment variables that Claude Code checks to determine
        if Serena MCP server should be used.
        """
        for key, value in self.config.environment_variables.items():
            os.environ[key] = value

        self.enabled = True
        print(f"  Serena enabled at {self.server_url}")

    def disable(self) -> None:
        """Disable Serena (baseline mode).

        Removes environment variables so Claude Code uses baseline
        file operations instead of Serena.
        """
        for key in self.config.environment_variables.keys():
            os.environ.pop(key, None)

        self.enabled = False
        print("  Serena disabled (baseline mode)")

    def is_available(self) -> bool:
        """Check if Serena is available and working.

        Returns:
            True if Serena server is accessible and healthy
        """
        if not self.config.health_check_url:
            # No health check configured, assume available
            return True

        try:
            response = requests.get(
                self.config.health_check_url,
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            print(f"  Warning: Serena health check failed: {e}")
            return False

    def collect_tool_metrics(self) -> ToolMetrics:
        """Collect Serena-specific metrics from call log.

        Returns:
            ToolMetrics with usage, performance, and value data
        """
        if not self.call_log:
            # No calls recorded, return empty metrics
            return ToolMetrics(
                features_used=[],
                feature_effectiveness={},
                tool_call_latency=[],
                tool_failures=0,
                fallback_count=0,
                unique_insights=0,
                time_saved_estimate=0.0,
            )

        # Analyze call log
        features_used = set()
        feature_success = defaultdict(list)
        latencies = []
        failures = 0

        for call in self.call_log:
            feature = call.get("feature", "unknown")
            features_used.add(feature)
            success = call.get("success", False)
            feature_success[feature].append(success)
            latencies.append(call.get("latency", 0.0))
            if not success:
                failures += 1

        # Calculate feature effectiveness
        feature_effectiveness = {
            feature: sum(successes) / len(successes)
            for feature, successes in feature_success.items()
        }

        # Estimate unique insights (simplified heuristic)
        unique_insights = self._count_unique_insights()

        # Estimate time saved (simplified heuristic)
        time_saved = self._estimate_time_saved()

        return ToolMetrics(
            features_used=list(features_used),
            feature_effectiveness=feature_effectiveness,
            tool_call_latency=latencies,
            tool_failures=failures,
            fallback_count=self._count_fallbacks(),
            unique_insights=unique_insights,
            time_saved_estimate=time_saved,
        )

    def get_capabilities(self) -> List[ToolCapability]:
        """Return Serena's capabilities from configuration.

        Returns:
            List of ToolCapability objects
        """
        return self.config.capabilities

    def log_call(
        self,
        feature: str,
        command: str,
        latency: float,
        success: bool,
        result: Dict = None
    ) -> None:
        """Log a Serena MCP call for metrics collection.

        Args:
            feature: Capability ID (e.g., "symbol_navigation")
            command: MCP command invoked
            latency: Call duration in seconds
            success: Whether call succeeded
            result: Optional result data for analysis
        """
        self.call_log.append({
            "feature": feature,
            "command": command,
            "latency": latency,
            "success": success,
            "result": result,
            "timestamp": time.time(),
        })

    def _count_fallbacks(self) -> int:
        """Count how many times Serena failed and fell back to baseline.

        Returns:
            Number of fallback occurrences
        """
        # Simplified: count failures as fallbacks
        return sum(1 for call in self.call_log if not call.get("success", False))

    def _count_unique_insights(self) -> int:
        """Count unique insights provided by Serena.

        This is a heuristic that counts:
        - Successful symbol navigations
        - Documentation retrievals
        - Semantic search results
        - Diagnostics found

        Returns:
            Estimated unique insights count
        """
        insights = 0
        for call in self.call_log:
            if not call.get("success", False):
                continue

            feature = call.get("feature", "")
            result = call.get("result", {})

            # Count different types of insights
            if feature == "symbol_navigation":
                # Each successful symbol navigation is an insight
                insights += 1
            elif feature == "hover_documentation":
                # Documentation provides insights
                insights += 1
            elif feature == "semantic_search":
                # Semantic matches are insights
                results_count = len(result.get("matches", []))
                insights += min(results_count, 5)  # Cap at 5 per call
            elif feature == "diagnostics":
                # Each diagnostic is an insight
                diagnostics_count = len(result.get("diagnostics", []))
                insights += diagnostics_count

        return insights

    def _estimate_time_saved(self) -> float:
        """Estimate time saved by using Serena vs baseline.

        This is a heuristic based on:
        - Symbol navigation: saves grep + file read time
        - Hover documentation: saves file read + parsing time
        - Semantic search: saves multiple grep attempts

        Returns:
            Estimated seconds saved
        """
        time_saved = 0.0

        for call in self.call_log:
            if not call.get("success", False):
                continue

            feature = call.get("feature", "")

            # Estimated time savings per feature
            # (based on typical baseline operation times)
            if feature == "symbol_navigation":
                # Saves ~2-5 seconds of grep + file reads
                time_saved += 3.0
            elif feature == "hover_documentation":
                # Saves ~1-2 seconds of file read + parsing
                time_saved += 1.5
            elif feature == "semantic_search":
                # Saves ~5-10 seconds of multiple grep attempts
                time_saved += 7.0
            elif feature == "diagnostics":
                # Saves potential debugging time
                time_saved += 2.0
            elif feature == "code_completion":
                # Saves typing time
                time_saved += 1.0

        return time_saved


class MockSerenaAdapter(SerenaToolAdapter):
    """Mock Serena adapter for testing without actual server.

    This adapter simulates Serena behavior for framework testing
    and development without requiring a running Serena server.
    """

    def __init__(self, config: ToolConfiguration):
        """Initialize mock adapter."""
        super().__init__(config)
        self.mock_available = True

    def is_available(self) -> bool:
        """Mock is always available (unless explicitly set otherwise)."""
        return self.mock_available

    def enable(self) -> None:
        """Mock enable."""
        self.enabled = True
        print("  Mock Serena enabled")

    def disable(self) -> None:
        """Mock disable."""
        self.enabled = False
        print("  Mock Serena disabled")
