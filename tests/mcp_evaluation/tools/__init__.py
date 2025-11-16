"""MCP Tool Adapters.

This package contains tool-specific adapters for MCP server integrations.
Each adapter implements the ToolAdapter interface and provides tool-specific
functionality for enablement, metrics collection, and capability reporting.
"""

import yaml
from pathlib import Path
from typing import Dict

from tests.mcp_evaluation.framework.types import ToolConfiguration


def load_tool_config(tool_name: str) -> ToolConfiguration:
    """Load tool configuration from YAML file.

    Args:
        tool_name: Name of the tool (e.g., "serena")

    Returns:
        ToolConfiguration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_path = Path(__file__).parent / f"{tool_name}_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Expected: tools/{tool_name}_config.yaml"
        )

    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Filter data to only include fields that ToolConfiguration accepts
    valid_fields = {
        'tool_id', 'tool_name', 'version', 'description', 'capabilities',
        'adapter_class', 'setup_required', 'setup_instructions',
        'expected_advantages', 'baseline_comparison_mode',
        'health_check_url', 'environment_variables', 'max_concurrent_calls',
        'timeout_seconds', 'fallback_behavior'
    }
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}

    config = ToolConfiguration(**filtered_data)

    # Validate configuration
    errors = config.validate()
    if errors:
        raise ValueError(
            f"Invalid configuration for {tool_name}:\n" +
            "\n".join(f"  - {err}" for err in errors)
        )

    return config


__all__ = [
    "load_tool_config",
]
