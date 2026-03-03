"""App type detection for project classification.

Detects whether a project is a Web app, CLI app, TUI app, API, or MCP server
by analyzing project structure, dependencies, and configuration files.
"""

import json
import re
from pathlib import Path
from typing import Any

from .models import (
    APIConfig,
    APIEndpointSpec,
    AppType,
    CLICommand,
    CLIConfig,
    MCPConfig,
    MCPResource,
    MCPTool,
    TUIConfig,
    TUIWidget,
)
from .utils import find_files, read_file

# Framework detection markers by app type
CLI_MARKERS = {
    "python": {
        "argparse": ["import argparse", "from argparse import"],
        "click": ["import click", "from click import", "@click.command", "@click.group"],
        "typer": ["import typer", "from typer import", "typer.Typer()"],
        "fire": ["import fire", "fire.Fire("],
    },
    "javascript": {
        "commander": ["require('commander')", "from 'commander'", "new Command("],
        "yargs": ["require('yargs')", "from 'yargs'", ".command("],
        "meow": ["require('meow')", "from 'meow'"],
        "oclif": ["@oclif/core", "extends Command"],
    },
    "rust": {
        "clap": ["use clap::", "#[derive(Parser)]", "clap = "],
        "structopt": ["use structopt::", "#[derive(StructOpt)]"],
    },
    "go": {
        "cobra": ["github.com/spf13/cobra", "cobra.Command"],
        "urfave_cli": ["github.com/urfave/cli", "cli.App"],
    },
}

TUI_MARKERS = {
    "python": {
        "textual": ["from textual", "import textual", "class.*App.*textual"],
        "rich": ["from rich", "import rich", "Console()"],
        "blessed": ["import blessed", "from blessed"],
        "curses": ["import curses", "curses.wrapper"],
        "prompt_toolkit": ["from prompt_toolkit", "import prompt_toolkit"],
    },
    "javascript": {
        "ink": ["from 'ink'", "require('ink')", "render(<"],
        "blessed": ["require('blessed')", "from 'blessed'"],
        "neo-blessed": ["require('neo-blessed')"],
    },
    "rust": {
        "ratatui": ["use ratatui::", "ratatui = "],
        "cursive": ["use cursive::", "cursive = "],
        "tui": ["use tui::", "tui = "],
    },
    "go": {
        "bubbletea": ["github.com/charmbracelet/bubbletea", "tea.Model"],
        "tview": ["github.com/rivo/tview", "tview.NewApplication"],
    },
}

API_SPEC_FILES = [
    "openapi.yaml",
    "openapi.yml",
    "openapi.json",
    "swagger.yaml",
    "swagger.yml",
    "swagger.json",
    "api-spec.yaml",
    "api-spec.json",
    "docs/openapi.yaml",
    "docs/openapi.json",
    "docs/swagger.yaml",
    "docs/swagger.json",
]

MCP_CONFIG_FILES = [
    "mcp.json",
    ".mcp.json",
    "mcp-config.json",
    "claude_desktop_config.json",
    "package.json",  # may contain MCP tool definitions
]


def detect_app_type(project_root: Path, explicit_type: str | None = None) -> AppType:
    """Detect the application type from project structure.

    Args:
        project_root: Path to project root
        explicit_type: Explicitly specified app type (overrides detection)

    Returns:
        Detected AppType
    """
    if explicit_type:
        try:
            return AppType(explicit_type.lower())
        except ValueError:
            pass

    # Check in priority order: MCP > API > TUI > CLI > Web
    # MCP and API have very specific markers so check first
    if _is_mcp_project(project_root):
        return AppType.MCP
    if _is_api_project(project_root):
        return AppType.API
    if _is_tui_project(project_root):
        return AppType.TUI
    if _is_cli_project(project_root):
        return AppType.CLI
    return AppType.WEB


def detect_cli_config(project_root: Path) -> CLIConfig:
    """Detect CLI application configuration.

    Args:
        project_root: Path to project root

    Returns:
        CLIConfig with detected commands, args, and flags
    """
    config = CLIConfig()
    framework, language = _detect_cli_framework(project_root)
    config.framework = framework
    config.binary_path = _find_binary_path(project_root, language)
    config.commands = _extract_cli_commands(project_root, framework, language)
    config.global_flags = _extract_global_flags(project_root, framework, language)
    config.has_interactive_mode = _has_interactive_mode(project_root, language)
    return config


def detect_tui_config(project_root: Path) -> TUIConfig:
    """Detect TUI application configuration.

    Args:
        project_root: Path to project root

    Returns:
        TUIConfig with detected widgets and navigation
    """
    config = TUIConfig()
    framework, language = _detect_tui_framework(project_root)
    config.framework = framework
    config.binary_path = _find_binary_path(project_root, language)
    config.widgets = _extract_tui_widgets(project_root, framework, language)
    config.screens = _extract_tui_screens(project_root, framework, language)
    config.keyboard_shortcuts = _extract_keyboard_shortcuts(project_root, framework, language)
    return config


def detect_api_config(project_root: Path) -> APIConfig:
    """Detect API configuration from OpenAPI/Swagger spec.

    Args:
        project_root: Path to project root

    Returns:
        APIConfig with parsed endpoints and schemas
    """
    config = APIConfig()
    spec_file, spec_data = _find_and_parse_api_spec(project_root)
    if spec_file and spec_data:
        config.spec_file = str(spec_file)
        config.spec_format = "swagger" if "swagger" in spec_data else "openapi"
        config.base_url = _extract_base_url(spec_data)
        config.api_version = spec_data.get("info", {}).get("version", "")
        config.endpoints = _extract_api_endpoints(spec_data)
        config.auth_type = _extract_auth_type(spec_data)
        config.schemas = spec_data.get("components", {}).get("schemas", {})
    return config


def detect_mcp_config(project_root: Path) -> MCPConfig:
    """Detect MCP server configuration.

    Args:
        project_root: Path to project root

    Returns:
        MCPConfig with detected tools and resources
    """
    config = MCPConfig()
    mcp_data = _find_and_parse_mcp_config(project_root)
    if mcp_data:
        config.server_command = mcp_data.get("command", "")
        config.server_args = mcp_data.get("args", [])
        config.transport = mcp_data.get("transport", "stdio")
        config.tools = _extract_mcp_tools(mcp_data, project_root)
        config.resources = _extract_mcp_resources(mcp_data, project_root)
        config.protocol_version = mcp_data.get("protocolVersion", "")
    return config


# --- Private detection helpers ---


def _is_mcp_project(project_root: Path) -> bool:
    """Check if project is an MCP server."""
    for config_file in MCP_CONFIG_FILES:
        path = project_root / config_file
        if path.exists():
            try:
                content = read_file(path)
                if any(
                    marker in content
                    for marker in [
                        "mcpServers",
                        "mcp-server",
                        '"tools"',
                        "McpServer",
                        "mcp.tool",
                        "@modelcontextprotocol",
                        "from mcp",
                        "import mcp",
                    ]
                ):
                    return True
            except Exception:
                continue

    # Check for MCP SDK imports in source files
    for pattern in ["*.py", "*.ts", "*.js"]:
        for f in _filter_vendor_files(find_files(project_root, pattern)):
            try:
                content = read_file(f)
                if any(
                    marker in content
                    for marker in [
                        "from mcp.server",
                        "import { McpServer",
                        "@modelcontextprotocol/sdk",
                        "mcp.tool(",
                    ]
                ):
                    return True
            except Exception:
                continue
    return False


def _is_api_project(project_root: Path) -> bool:
    """Check if project has an API spec file."""
    for spec_file in API_SPEC_FILES:
        if (project_root / spec_file).exists():
            return True
    return False


def _is_tui_project(project_root: Path) -> bool:
    """Check if project uses a TUI framework."""
    framework, _ = _detect_tui_framework(project_root)
    return framework != "unknown"


def _is_cli_project(project_root: Path) -> bool:
    """Check if project uses a CLI framework."""
    framework, _ = _detect_cli_framework(project_root)
    return framework != "unknown"


def _filter_vendor_files(files: list[Path]) -> list[Path]:
    """Filter out vendor, node_modules, and other non-project directories."""
    skip_dirs = ("vendor", "node_modules", "dist", ".venv", "__pycache__", ".git")
    return [f for f in files if not any(skip in f.parts for skip in skip_dirs)]


def _detect_cli_framework(project_root: Path) -> tuple[str, str]:
    """Detect CLI framework and language."""
    for language, frameworks in CLI_MARKERS.items():
        extensions = _language_extensions(language)
        for ext in extensions:
            for f in _filter_vendor_files(find_files(project_root, f"*{ext}")):
                try:
                    content = read_file(f)
                    for framework, markers in frameworks.items():
                        if any(marker in content for marker in markers):
                            return framework, language
                except Exception:
                    continue
    return "unknown", "unknown"


def _detect_tui_framework(project_root: Path) -> tuple[str, str]:
    """Detect TUI framework and language."""
    for language, frameworks in TUI_MARKERS.items():
        extensions = _language_extensions(language)
        for ext in extensions:
            for f in _filter_vendor_files(find_files(project_root, f"*{ext}")):
                try:
                    content = read_file(f)
                    for framework, markers in frameworks.items():
                        if any(marker in content for marker in markers):
                            return framework, language
                except Exception:
                    continue
    return "unknown", "unknown"


def _language_extensions(language: str) -> list[str]:
    """Get file extensions for a language."""
    return {
        "python": [".py"],
        "javascript": [".js", ".ts", ".mjs"],
        "rust": [".rs"],
        "go": [".go"],
    }.get(language, [])


def _find_binary_path(project_root: Path, language: str) -> str:
    """Find the binary/entry point path."""
    if language == "python":
        for name in ["cli.py", "main.py", "app.py", "__main__.py"]:
            candidates = find_files(project_root, name)
            # Filter out vendor/node_modules directories
            candidates = [c for c in candidates if not any(
                skip in c.parts for skip in ("vendor", "node_modules", ".venv", "__pycache__")
            )]
            if candidates:
                return str(candidates[0].relative_to(project_root))
        return "python -m <module>"
    elif language == "javascript":
        pkg_json = project_root / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(read_file(pkg_json))
                if "bin" in data:
                    bins = data["bin"]
                    if isinstance(bins, str):
                        return bins
                    if isinstance(bins, dict):
                        return list(bins.values())[0]
            except Exception:
                pass
        return "node index.js"
    elif language == "rust":
        return "cargo run --"
    elif language == "go":
        return "go run ."
    return "./<app>"


def _extract_cli_commands(
    project_root: Path, framework: str, language: str
) -> list[CLICommand]:
    """Extract CLI commands from source code."""
    commands = []
    extensions = _language_extensions(language)

    # Prioritize CLI entry point files, exclude vendor directories
    priority_names = ["cli", "main", "app", "__main__", "commands", "cmd"]
    for ext in extensions:
        all_files = find_files(project_root, f"*{ext}")
        # Filter out vendor/node_modules/dist directories
        filtered = [f for f in all_files if not any(
            skip in f.parts for skip in ("vendor", "node_modules", "dist", ".venv", "__pycache__")
        )]
        # Sort: priority files first
        prioritized = sorted(filtered, key=lambda f: (
            0 if f.stem in priority_names else 1,
            str(f),
        ))
        for f in prioritized:
            try:
                content = read_file(f)
                commands.extend(_parse_commands_from_content(content, framework))
            except Exception:
                continue

    # Deduplicate by name
    seen = set()
    unique = []
    for cmd in commands:
        if cmd.name not in seen:
            seen.add(cmd.name)
            unique.append(cmd)
    return unique


def _parse_commands_from_content(content: str, framework: str) -> list[CLICommand]:
    """Parse CLI commands from file content based on framework."""
    commands = []

    if framework == "click":
        # @click.command() / @click.group()
        cmd_pattern = re.compile(
            r'@(?:click\.command|.*\.command)\(["\']?([^"\')\s]*)["\']?\)',
            re.MULTILINE,
        )
        for match in cmd_pattern.finditer(content):
            name = match.group(1) or "main"
            commands.append(CLICommand(name=name))

        # @click.option / @click.argument
        opt_pattern = re.compile(
            r"@click\.option\(['\"](-[-\w]+)['\"]",
            re.MULTILINE,
        )
        arg_pattern = re.compile(
            r"@click\.argument\(['\"](\w+)['\"]",
            re.MULTILINE,
        )
        flags = [m.group(1) for m in opt_pattern.finditer(content)]
        args = [m.group(1) for m in arg_pattern.finditer(content)]
        if commands:
            commands[-1].flags = flags
            commands[-1].args = args

    elif framework == "typer":
        cmd_pattern = re.compile(
            r'@(?:app|cli)\.command\(["\']?([^"\')\s]*)["\']?\)',
            re.MULTILINE,
        )
        for match in cmd_pattern.finditer(content):
            name = match.group(1) or "main"
            commands.append(CLICommand(name=name))

    elif framework == "argparse":
        # add_subparsers / add_parser
        sub_pattern = re.compile(
            r'add_parser\(["\'](\w+)["\']',
            re.MULTILINE,
        )
        for match in sub_pattern.finditer(content):
            commands.append(CLICommand(name=match.group(1)))

        # add_argument
        arg_pattern = re.compile(
            r'add_argument\(["\'](-[-\w]+)["\']',
            re.MULTILINE,
        )
        flags = [m.group(1) for m in arg_pattern.finditer(content)]
        if commands:
            commands[-1].flags = flags

    elif framework == "commander":
        cmd_pattern = re.compile(
            r"\.command\(['\"](\w+)['\"]",
            re.MULTILINE,
        )
        for match in cmd_pattern.finditer(content):
            commands.append(CLICommand(name=match.group(1)))

    elif framework == "yargs":
        cmd_pattern = re.compile(
            r"\.command\(['\"](\w+)['\"]",
            re.MULTILINE,
        )
        for match in cmd_pattern.finditer(content):
            commands.append(CLICommand(name=match.group(1)))

    elif framework == "clap":
        # Rust clap: #[arg] or .arg(Arg::new("name"))
        cmd_pattern = re.compile(
            r'Subcommand[^{]*\{([^}]+)\}',
            re.MULTILINE | re.DOTALL,
        )
        for match in cmd_pattern.finditer(content):
            variants = re.findall(r'(\w+)', match.group(1))
            for v in variants:
                if v[0].isupper():
                    commands.append(CLICommand(name=v.lower()))

    return commands


def _extract_global_flags(
    project_root: Path, framework: str, language: str
) -> list[str]:
    """Extract global flags from the CLI app."""
    # Common flags that most CLIs support
    return ["--help", "--version", "--verbose", "--quiet"]


def _has_interactive_mode(project_root: Path, language: str) -> bool:
    """Check if CLI has an interactive/REPL mode."""
    extensions = _language_extensions(language)
    for ext in extensions:
        for f in _filter_vendor_files(find_files(project_root, f"*{ext}")):
            try:
                content = read_file(f)
                if any(
                    marker in content
                    for marker in ["interactive", "repl", "shell", "prompt"]
                ):
                    return True
            except Exception:
                continue
    return False


def _extract_tui_widgets(
    project_root: Path, framework: str, language: str
) -> list[TUIWidget]:
    """Extract TUI widgets from source code."""
    widgets = []
    extensions = _language_extensions(language)

    widget_patterns = {
        "textual": {
            "DataTable": "table",
            "ListView": "list",
            "Input": "input",
            "Button": "button",
            "TextArea": "input",
            "Tree": "tree",
            "Header": "panel",
            "Footer": "panel",
            "Static": "panel",
        },
        "ink": {
            "TextInput": "input",
            "SelectInput": "list",
            "Box": "panel",
            "Text": "panel",
        },
        "ratatui": {
            "Table": "table",
            "List": "list",
            "Paragraph": "panel",
            "Block": "panel",
            "Tabs": "panel",
        },
        "bubbletea": {
            "list.Model": "list",
            "table.Model": "table",
            "textinput.Model": "input",
            "viewport.Model": "panel",
        },
    }

    framework_widgets = widget_patterns.get(framework, {})
    for ext in extensions:
        for f in _filter_vendor_files(find_files(project_root, f"*{ext}")):
            try:
                content = read_file(f)
                for widget_name, widget_type in framework_widgets.items():
                    if widget_name in content:
                        widgets.append(
                            TUIWidget(name=widget_name, widget_type=widget_type)
                        )
            except Exception:
                continue

    # Deduplicate
    seen = set()
    unique = []
    for w in widgets:
        if w.name not in seen:
            seen.add(w.name)
            unique.append(w)
    return unique


def _extract_tui_screens(
    project_root: Path, framework: str, language: str
) -> list[str]:
    """Extract TUI screen names from source code."""
    screens = []
    extensions = _language_extensions(language)

    for ext in extensions:
        for f in _filter_vendor_files(find_files(project_root, f"*{ext}")):
            try:
                content = read_file(f)
                if framework == "textual":
                    # class MyScreen(Screen):
                    pattern = re.compile(r"class\s+(\w+)\s*\(.*Screen.*\)")
                    screens.extend(m.group(1) for m in pattern.finditer(content))
                elif framework == "bubbletea":
                    # Look for model struct names
                    pattern = re.compile(r"type\s+(\w+Model)\s+struct")
                    screens.extend(m.group(1) for m in pattern.finditer(content))
            except Exception:
                continue
    return list(set(screens))


def _extract_keyboard_shortcuts(
    project_root: Path, framework: str, language: str
) -> dict[str, str]:
    """Extract keyboard shortcuts from TUI source code."""
    shortcuts: dict[str, str] = {}
    extensions = _language_extensions(language)

    for ext in extensions:
        for f in _filter_vendor_files(find_files(project_root, f"*{ext}")):
            try:
                content = read_file(f)
                if framework == "textual":
                    # BINDINGS = [Binding("q", "quit", "Quit")]
                    pattern = re.compile(
                        r'Binding\(["\'](\w+)["\'],\s*["\'](\w+)["\']'
                    )
                    for m in pattern.finditer(content):
                        shortcuts[m.group(1)] = m.group(2)
                elif framework == "bubbletea":
                    # key.Matches(msg, "q") => quit
                    pattern = re.compile(
                        r'key\.Matches\(.*["\'](\w+)["\'].*\)'
                    )
                    for m in pattern.finditer(content):
                        shortcuts[m.group(1)] = m.group(1)
            except Exception:
                continue
    return shortcuts


def _find_and_parse_api_spec(
    project_root: Path,
) -> tuple[Path | None, dict | None]:
    """Find and parse OpenAPI/Swagger spec file."""
    for spec_file in API_SPEC_FILES:
        path = project_root / spec_file
        if path.exists():
            try:
                content = read_file(path)
                if path.suffix in [".json"]:
                    data = json.loads(content)
                else:
                    # Simple YAML parsing for OpenAPI (avoid yaml dependency)
                    data = _simple_yaml_parse(content)
                if data and ("openapi" in data or "swagger" in data or "paths" in data):
                    return path, data
            except Exception:
                continue
    return None, None


def _simple_yaml_parse(content: str) -> dict[str, Any]:
    """Minimal YAML-to-dict parser for OpenAPI specs.

    Handles flat key-value pairs and basic nested structures.
    For complex specs, falls back to treating as empty.
    """
    try:
        # Try json first (some .yaml files are actually JSON)
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Basic key-value extraction from YAML
    result: dict[str, Any] = {}
    for line in content.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#") and not line.startswith("-"):
            key, _, value = line.partition(":")
            key = key.strip().strip('"').strip("'")
            value = value.strip().strip('"').strip("'")
            if value:
                result[key] = value
    return result


def _extract_base_url(spec_data: dict) -> str:
    """Extract base URL from API spec."""
    # OpenAPI 3.x
    servers = spec_data.get("servers", [])
    if servers and isinstance(servers, list):
        if isinstance(servers[0], dict):
            return servers[0].get("url", "http://localhost:3000")
    # Swagger 2.x
    host = spec_data.get("host", "localhost:3000")
    base_path = spec_data.get("basePath", "")
    scheme = "https" if "https" in spec_data.get("schemes", []) else "http"
    return f"{scheme}://{host}{base_path}"


def _extract_api_endpoints(spec_data: dict) -> list[APIEndpointSpec]:
    """Extract API endpoints from OpenAPI spec."""
    endpoints = []
    paths = spec_data.get("paths", {})
    if not isinstance(paths, dict):
        return endpoints

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue
            if not isinstance(details, dict):
                continue

            endpoint = APIEndpointSpec(
                path=path,
                method=method.upper(),
                operation_id=details.get("operationId", ""),
                summary=details.get("summary", ""),
                description=details.get("description", ""),
                tags=details.get("tags", []),
                requires_auth=bool(details.get("security")),
            )

            # Extract request body schema
            request_body = details.get("requestBody", {})
            if isinstance(request_body, dict):
                content = request_body.get("content", {})
                if isinstance(content, dict):
                    json_content = content.get("application/json", {})
                    if isinstance(json_content, dict):
                        endpoint.request_body_schema = json_content.get("schema")

            # Extract response schema
            responses = details.get("responses", {})
            if isinstance(responses, dict):
                for status_code in ["200", "201"]:
                    resp = responses.get(status_code, {})
                    if isinstance(resp, dict):
                        resp_content = resp.get("content", {})
                        if isinstance(resp_content, dict):
                            json_resp = resp_content.get("application/json", {})
                            if isinstance(json_resp, dict):
                                endpoint.response_schema = json_resp.get("schema")
                                break

            # Extract parameters
            params = details.get("parameters", [])
            if isinstance(params, list):
                endpoint.parameters = [p for p in params if isinstance(p, dict)]

            endpoints.append(endpoint)

    return endpoints


def _extract_auth_type(spec_data: dict) -> str:
    """Extract authentication type from API spec."""
    security_schemes = (
        spec_data.get("components", {}).get("securitySchemes", {})
        or spec_data.get("securityDefinitions", {})
    )
    if not isinstance(security_schemes, dict):
        return "none"

    for _, scheme in security_schemes.items():
        if not isinstance(scheme, dict):
            continue
        scheme_type = scheme.get("type", "")
        if scheme_type == "http" and scheme.get("scheme") == "bearer":
            return "bearer"
        if scheme_type == "apiKey":
            return "api_key"
        if scheme_type == "oauth2":
            return "oauth2"
        if scheme_type == "http" and scheme.get("scheme") == "basic":
            return "basic"
    return "none"


def _find_and_parse_mcp_config(project_root: Path) -> dict | None:
    """Find and parse MCP configuration."""
    # Check for dedicated MCP config files
    for config_file in ["mcp.json", ".mcp.json", "mcp-config.json"]:
        path = project_root / config_file
        if path.exists():
            try:
                return json.loads(read_file(path))
            except Exception:
                continue

    # Check package.json for MCP server info
    pkg_path = project_root / "package.json"
    if pkg_path.exists():
        try:
            data = json.loads(read_file(pkg_path))
            if "mcpServers" in data or "@modelcontextprotocol" in str(
                data.get("dependencies", {})
            ):
                return {
                    "command": "node",
                    "args": [data.get("main", "index.js")],
                    "transport": "stdio",
                    "_package": data,
                }
        except Exception:
            pass

    # Check Python setup for MCP
    for setup_file in ["setup.py", "pyproject.toml"]:
        path = project_root / setup_file
        if path.exists():
            try:
                content = read_file(path)
                if "mcp" in content.lower():
                    return {
                        "command": "python",
                        "args": ["-m", project_root.name],
                        "transport": "stdio",
                    }
            except Exception:
                continue

    return None


def _extract_mcp_tools(mcp_data: dict, project_root: Path) -> list[MCPTool]:
    """Extract MCP tool definitions from config or source code."""
    tools = []

    # From explicit config
    config_tools = mcp_data.get("tools", [])
    if isinstance(config_tools, list):
        for tool_def in config_tools:
            if isinstance(tool_def, dict):
                tools.append(
                    MCPTool(
                        name=tool_def.get("name", ""),
                        description=tool_def.get("description", ""),
                        input_schema=tool_def.get("inputSchema", {}),
                        required_inputs=tool_def.get("inputSchema", {})
                        .get("required", []),
                    )
                )

    # From source code (Python MCP SDK patterns)
    if not tools:
        for f in _filter_vendor_files(find_files(project_root, "*.py")):
            try:
                content = read_file(f)
                # @server.tool() or @mcp.tool()
                pattern = re.compile(
                    r'@(?:server|mcp)\.tool\(\)\s*(?:async\s+)?def\s+(\w+)',
                    re.MULTILINE,
                )
                for match in pattern.finditer(content):
                    tools.append(MCPTool(name=match.group(1)))

                # server.add_tool(Tool(name="..."))
                pattern2 = re.compile(
                    r'Tool\(\s*name\s*=\s*["\'](\w+)["\']',
                    re.MULTILINE,
                )
                for match in pattern2.finditer(content):
                    tools.append(MCPTool(name=match.group(1)))
            except Exception:
                continue

    # From source code (TypeScript MCP SDK patterns)
    if not tools:
        for f in _filter_vendor_files(find_files(project_root, "*.ts")):
            try:
                content = read_file(f)
                # server.tool("name", ...)
                pattern = re.compile(
                    r'\.tool\(\s*["\'](\w+)["\']',
                    re.MULTILINE,
                )
                for match in pattern.finditer(content):
                    tools.append(MCPTool(name=match.group(1)))
            except Exception:
                continue

    # Deduplicate
    seen = set()
    unique = []
    for t in tools:
        if t.name and t.name not in seen:
            seen.add(t.name)
            unique.append(t)
    return unique


def _extract_mcp_resources(mcp_data: dict, project_root: Path) -> list[MCPResource]:
    """Extract MCP resource definitions."""
    resources = []
    config_resources = mcp_data.get("resources", [])
    if isinstance(config_resources, list):
        for res_def in config_resources:
            if isinstance(res_def, dict):
                resources.append(
                    MCPResource(
                        uri=res_def.get("uri", ""),
                        name=res_def.get("name", ""),
                        description=res_def.get("description", ""),
                        mime_type=res_def.get("mimeType", ""),
                    )
                )
    return resources
