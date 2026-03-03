"""MCP test scenario generator.

Generates gadugi-agentic-test YAML scenarios for MCP servers
based on tool definitions, input schemas, and resource definitions.
"""

import json
from pathlib import Path

from .models import GeneratedTest, MCPConfig, MCPTool, TestCategory
from .template_manager import TemplateManager
from .utils import ensure_directory, write_file


def generate_mcp_tests(
    config: MCPConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate all MCP test scenarios.

    Args:
        config: MCP server configuration
        template_mgr: Template manager
        output_dir: Output directory for generated test files

    Returns:
        List of GeneratedTest objects
    """
    generated = []
    generated.extend(_generate_mcp_smoke_tests(config, template_mgr, output_dir))
    generated.extend(_generate_mcp_validation_tests(config, template_mgr, output_dir))
    generated.extend(_generate_mcp_error_tests(config, template_mgr, output_dir))
    generated.extend(_generate_mcp_workflow_tests(config, template_mgr, output_dir))
    return generated


def _generate_mcp_smoke_tests(
    config: MCPConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate MCP tool smoke tests (one per tool)."""
    tests_dir = output_dir / "mcp-smoke"
    ensure_directory(tests_dir)

    generated = []
    server_args = ", ".join(f'"{a}"' for a in config.server_args)

    for tool in config.tools[:10]:  # Limit to 10 tools
        # Generate sample valid input from schema
        valid_input = _generate_sample_input(tool)
        valid_input_json = json.dumps(valid_input, indent=6)

        # Build validation steps for required inputs
        validation_steps = ""
        if tool.required_inputs:
            # Test with missing required field
            if valid_input:
                first_required = tool.required_inputs[0]
                incomplete_input = {k: v for k, v in valid_input.items() if k != first_required}
                validation_steps = f"""    - action: mcp_call_tool
      tool: "{tool.name}"
      input: {json.dumps(incomplete_input)}
      description: "Call without required field '{first_required}'"
      timeout: 15s

    - action: verify_mcp_error
      matches: "(required|missing|{first_required})"
      description: "Should report missing required field"
"""

        # Build error steps
        error_steps = f"""    - action: mcp_call_tool
      tool: "{tool.name}"
      input: {{"__invalid__": true}}
      description: "Call with invalid input schema"
      timeout: 15s

    - action: verify_mcp_error
      matches: "(invalid|error|unexpected)"
      description: "Should handle invalid input gracefully"
"""

        context = {
            "tool_name": tool.name,
            "tool_description": tool.description or f"MCP tool: {tool.name}",
            "transport": config.transport,
            "server_command": config.server_command,
            "server_args": server_args,
            "valid_input": valid_input_json,
            "response_pattern": ".*",  # Any response is ok for smoke
            "validation_steps": validation_steps,
            "error_steps": error_steps,
        }

        content = template_mgr.render("mcp_tool", context)
        test_file = tests_dir / f"{tool.name}.yaml"
        write_file(test_file, content)

        test_count = 2  # basic call + invalid input
        if validation_steps:
            test_count += 1

        generated.append(
            GeneratedTest(
                category=TestCategory.MCP_TOOL_SMOKE,
                file_path=test_file,
                test_count=test_count,
                description=f"MCP smoke test for tool '{tool.name}'",
            )
        )

    return generated


def _generate_mcp_validation_tests(
    config: MCPConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate MCP input validation test scenarios."""
    tests_dir = output_dir / "mcp-validation"
    ensure_directory(tests_dir)

    generated = []
    server_args = ", ".join(f'"{a}"' for a in config.server_args)

    # Find tools with defined input schemas
    schema_tools = [t for t in config.tools if t.input_schema]

    for tool in schema_tools[:5]:
        properties = tool.input_schema.get("properties", {})
        if not isinstance(properties, dict):
            continue

        # Generate type mismatch tests
        steps = ""
        for prop_name, prop_def in list(properties.items())[:3]:
            if not isinstance(prop_def, dict):
                continue
            prop_type = prop_def.get("type", "string")

            # Create input with wrong type
            wrong_value = _wrong_type_value(prop_type)
            wrong_input = {prop_name: wrong_value}

            steps += f"""    - action: mcp_call_tool
      tool: "{tool.name}"
      input: {json.dumps(wrong_input)}
      description: "Send wrong type for '{prop_name}' (expected {prop_type})"
      timeout: 15s

    - action: verify_mcp_error
      matches: "(type|invalid|error|{prop_name})"
      description: "Should reject wrong type for {prop_name}"

"""

        if steps:
            content = f"""# MCP Input Validation Test - {tool.name}
# Auto-generated outside-in test scenario

scenario:
  name: "MCP Validation - {tool.name} Input Types"
  description: |
    Verifies that the '{tool.name}' tool properly validates input types
    and returns meaningful error messages for type mismatches.
  type: mcp
  level: 2
  tags: [mcp, validation, {tool.name}, auto-generated]

  prerequisites:
    - "MCP server is available via {config.transport} transport"

  steps:
    - action: mcp_connect
      command: "{config.server_command}"
      args: [{server_args}]
      transport: "{config.transport}"
      description: "Connect to MCP server"
      timeout: 15s

{steps}
    - action: mcp_disconnect
      description: "Disconnect from MCP server"

  cleanup:
    - action: mcp_disconnect
      force: true
"""
            test_file = tests_dir / f"validate-{tool.name}.yaml"
            write_file(test_file, content)

            prop_count = min(len(properties), 3)
            generated.append(
                GeneratedTest(
                    category=TestCategory.MCP_TOOL_VALIDATION,
                    file_path=test_file,
                    test_count=prop_count,
                    description=f"MCP validation test for '{tool.name}'",
                )
            )

    return generated


def _generate_mcp_error_tests(
    config: MCPConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate MCP error handling test scenarios."""
    tests_dir = output_dir / "mcp-errors"
    ensure_directory(tests_dir)

    server_args = ", ".join(f'"{a}"' for a in config.server_args)

    content = f"""# MCP Error Handling Test
# Auto-generated outside-in test scenario

scenario:
  name: "MCP Error Handling - Server Resilience"
  description: |
    Verifies that the MCP server handles error conditions gracefully
    including unknown tools, malformed input, and edge cases.
  type: mcp
  level: 2
  tags: [mcp, error-handling, resilience, auto-generated]

  prerequisites:
    - "MCP server is available via {config.transport} transport"

  steps:
    - action: mcp_connect
      command: "{config.server_command}"
      args: [{server_args}]
      transport: "{config.transport}"
      description: "Connect to MCP server"
      timeout: 15s

    - action: mcp_call_tool
      tool: "nonexistent_tool_xyz"
      input: {{}}
      description: "Call non-existent tool"
      timeout: 10s

    - action: verify_mcp_error
      matches: "(not found|unknown|does not exist)"
      description: "Should report unknown tool"

    - action: mcp_call_tool
      tool: "{config.tools[0].name if config.tools else 'test'}"
      input: null
      description: "Call with null input"
      timeout: 10s

    - action: verify_mcp_error
      matches: "(invalid|null|error)"
      description: "Should handle null input"

    - action: mcp_disconnect
      description: "Disconnect from MCP server"

  cleanup:
    - action: mcp_disconnect
      force: true
"""
    test_file = tests_dir / "error-handling.yaml"
    write_file(test_file, content)

    return [
        GeneratedTest(
            category=TestCategory.MCP_TOOL_ERROR,
            file_path=test_file,
            test_count=3,
            description="MCP error handling tests",
        )
    ]


def _generate_mcp_workflow_tests(
    config: MCPConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate MCP multi-tool workflow test scenarios."""
    if len(config.tools) < 2:
        return []

    tests_dir = output_dir / "mcp-workflows"
    ensure_directory(tests_dir)

    server_args = ", ".join(f'"{a}"' for a in config.server_args)

    # Build workflow steps calling tools in sequence
    steps = ""
    for i, tool in enumerate(config.tools[:4]):
        valid_input = _generate_sample_input(tool)
        steps += f"""    - action: mcp_call_tool
      tool: "{tool.name}"
      input: {json.dumps(valid_input)}
      description: "Step {i+1}: Call {tool.name}"
      timeout: 30s

    - action: verify_mcp_response
      matches: ".*"
      description: "Step {i+1}: {tool.name} should respond"

"""

    context = {
        "workflow_name": "Multi-Tool Sequence",
        "transport": config.transport,
        "server_command": config.server_command,
        "server_args": server_args,
        "workflow_steps": steps,
    }

    content = template_mgr.render("mcp_workflow", context)
    test_file = tests_dir / "multi-tool-workflow.yaml"
    write_file(test_file, content)

    return [
        GeneratedTest(
            category=TestCategory.MCP_WORKFLOW,
            file_path=test_file,
            test_count=min(len(config.tools), 4) * 2,
            description="MCP multi-tool workflow test",
        )
    ]


def _generate_sample_input(tool: MCPTool) -> dict:
    """Generate sample valid input for an MCP tool."""
    if not tool.input_schema:
        return {}

    sample: dict = {}
    properties = tool.input_schema.get("properties", {})
    if not isinstance(properties, dict):
        return sample

    for prop_name, prop_def in properties.items():
        if not isinstance(prop_def, dict):
            continue
        prop_type = prop_def.get("type", "string")
        if prop_type == "string":
            if "path" in prop_name.lower() or "file" in prop_name.lower():
                sample[prop_name] = "/tmp/test-file.txt"
            elif "url" in prop_name.lower():
                sample[prop_name] = "https://example.com"
            elif "query" in prop_name.lower():
                sample[prop_name] = "test query"
            else:
                sample[prop_name] = f"test-{prop_name}"
        elif prop_type == "integer":
            sample[prop_name] = 1
        elif prop_type == "number":
            sample[prop_name] = 1.0
        elif prop_type == "boolean":
            sample[prop_name] = True
        elif prop_type == "array":
            sample[prop_name] = ["item1"]
        elif prop_type == "object":
            sample[prop_name] = {}

    return sample


def _wrong_type_value(expected_type: str):
    """Return a value of the wrong type for testing."""
    wrong_values = {
        "string": 12345,
        "integer": "not-a-number",
        "number": "not-a-number",
        "boolean": "not-a-bool",
        "array": "not-an-array",
        "object": "not-an-object",
    }
    return wrong_values.get(expected_type, None)
