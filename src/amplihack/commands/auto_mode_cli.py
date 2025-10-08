"""
Auto-Mode CLI Command Implementation

Provides CLI interface for auto-mode functionality through `amplihack auto` command.
Integrates with the core auto-mode orchestrator and provides user-friendly interface.

# noqa: print - CLI code legitimately uses print statements for user interaction
# noqa - "amplihack" is the project name, not a development artifact
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, Optional

from ..auto_mode.command_handler import AutoModeCommandHandler
from ..auto_mode.orchestrator import AutoModeOrchestrator


class AutoModeCLI:
    """
    CLI interface for auto-mode functionality.
    """

    def __init__(self):
        self.orchestrator: Optional[AutoModeOrchestrator] = None
        self.command_handler: Optional[AutoModeCommandHandler] = None

    def create_auto_parser(self, subparsers) -> argparse.ArgumentParser:
        """
        Create the auto command parser.

        Args:
            subparsers: Subparsers from main CLI

        Returns:
            argparse.ArgumentParser: Auto command parser
        """
        auto_parser = subparsers.add_parser(
            "auto",
            help="Auto-mode for persistent conversation analysis and improvement suggestions",
            description="Enable auto-mode for intelligent conversation analysis using Claude Agent SDK",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""Examples:
  amplihack auto start                              # Start auto-mode with default settings
  amplihack auto start --config learning_mode      # Start with learning-focused configuration
  amplihack auto status                            # Check current auto-mode status
  amplihack auto stop                              # Stop auto-mode
  amplihack auto configure --show                  # Show current configuration
  amplihack auto configure analysis_frequency high # Configure analysis frequency
  amplihack auto analyze --output json             # Request immediate analysis (JSON output)
  amplihack auto summary                           # Generate session summary""",
        )

        # Create subcommands for auto-mode
        auto_subparsers = auto_parser.add_subparsers(
            dest="auto_action", help="Auto-mode actions", metavar="ACTION"
        )

        # Start command
        start_parser = auto_subparsers.add_parser("start", help="Start auto-mode session")
        start_parser.add_argument(
            "--config",
            "-c",
            choices=[
                "default",
                "aggressive_analysis",
                "minimal_intervention",
                "learning_mode",
                "privacy_focused",
            ],
            default="default",
            help="Configuration preset to use",
        )
        start_parser.add_argument(
            "--user-id", "-u", help="User identifier (auto-detected if not provided)"
        )
        start_parser.add_argument(
            "--background", "-b", action="store_true", help="Run in background mode (daemon-like)"
        )

        # Stop command
        stop_parser = auto_subparsers.add_parser("stop", help="Stop auto-mode session")
        stop_parser.add_argument(
            "--session-id",
            "-s",
            help="Specific session to stop (stops all user sessions if not provided)",
        )
        stop_parser.add_argument(
            "--save-insights", action="store_true", help="Save learned insights for future sessions"
        )

        # Status command
        status_parser = auto_subparsers.add_parser("status", help="Check auto-mode status")
        status_parser.add_argument(
            "--detailed", "-d", action="store_true", help="Show detailed status information"
        )
        status_parser.add_argument("--session-id", "-s", help="Show status for specific session")
        status_parser.add_argument("--json", action="store_true", help="Output status as JSON")

        # Configure command
        configure_parser = auto_subparsers.add_parser(
            "configure", help="Configure auto-mode settings"
        )
        configure_parser.add_argument(
            "setting",
            nargs="?",
            choices=[
                "analysis_frequency",
                "intervention_threshold",
                "background_mode",
                "learning_mode",
                "privacy_level",
            ],
            help="Setting to configure",
        )
        configure_parser.add_argument(
            "value", nargs="?", help="Value to set (show current values if not provided)"
        )
        configure_parser.add_argument(
            "--show", action="store_true", help="Show current configuration"
        )

        # Analyze command
        analyze_parser = auto_subparsers.add_parser("analyze", help="Request immediate analysis")
        analyze_parser.add_argument(
            "--type",
            "-t",
            choices=["quick", "comprehensive", "quality", "patterns"],
            default="comprehensive",
            help="Type of analysis to perform",
        )
        analyze_parser.add_argument(
            "--scope",
            choices=["current", "session", "recent"],
            default="current",
            help="Scope of analysis",
        )
        analyze_parser.add_argument(
            "--output",
            "-o",
            choices=["summary", "detailed", "json"],
            default="summary",
            help="Output format",
        )

        # Summary command
        summary_parser = auto_subparsers.add_parser("summary", help="Generate session summary")
        summary_parser.add_argument(
            "--format",
            "-f",
            choices=["brief", "detailed", "report"],
            default="detailed",
            help="Summary format",
        )
        summary_parser.add_argument(
            "--include",
            choices=["analysis", "insights", "recommendations", "metrics"],
            nargs="+",
            default=["analysis", "insights", "recommendations"],
            help="Sections to include in summary",
        )
        summary_parser.add_argument("--save", help="Save summary to file")

        # Insights command
        insights_parser = auto_subparsers.add_parser("insights", help="View learned insights")
        insights_parser.add_argument(
            "--category",
            choices=["preferences", "patterns", "optimizations"],
            help="Filter by insight category",
        )
        insights_parser.add_argument(
            "--export",
            choices=["text", "json", "markdown"],
            help="Export insights in specified format",
        )

        # Feedback command
        feedback_parser = auto_subparsers.add_parser(
            "feedback", help="Provide feedback on auto-mode"
        )
        feedback_parser.add_argument(
            "--rating", type=int, choices=range(1, 6), help="Rating from 1-5"
        )
        feedback_parser.add_argument("--comment", help="Detailed feedback comment")
        feedback_parser.add_argument(
            "--suggestion-id", help="Provide feedback on specific suggestion"
        )

        return auto_parser

    async def handle_auto_command(self, args: argparse.Namespace) -> int:
        """
        Handle auto command execution.

        Args:
            args: Parsed command arguments

        Returns:
            int: Exit code
        """
        try:
            if not args.auto_action:
                print(
                    "Error: No auto-mode action specified. Use 'amplihack auto --help' for available actions."
                )
                return 1

            # Initialize command handler if needed
            if not self.command_handler:
                self.command_handler = AutoModeCommandHandler()

            # Build command string for handler
            command_parts = [args.auto_action]

            # Add arguments based on action
            if args.auto_action == "start":
                if hasattr(args, "config"):
                    command_parts.extend(["--config", args.config])
                if hasattr(args, "user_id") and args.user_id:
                    command_parts.extend(["--user-id", args.user_id])

            elif args.auto_action == "stop":
                if hasattr(args, "session_id") and args.session_id:
                    command_parts.extend(["--session-id", args.session_id])
                if hasattr(args, "save_insights") and args.save_insights:
                    command_parts.append("--save-insights")

            elif args.auto_action == "status":
                if hasattr(args, "detailed") and args.detailed:
                    command_parts.append("--detailed")
                if hasattr(args, "session_id") and args.session_id:
                    command_parts.extend(["--session-id", args.session_id])

            elif args.auto_action == "configure":
                if hasattr(args, "setting") and args.setting:
                    command_parts.append(args.setting)
                    if hasattr(args, "value") and args.value:
                        command_parts.append(args.value)

            elif args.auto_action == "analyze":
                if hasattr(args, "type"):
                    command_parts.extend(["--type", args.type])
                if hasattr(args, "scope"):
                    command_parts.extend(["--scope", args.scope])
                if hasattr(args, "output"):
                    command_parts.extend(["--output", args.output])

            elif args.auto_action == "summary":
                if hasattr(args, "format"):
                    command_parts.extend(["--format", args.format])
                if hasattr(args, "include"):
                    command_parts.extend(["--include", ",".join(args.include)])

            # Build context
            context = {
                "user_id": getattr(args, "user_id", "cli_user"),
                "conversation_context": {},
                "cli_mode": True,
            }

            # Execute command
            command_string = " ".join(command_parts)
            result = await self.command_handler.handle_command(command_string, context)

            # Handle output
            return self._handle_command_result(result, args)

        except Exception as e:
            print(f"Error executing auto-mode command: {e}", file=sys.stderr)
            return 1

    def _handle_command_result(self, result, args: argparse.Namespace) -> int:
        """
        Handle command result output and return appropriate exit code.

        Args:
            result: Command result from handler
            args: Original command arguments

        Returns:
            int: Exit code
        """
        try:
            if not result.success:
                print(f"Error: {result.message}", file=sys.stderr)
                if result.error_code:
                    print(f"Error code: {result.error_code}", file=sys.stderr)
                return 1

            # Handle JSON output for status command
            if hasattr(args, "json") and args.json and args.auto_action == "status" and result.data:
                print(json.dumps(result.data, indent=2))
                return 0

            # Handle JSON output for analyze command
            if (
                hasattr(args, "output")
                and args.output == "json"
                and args.auto_action == "analyze"
                and result.data
            ):
                print(json.dumps(result.data, indent=2))
                return 0

            # Default text output
            print(result.message)

            # Print additional data if available
            if result.data and not (hasattr(args, "json") and args.json):
                if args.auto_action == "start":
                    print(f"Session ID: {result.data.get('session_id', 'unknown')}")
                    print(f"Configuration: {result.data.get('config', 'default')}")
                    print(f"Status: {result.data.get('status', 'unknown')}")

                elif args.auto_action == "status":
                    self._print_status_info(result.data)

                elif args.auto_action == "configure" and not hasattr(args, "setting"):
                    self._print_configuration(result.data)

            return 0

        except Exception as e:
            print(f"Error formatting command output: {e}", file=sys.stderr)
            return 1

    def _print_status_info(self, status_data: Dict[str, Any]):
        """Print formatted status information."""
        print("\nAuto-Mode Status:")
        print(f"  Status: {status_data.get('status', 'unknown')}")
        print(f"  Active Sessions: {status_data.get('active_sessions', 0)}")

        if status_data.get("total_sessions", 0) > 0:
            print(f"  Total Sessions: {status_data.get('total_sessions')}")
            print(f"  Analysis Cycles: {status_data.get('analysis_cycles', 0)}")
            print(f"  Interventions: {status_data.get('interventions', 0)}")
            print(f"  Average Quality: {status_data.get('average_quality', 0):.2f}")
            print(f"  Uptime: {status_data.get('uptime', '0s')}")

        print(f"  SDK Connection: {status_data.get('sdk_connection', 'unknown')}")

        # Print detailed info if available
        if "detailed_metrics" in status_data:
            print("\nDetailed Metrics:")
            metrics = status_data["detailed_metrics"]
            for key, value in metrics.items():
                if key not in ["uptime_seconds"]:  # Skip already shown items
                    print(f"  {key.replace('_', ' ').title()}: {value}")

    def _print_configuration(self, config_data: Dict[str, Any]):
        """Print formatted configuration information."""
        print("\nCurrent Configuration:")
        for key, value in config_data.items():
            formatted_key = key.replace("_", " ").title()
            print(f"  {formatted_key}: {value}")

    async def run_interactive_mode(self, args: argparse.Namespace) -> int:
        """
        Run auto-mode in interactive mode.

        Args:
            args: Command arguments

        Returns:
            int: Exit code
        """
        print("🤖 Auto-Mode Interactive Session")
        print("Type 'help' for available commands, 'quit' to exit")

        try:
            while True:
                try:
                    command_input = input("\nauto-mode> ").strip()

                    if not command_input:
                        continue

                    if command_input.lower() in ["quit", "exit"]:
                        print("Goodbye!")
                        break

                    if command_input.lower() == "help":
                        self._print_interactive_help()
                        continue

                    # Parse the command
                    command_parts = command_input.split()
                    if not command_parts:
                        continue

                    # Create mock args for the command
                    mock_args = argparse.Namespace()
                    mock_args.auto_action = command_parts[0]

                    # Simple argument parsing for interactive mode
                    for i, part in enumerate(command_parts[1:], 1):
                        if part.startswith("--"):
                            key = part[2:].replace("-", "_")
                            if i + 1 < len(command_parts) and not command_parts[i + 1].startswith(
                                "--"
                            ):
                                setattr(mock_args, key, command_parts[i + 1])
                            else:
                                setattr(mock_args, key, True)

                    # Execute the command
                    result_code = await self.handle_auto_command(mock_args)

                    if result_code != 0:
                        print(f"Command failed with exit code: {result_code}")

                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit auto-mode")
                    continue
                except Exception as e:
                    print(f"Error: {e}")
                    continue

            return 0

        except KeyboardInterrupt:
            print("\nGoodbye!")
            return 0

    def _print_interactive_help(self):
        """Print help for interactive mode."""
        print("""
Available commands:
  start [--config CONFIG]     Start auto-mode session
  stop [--session-id ID]      Stop auto-mode session
  status [--detailed]         Check auto-mode status
  configure [SETTING VALUE]   Configure auto-mode settings
  analyze [--type TYPE]       Request immediate analysis
  summary [--format FORMAT]  Generate session summary
  insights [--category CAT]   View learned insights
  feedback [--rating N]       Provide feedback
  help                        Show this help
  quit                        Exit auto-mode

Examples:
  start --config learning_mode
  status --detailed
  configure analysis_frequency high
  analyze --type comprehensive --output json
""")


def auto_command_handler(args: argparse.Namespace) -> int:
    """
    Entry point for auto command from CLI.

    Args:
        args: Parsed command arguments

    Returns:
        int: Exit code
    """
    cli = AutoModeCLI()

    # Check if this should be interactive mode
    if not hasattr(args, "auto_action") or not args.auto_action:
        # Interactive mode
        return asyncio.run(cli.run_interactive_mode(args))
    # Single command mode
    return asyncio.run(cli.handle_auto_command(args))


# Export for CLI integration
__all__ = ["AutoModeCLI", "auto_command_handler"]
