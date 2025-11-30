"""Test scenarios for MCP evaluation.

This package contains test scenarios that evaluate MCP tool capabilities
across three categories:
1. Cross-file navigation
2. Code understanding and analysis
3. Targeted code modification
"""

from .scenario_1_navigation import create_navigation_scenario
from .scenario_2_analysis import create_analysis_scenario
from .scenario_3_modification import create_modification_scenario


def get_all_scenarios():
    """Get all test scenarios.

    Returns:
        List of TestScenario objects
    """
    return [
        create_navigation_scenario(),
        create_analysis_scenario(),
        create_modification_scenario(),
    ]


__all__ = [
    "create_navigation_scenario",
    "create_analysis_scenario",
    "create_modification_scenario",
    "get_all_scenarios",
]
