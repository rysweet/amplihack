"""CLI interface for Serena MCP integration.

This module provides the command-line interface for managing
Serena MCP server configuration.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .configurator import SerenaConfigurator
from .detector import SerenaDetector
from .errors import (
    ConfigurationError,
    SerenaIntegrationError,
    SerenaNotFoundError,
    UvNotFoundError,
)


class SerenaCLI:
    """Command-line interface for Serena integration."""

    def __init__(
        self,
        detector: Optional[SerenaDetector] = None,
        configurator: Optional[SerenaConfigurator] = None,
    ):
        """Initialize CLI.

        Args:
            detector: SerenaDetector instance (creates new one if not provided)
            configurator: SerenaConfigurator instance (creates new one if not provided)
        """
        self.detector = detector or SerenaDetector()
        self.configurator = configurator or SerenaConfigurator(self.detector)

    def setup_parser(self, subparsers: argparse._SubParsersAction) -> None:
        """Set up argument parser for serena subcommand.

        Args:
            subparsers: Subparsers object from parent ArgumentParser
        """
        serena_parser = subparsers.add_parser(
            "serena",
            help="Manage Serena MCP server integration",
            description="Configure and manage the Serena MCP server for Claude Desktop",
        )

        serena_subparsers = serena_parser.add_subparsers(
            dest="serena_command",
            help="Serena subcommands",
            required=True,
        )

        # Status command
        status_parser = serena_subparsers.add_parser(
            "status",
            help="Show Serena detection and configuration status",
        )
        status_parser.set_defaults(func=self.cmd_status)

        # Setup command
        setup_parser = serena_subparsers.add_parser(
            "setup",
            help="Configure Serena MCP server",
        )
        setup_parser.add_argument(
            "--force",
            action="store_true",
            help="Force setup even if already configured",
        )
        setup_parser.set_defaults(func=self.cmd_setup)

        # Remove command
        remove_parser = serena_subparsers.add_parser(
            "remove",
            help="Remove Serena configuration",
        )
        remove_parser.set_defaults(func=self.cmd_remove)

        # Export command
        export_parser = serena_subparsers.add_parser(
            "export",
            help="Export configuration snippet for manual setup",
        )
        export_parser.add_argument(
            "output",
            type=Path,
            nargs="?",
            default=Path("serena_config.json"),
            help="Output file path (default: serena_config.json)",
        )
        export_parser.set_defaults(func=self.cmd_export)

        # Diagnose command
        diagnose_parser = serena_subparsers.add_parser(
            "diagnose",
            help="Show detailed diagnostic information",
        )
        diagnose_parser.set_defaults(func=self.cmd_diagnose)

    def execute(self, args: argparse.Namespace) -> int:
        """Execute the command specified in args.

        Args:
            args: Parsed command-line arguments

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            if hasattr(args, "func"):
                return args.func(args)
            print("Error: No subcommand specified", file=sys.stderr)
            return 1
        except SerenaIntegrationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return 2

    def cmd_status(self, args: argparse.Namespace) -> int:
        """Show detection and configuration status.

        Args:
            args: Parsed command-line arguments

        Returns:
            Exit code (0 for success)
        """
        print("Serena MCP Integration Status")
        print("=" * 40)
        print()

        # Detection status
        result = self.detector.detect_all()
        print("Prerequisites:")
        print(f"  uv available: {'Yes' if result.uv_available else 'No'}")
        if result.uv_path:
            print(f"  uv path: {result.uv_path}")
        print(f"  Serena accessible: {'Yes' if result.serena_available else 'No'}")
        print()

        # Configuration status
        print("Configuration:")
        print(f"  Platform: {result.platform}")
        if result.mcp_config_path:
            print(f"  MCP config path: {result.mcp_config_path}")
            print(f"  Config exists: {'Yes' if result.config_exists else 'No'}")
            is_configured = self.configurator.is_configured()
            print(f"  Serena configured: {'Yes' if is_configured else 'No'}")
        else:
            print("  MCP config path: Not found")
        print()

        # Overall status
        if result.is_ready():
            if self.configurator.is_configured():
                print("Status: Serena is fully configured and ready to use")
            else:
                print("Status: Prerequisites met, ready to configure")
                print("Run 'amplihack serena setup' to configure")
        else:
            print("Status: Prerequisites not met")
            if not result.uv_available:
                print("  - uv is not installed")
            if not result.serena_available:
                print("  - Serena is not accessible")
            if not result.mcp_config_path:
                print("  - MCP config path not found")

        return 0

    def cmd_setup(self, args: argparse.Namespace) -> int:
        """Configure Serena MCP server.

        Args:
            args: Parsed command-line arguments with 'force' attribute

        Returns:
            Exit code (0 for success, 1 for error)
        """
        print("Configuring Serena MCP server...")
        print()

        # Check prerequisites
        result = self.detector.detect_all()
        if not result.uv_available:
            raise UvNotFoundError()
        if not result.serena_available:
            raise SerenaNotFoundError()

        # Check if already configured
        if self.configurator.is_configured() and not args.force:
            print("Serena is already configured.")
            print("Use --force to reconfigure.")
            return 0

        # Add configuration
        try:
            was_added = self.configurator.add_to_mcp_servers()
            if was_added or args.force:
                print("Success! Serena has been configured.")
                print()
                print("Next steps:")
                print("  1. Restart Claude Desktop")
                print("  2. Serena MCP server will be available")
                print()
                if result.mcp_config_path:
                    print(f"Configuration written to: {result.mcp_config_path}")
                return 0
            print("Configuration was already present (use --force to overwrite).")
            return 0
        except ConfigurationError as e:
            raise e

    def cmd_remove(self, args: argparse.Namespace) -> int:
        """Remove Serena configuration.

        Args:
            args: Parsed command-line arguments

        Returns:
            Exit code (0 for success)
        """
        print("Removing Serena MCP configuration...")
        print()

        was_removed = self.configurator.remove_from_mcp_servers()
        if was_removed:
            print("Success! Serena configuration has been removed.")
            print()
            print("Next steps:")
            print("  1. Restart Claude Desktop")
            print("  2. Serena MCP server will no longer be available")
        else:
            print("Serena was not configured (nothing to remove).")

        return 0

    def cmd_export(self, args: argparse.Namespace) -> int:
        """Export configuration snippet for manual setup.

        Args:
            args: Parsed command-line arguments with 'output' attribute

        Returns:
            Exit code (0 for success, 1 for error)
        """
        output_path: Path = args.output
        print(f"Exporting Serena configuration to {output_path}...")
        print()

        try:
            self.configurator.export_to_claude_desktop(output_path)
            print(f"Success! Configuration exported to: {output_path}")
            print()
            print("Manual setup instructions:")
            print("  1. Open your Claude Desktop config file:")

            result = self.detector.detect_all()
            if result.mcp_config_path:
                print(f"     {result.mcp_config_path}")
            else:
                print("     (location depends on your platform)")

            print("  2. Merge the exported configuration into mcpServers section")
            print("  3. Restart Claude Desktop")
            return 0
        except ConfigurationError as e:
            raise e

    def cmd_diagnose(self, args: argparse.Namespace) -> int:
        """Show detailed diagnostic information.

        Args:
            args: Parsed command-line arguments

        Returns:
            Exit code (0 for success)
        """
        print("Serena MCP Integration Diagnostics")
        print("=" * 40)
        print()

        # Full detection
        result = self.detector.detect_all()
        print(result.get_status_summary())
        print()

        # Configuration details
        if result.config_exists:
            print("Configuration Details:")
            try:
                current_config = self.configurator.get_current_config()
                if current_config:
                    print(f"  Name: {current_config.name}")
                    print(f"  Command: {current_config.command}")
                    print(f"  Args: {current_config.args}")
                    print(f"  Env: {current_config.env}")
                else:
                    print("  Serena not configured in mcpServers")
            except Exception as e:
                print(f"  Error reading configuration: {e}")
        else:
            print("Configuration file does not exist yet.")

        print()

        # Recommendations
        print("Recommendations:")
        if not result.uv_available:
            print("  - Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        if not result.serena_available and result.uv_available:
            print("  - Test Serena access manually:")
            print("    uvx --from git+https://github.com/oraios/serena serena --help")
        if result.is_ready() and not self.configurator.is_configured():
            print("  - Run 'amplihack serena setup' to configure")
        if result.is_ready() and self.configurator.is_configured():
            print("  - Serena is fully configured")
            print("  - Restart Claude Desktop if you haven't already")

        return 0
