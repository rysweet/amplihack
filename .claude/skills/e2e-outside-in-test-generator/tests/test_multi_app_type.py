"""Tests for multi-app-type test generation.

Covers: app type detection, CLI/TUI/API/MCP generators, orchestrator dispatch.
Testing pyramid: 80% unit (detection + generation), 20% integration (orchestrator).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.api_test_generator import generate_api_tests
from generator.app_type_detector import (
    detect_app_type,
)
from generator.cli_test_generator import generate_cli_tests
from generator.mcp_test_generator import generate_mcp_tests
from generator.models import (
    APIConfig,
    APIEndpointSpec,
    AppType,
    CLICommand,
    CLIConfig,
    MCPConfig,
    MCPTool,
    TUIConfig,
    TUIWidget,
)
from generator.template_manager import TemplateManager
from generator.tui_test_generator import generate_tui_tests


@pytest.fixture(autouse=True)
def _disable_path_security(monkeypatch):
    """Allow writes to tmp_path in tests by making validate_project_root a no-op."""
    monkeypatch.setattr(
        "generator.security.validate_project_root",
        lambda path, allowed_root=None: path.resolve(),
    )
    monkeypatch.setattr(
        "generator.utils.validate_project_root",
        lambda path, allowed_root=None: path.resolve(),
    )


# ── App Type Detection ──────────────────────────────────────────────────


class TestAppTypeDetection:
    def test_explicit_type_override(self, tmp_path):
        assert detect_app_type(tmp_path, "cli") == AppType.CLI
        assert detect_app_type(tmp_path, "tui") == AppType.TUI
        assert detect_app_type(tmp_path, "api") == AppType.API
        assert detect_app_type(tmp_path, "mcp") == AppType.MCP
        assert detect_app_type(tmp_path, "web") == AppType.WEB

    def test_invalid_explicit_type_falls_through(self, tmp_path):
        result = detect_app_type(tmp_path, "invalid")
        assert result == AppType.WEB  # Falls through to default

    def test_detect_api_from_openapi_spec(self, tmp_path):
        (tmp_path / "openapi.yaml").write_text("openapi: 3.0.0\npaths: {}")
        assert detect_app_type(tmp_path) == AppType.API

    def test_detect_cli_from_click(self, tmp_path):
        (tmp_path / "cli.py").write_text("import click\n@click.command()\ndef main(): pass")
        assert detect_app_type(tmp_path) == AppType.CLI

    def test_detect_tui_from_textual(self, tmp_path):
        (tmp_path / "app.py").write_text("from textual.app import App\nclass MyApp(App): pass")
        assert detect_app_type(tmp_path) == AppType.TUI

    def test_detect_mcp_from_sdk(self, tmp_path):
        (tmp_path / "server.py").write_text("from mcp.server import McpServer\n")
        assert detect_app_type(tmp_path) == AppType.MCP

    def test_default_to_web(self, tmp_path):
        # Empty project defaults to web
        assert detect_app_type(tmp_path) == AppType.WEB

    def test_detection_priority_mcp_over_cli(self, tmp_path):
        # Project with both MCP and CLI markers → MCP wins
        (tmp_path / "server.py").write_text("from mcp.server import McpServer\nimport click")
        assert detect_app_type(tmp_path) == AppType.MCP


# ── CLI Test Generator ──────────────────────────────────────────────────


class TestCLITestGenerator:
    def test_generates_smoke_tests(self, tmp_path):
        config = CLIConfig(binary_path="myapp", framework="click", commands=[])
        template_mgr = TemplateManager()
        results = generate_cli_tests(config, template_mgr, tmp_path)
        assert any(r.category.value == "cli_smoke" for r in results)

    def test_generates_command_tests(self, tmp_path):
        config = CLIConfig(
            binary_path="myapp",
            framework="click",
            commands=[CLICommand(name="run", args=["file"], flags=["--verbose"])],
        )
        template_mgr = TemplateManager()
        results = generate_cli_tests(config, template_mgr, tmp_path)
        assert any(r.category.value == "cli_commands" for r in results)

    def test_generates_error_handling_tests(self, tmp_path):
        config = CLIConfig(
            binary_path="myapp",
            framework="click",
            commands=[CLICommand(name="run")],
        )
        template_mgr = TemplateManager()
        results = generate_cli_tests(config, template_mgr, tmp_path)
        assert any(r.category.value == "cli_error_handling" for r in results)

    def test_output_files_are_yaml(self, tmp_path):
        config = CLIConfig(
            binary_path="myapp", framework="click", commands=[CLICommand(name="test")]
        )
        template_mgr = TemplateManager()
        results = generate_cli_tests(config, template_mgr, tmp_path)
        for r in results:
            assert r.file_path.suffix == ".yaml"
            assert r.file_path.exists()


# ── TUI Test Generator ──────────────────────────────────────────────────


class TestTUITestGenerator:
    def test_generates_smoke_tests(self, tmp_path):
        config = TUIConfig(binary_path="myapp", framework="textual")
        template_mgr = TemplateManager()
        results = generate_tui_tests(config, template_mgr, tmp_path)
        assert any(r.category.value == "tui_smoke" for r in results)

    def test_generates_navigation_tests(self, tmp_path):
        config = TUIConfig(
            binary_path="myapp", framework="textual", keyboard_shortcuts={"j": "down", "k": "up"}
        )
        template_mgr = TemplateManager()
        results = generate_tui_tests(config, template_mgr, tmp_path)
        assert any(r.category.value == "tui_navigation" for r in results)

    def test_generates_interaction_tests_for_list_widgets(self, tmp_path):
        config = TUIConfig(
            binary_path="myapp",
            framework="textual",
            widgets=[TUIWidget(name="ListView", widget_type="list")],
        )
        template_mgr = TemplateManager()
        results = generate_tui_tests(config, template_mgr, tmp_path)
        assert any(r.category.value == "tui_interaction" for r in results)


# ── API Test Generator ──────────────────────────────────────────────────


class TestAPITestGenerator:
    def _api_config(self):
        return APIConfig(
            base_url="http://localhost:3000",
            spec_format="openapi",
            endpoints=[
                APIEndpointSpec(path="/users", method="GET", summary="List users", tags=["users"]),
                APIEndpointSpec(
                    path="/users",
                    method="POST",
                    summary="Create user",
                    tags=["users"],
                    request_body_schema={
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                ),
                APIEndpointSpec(
                    path="/users/{id}", method="DELETE", summary="Delete user", tags=["users"]
                ),
            ],
            auth_type="bearer",
        )

    def test_generates_smoke_tests(self, tmp_path):
        results = generate_api_tests(self._api_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "api_smoke" for r in results)

    def test_generates_crud_tests(self, tmp_path):
        results = generate_api_tests(self._api_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "api_crud" for r in results)

    def test_generates_validation_tests(self, tmp_path):
        results = generate_api_tests(self._api_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "api_validation" for r in results)

    def test_generates_auth_tests(self, tmp_path):
        results = generate_api_tests(self._api_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "api_auth" for r in results)

    def test_generates_workflow_tests(self, tmp_path):
        results = generate_api_tests(self._api_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "api_workflow" for r in results)


# ── MCP Test Generator ──────────────────────────────────────────────────


class TestMCPTestGenerator:
    def _mcp_config(self):
        return MCPConfig(
            server_command="python",
            server_args=["-m", "myserver"],
            transport="stdio",
            tools=[
                MCPTool(
                    name="search",
                    description="Search documents",
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                    required_inputs=["query"],
                ),
                MCPTool(
                    name="summarize",
                    description="Summarize text",
                    input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                    required_inputs=["text"],
                ),
            ],
        )

    def test_generates_smoke_tests(self, tmp_path):
        results = generate_mcp_tests(self._mcp_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "mcp_tool_smoke" for r in results)

    def test_generates_error_tests(self, tmp_path):
        results = generate_mcp_tests(self._mcp_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "mcp_tool_error" for r in results)

    def test_generates_workflow_tests_with_multiple_tools(self, tmp_path):
        results = generate_mcp_tests(self._mcp_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "mcp_workflow" for r in results)

    def test_generates_validation_tests_for_schema_tools(self, tmp_path):
        results = generate_mcp_tests(self._mcp_config(), TemplateManager(), tmp_path)
        assert any(r.category.value == "mcp_tool_validation" for r in results)


# ── Orchestrator Integration ────────────────────────────────────────────


class TestOrchestratorDispatch:
    def test_generate_tests_with_explicit_cli_type(self, tmp_path):
        from generator.orchestrator import generate_tests

        result = generate_tests(tmp_path, app_type="cli")
        assert result.success
        assert result.total_tests > 0

    def test_generate_tests_with_explicit_api_type(self, tmp_path):
        from generator.orchestrator import generate_tests

        # Create a minimal OpenAPI spec for the API detector
        (tmp_path / "openapi.json").write_text(
            json.dumps(
                {
                    "openapi": "3.0.0",
                    "info": {"title": "Test", "version": "1.0"},
                    "paths": {
                        "/items": {
                            "get": {
                                "summary": "List items",
                                "responses": {"200": {"description": "OK"}},
                            },
                            "post": {
                                "summary": "Create item",
                                "responses": {"201": {"description": "Created"}},
                            },
                        }
                    },
                }
            )
        )
        result = generate_tests(tmp_path, app_type="api")
        assert result.success
        assert result.total_tests > 0

    def test_backward_compat_generate_e2e_tests(self):
        """generate_e2e_tests still exists and is importable."""
        from generator import generate_e2e_tests

        assert callable(generate_e2e_tests)

    def test_all_app_types_importable(self):
        from generator import AppType

        assert AppType.CLI.value == "cli"
        assert AppType.TUI.value == "tui"
        assert AppType.API.value == "api"
        assert AppType.MCP.value == "mcp"
