"""
MCP Configurator for cclsp LSP integration.

Philosophy:
- Configure Claude Code to use cclsp as MCP server
- Generate cclsp.json configuration file
- Add MCP server to Claude Code settings.json
- Zero-BS: Real configuration, no stubs

Public API:
    MCPConfigurator: Configure cclsp MCP server for Claude Code
"""

import json
import subprocess
from pathlib import Path
from typing import Any

__all__ = ["MCPConfigurator", "CCLSPConfig"]


class CCLSPConfig:
    """cclsp.json configuration generator."""

    # Language to LSP server mapping
    LANGUAGE_SERVERS = {
        "python": {"extensions": ["py"], "command": ["pylsp"], "rootDir": "."},
        "javascript": {
            "extensions": ["js", "jsx"],
            "command": ["typescript-language-server", "--stdio"],
            "rootDir": ".",
        },
        "typescript": {
            "extensions": ["ts", "tsx"],
            "command": ["typescript-language-server", "--stdio"],
            "rootDir": ".",
        },
        "rust": {"extensions": ["rs"], "command": ["rust-analyzer"], "rootDir": "."},
        "go": {"extensions": ["go"], "command": ["gopls"], "rootDir": "."},
        "java": {"extensions": ["java"], "command": ["jdtls"], "rootDir": "."},
        "cpp": {
            "extensions": ["cpp", "cxx", "cc", "h", "hpp"],
            "command": ["clangd"],
            "rootDir": ".",
        },
        "c": {"extensions": ["c", "h"], "command": ["clangd"], "rootDir": "."},
        "ruby": {"extensions": ["rb"], "command": ["solargraph", "stdio"], "rootDir": "."},
        "php": {"extensions": ["php"], "command": ["phpactor", "language-server"], "rootDir": "."},
    }

    @classmethod
    def generate_config(cls, languages: list[str]) -> dict[str, Any]:
        """Generate cclsp.json configuration for detected languages."""
        servers = []
        for lang in languages:
            if lang in cls.LANGUAGE_SERVERS:
                servers.append(cls.LANGUAGE_SERVERS[lang])

        return {"servers": servers}


class MCPConfigurator:
    """Configure Claude Code MCP server for cclsp LSP integration."""

    def __init__(self, project_root: Path):
        """Initialize MCP configurator.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root)
        self.cclsp_config_file = self.project_root / "cclsp.json"
        self.claude_settings = self.project_root / ".claude" / "settings.json"

    def generate_cclsp_config(self, languages: list[str]) -> bool:
        """Generate cclsp.json configuration file.

        Args:
            languages: List of language names to configure

        Returns:
            True if successful
        """
        try:
            config = CCLSPConfig.generate_config(languages)

            # Write cclsp.json
            self.cclsp_config_file.write_text(json.dumps(config, indent=2) + "\n")
            return True
        except OSError:
            return False

    def add_mcp_server_to_claude(self) -> bool:
        """Add cclsp MCP server to Claude Code settings.json.

        Returns:
            True if successful
        """
        try:
            # Ensure .claude directory exists
            self.claude_settings.parent.mkdir(parents=True, exist_ok=True)

            # Load or create settings
            if self.claude_settings.exists():
                settings = json.loads(self.claude_settings.read_text())
            else:
                settings = {}

            # Add mcpServers section if not present
            if "mcpServers" not in settings:
                settings["mcpServers"] = {}

            # Add cclsp server configuration
            settings["mcpServers"]["cclsp"] = {"command": "npx", "args": ["cclsp"]}

            # Write back
            self.claude_settings.write_text(json.dumps(settings, indent=2) + "\n")
            return True

        except (OSError, json.JSONDecodeError):
            return False

    def is_cclsp_configured(self) -> bool:
        """Check if cclsp MCP server is configured.

        Returns:
            True if configured
        """
        if not self.claude_settings.exists():
            return False

        try:
            settings = json.loads(self.claude_settings.read_text())
            return "cclsp" in settings.get("mcpServers", {})
        except (OSError, json.JSONDecodeError):
            return False

    def check_cclsp_available(self) -> bool:
        """Check if cclsp is available via npx.

        Returns:
            True if cclsp can be run
        """
        try:
            result = subprocess.run(["npx", "cclsp", "--version"], capture_output=True, timeout=5)
            # cclsp doesn't have --version, but if it runs, it's available
            return result.returncode in [0, 1]  # May return 1 for unknown flag
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
