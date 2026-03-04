"""CLI argument parsing and subcommand definitions for amplihack.

This module contains all argparse-related code: the main parser,
subcommand parsers, and shared argument groups.

Public API:
    create_parser: Build the full ArgumentParser for the amplihack CLI
    parse_args_with_passthrough: Parse args with support for -- separator
    add_auto_mode_args: Add auto mode arguments to a parser
    add_common_sdk_args: Add common SDK arguments to a parser
    add_claude_specific_args: Add Claude-specific arguments to a parser
    IS_WINDOWS: Platform flag
    EMOJI: Platform-safe emoji mapping
    _CLAUDE_COMMANDS: Commands that require Claude Code plugin installation
"""

import argparse
import platform
import sys
from pathlib import Path

# Platform-specific emoji support
IS_WINDOWS = platform.system() == "Windows"
EMOJI = {
    "check": "[OK]" if IS_WINDOWS else "\u2713",
}

# Commands that require Claude Code plugin installation.
# All other commands (copilot, amplifier, codex, etc.) skip it.
_CLAUDE_COMMANDS = {None, "launch", "claude", "RustyClawd"}


def add_auto_mode_args(parser: argparse.ArgumentParser) -> None:
    """Add auto mode arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in autonomous agentic mode with iterative loop (clarify \u2192 plan \u2192 execute \u2192 evaluate). Usage: --auto -- -p 'your task'. See docs/AUTO_MODE.md for details.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max turns for auto mode (default: 10). Guidance: 5-10 for simple tasks, 10-15 for medium complexity, 15-30 for complex tasks.",
    )
    parser.add_argument(
        "--append",
        metavar="PROMPT",
        help="Append new instructions to a running auto mode session. Finds the active auto mode log directory in the current project and injects the new prompt.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Enable interactive UI mode for auto mode (requires Rich library). Shows real-time execution state, logs, and allows prompt injection.",
    )


def add_common_sdk_args(parser: argparse.ArgumentParser) -> None:
    """Add common SDK arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable post-session reflection analysis. Reflection normally runs after sessions to capture insights and learnings.",
    )
    parser.add_argument(
        "--subprocess-safe",
        action="store_true",
        help="Skip all staging/env updates (staging, cleanup, settings sync). "
        "Use when running as a subprocess delegate from an existing amplihack "
        "session to avoid concurrent write races on ~/.amplihack/.claude/.",
    )


def add_claude_specific_args(parser: argparse.ArgumentParser) -> None:
    """Add Claude-specific arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--with-proxy-config",
        metavar="PATH",
        help="Path to .env file with proxy configuration (for Azure OpenAI integration with auto persistence prompt)",
    )
    parser.add_argument(
        "--builtin-proxy",
        action="store_true",
        help="Use built-in proxy server with OpenAI Responses API support instead of external claude-code-proxy",
    )
    parser.add_argument(
        "--checkout-repo",
        metavar="GITHUB_URI",
        help="Clone a GitHub repository and use it as working directory. Supports: owner/repo, https://github.com/owner/repo, git@github.com:owner/repo",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run amplihack in Docker container for isolated execution",
    )


# Neo4j arguments removed (Week 7 cleanup) - Kuzu is now the only backend


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for amplihack CLI.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="amplihack",
        description="Amplihack CLI - Enhanced tools for Claude Code development",
        epilog="""Examples:
  amplihack                                    # Launch Claude directly
  amplihack -- --model claude-3-opus-20240229 # Forward model argument to Claude
  amplihack -- --verbose                      # Forward verbose flag to Claude
  amplihack launch -- --help                  # Get Claude help
  amplihack install                           # Install amplihack (no forwarding)
  amplihack install -- --verbose             # Install with Claude args forwarded

Auto Mode Examples:
  amplihack launch --auto -- -p "implement user authentication"
  amplihack claude --auto --max-turns 20 -- -p "refactor the API module"
  amplihack copilot --auto -- -p "add logging to all services"
  amplihack codex --auto -- -p "optimize database queries"
  amplihack amplifier --auto -- -p "build a REST API"

Amplifier Examples:
  amplihack amplifier                                        # Launch Amplifier with amplihack bundle
  amplihack amplifier -- -p "explain this code"              # Non-interactive with prompt
  amplihack amplifier -- resume SESSION_ID                   # Resume a session
  amplihack amplifier -- --model gpt-4o                      # Use specific model
  amplihack amplifier -- --model gpt-4o -p "explain this"    # Model + prompt

For comprehensive auto mode documentation, see docs/AUTO_MODE.md""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command (existing)
    subparsers.add_parser("install", help="Install amplihack agents and tools to ~/.claude")

    # Uninstall command (existing)
    subparsers.add_parser("uninstall", help="Remove amplihack agents and tools from ~/.claude")

    # Launch command (new)
    launch_parser = subparsers.add_parser(
        "launch", help="Launch Claude Code with optional proxy configuration"
    )
    add_claude_specific_args(launch_parser)
    add_auto_mode_args(launch_parser)
    add_common_sdk_args(launch_parser)

    # Claude command (alias for launch)
    claude_parser = subparsers.add_parser("claude", help="Launch Claude Code (alias for launch)")
    add_claude_specific_args(claude_parser)
    add_auto_mode_args(claude_parser)
    add_common_sdk_args(claude_parser)

    # RustyClawd command (Rust implementation)
    rustyclawd_parser = subparsers.add_parser(
        "RustyClawd", help="Launch RustyClawd (Rust implementation)"
    )
    add_claude_specific_args(rustyclawd_parser)
    add_auto_mode_args(rustyclawd_parser)
    add_common_sdk_args(rustyclawd_parser)

    # Copilot command
    copilot_parser = subparsers.add_parser("copilot", help="Launch GitHub Copilot CLI")
    add_auto_mode_args(copilot_parser)
    add_common_sdk_args(copilot_parser)

    # Codex command
    codex_parser = subparsers.add_parser("codex", help="Launch OpenAI Codex CLI")
    add_auto_mode_args(codex_parser)
    add_common_sdk_args(codex_parser)

    # Amplifier command
    # Note: All amplifier-specific args (--model, --provider, --resume, etc.) should be
    # passed after "--" separator, just like other CLI tools (claude, codex, copilot)
    amplifier_parser = subparsers.add_parser(
        "amplifier", help="Launch Microsoft Amplifier with amplihack bundle"
    )
    add_auto_mode_args(amplifier_parser)
    add_common_sdk_args(amplifier_parser)

    # UVX helper command
    uvx_parser = subparsers.add_parser("uvx-help", help="Get help with UVX deployment")
    uvx_parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    uvx_parser.add_argument("--info", action="store_true", help="Show UVX staging information")

    # Hidden local install command
    local_install_parser = subparsers.add_parser("_local_install", help=argparse.SUPPRESS)
    local_install_parser.add_argument("repo_root", help="Repository root directory")

    # Plugin management commands
    plugin_parser = subparsers.add_parser("plugin", help="Plugin management commands")
    plugin_subparsers = plugin_parser.add_subparsers(
        dest="plugin_command", help="Plugin subcommands"
    )

    # Install plugin command
    install_parser = plugin_subparsers.add_parser(
        "install", help="Install plugin from git URL or local path"
    )
    install_parser.add_argument("source", help="Git URL or local directory path")
    install_parser.add_argument("--force", action="store_true", help="Overwrite existing plugin")

    # Uninstall plugin command
    uninstall_parser = plugin_subparsers.add_parser("uninstall", help="Remove plugin")
    uninstall_parser.add_argument("plugin_name", help="Name of plugin to remove")

    # Link plugin command
    link_parser = plugin_subparsers.add_parser(
        "link", help="Link installed plugin to Claude Code settings"
    )
    link_parser.add_argument(
        "plugin_name",
        nargs="?",
        default="amplihack",
        help="Plugin name to link (default: amplihack)",
    )

    # Verify plugin command
    verify_parser = plugin_subparsers.add_parser(
        "verify", help="Verify plugin installation and discoverability"
    )
    verify_parser.add_argument(
        "plugin_name",
        nargs="?",
        default="amplihack",
        help="Plugin name to verify (default: amplihack)",
    )

    # Memory tree visualization command
    memory_parser = subparsers.add_parser("memory", help="Memory system commands")
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command", help="Memory subcommands"
    )

    tree_parser = memory_subparsers.add_parser("tree", help="Visualize memory graph as tree")
    tree_parser.add_argument("--session", help="Filter by session ID")
    tree_parser.add_argument(
        "--type",
        choices=["conversation", "decision", "pattern", "context", "learning", "artifact"],
        help="Filter by memory type",
    )
    tree_parser.add_argument("--depth", type=int, help="Maximum tree depth")
    tree_parser.add_argument(
        "--backend", choices=["kuzu", "sqlite"], default="kuzu", help="Memory backend to use"
    )

    # Export subcommand
    export_parser = memory_subparsers.add_parser(
        "export", help="Export agent memory to a portable format"
    )
    export_parser.add_argument(
        "--agent", required=True, help="Name of the agent whose memory to export"
    )
    export_parser.add_argument(
        "--output", "-o", required=True, help="Output file path (.json) or directory (kuzu)"
    )
    export_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "kuzu"],
        default="json",
        help="Export format (default: json)",
    )
    export_parser.add_argument("--storage-path", help="Custom storage path for the agent's Kuzu DB")

    # Import subcommand
    import_parser = memory_subparsers.add_parser(
        "import", help="Import memory from a portable format into an agent"
    )
    import_parser.add_argument(
        "--agent", required=True, help="Name of the target agent to import into"
    )
    import_parser.add_argument(
        "--input", "-i", required=True, help="Input file path (.json) or directory (kuzu)"
    )
    import_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "kuzu"],
        default="json",
        help="Import format (default: json)",
    )
    import_parser.add_argument(
        "--merge", action="store_true", help="Merge into existing memory (default: replace)"
    )
    import_parser.add_argument("--storage-path", help="Custom storage path for the agent's Kuzu DB")

    # Clean subcommand
    clean_parser = memory_subparsers.add_parser(
        "clean",
        help="Clean up test sessions",
        epilog="Examples:\n"
        "  amplihack memory clean --pattern 'test_*'     # Clean test sessions\n"
        "  amplihack memory clean --pattern 'demo_*'     # Clean demo sessions\n"
        "  amplihack memory clean --pattern '*_temp'     # Clean temporary sessions\n"
        "  amplihack memory clean --pattern 'dev_*' --no-dry-run  # Actually delete dev sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    clean_parser.add_argument(
        "--pattern",
        default="test_*",
        help="Session ID pattern to match (supports * wildcards, default: test_*)",
    )
    clean_parser.add_argument(
        "--backend", choices=["kuzu", "sqlite"], default="kuzu", help="Memory backend to use"
    )
    clean_parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually delete sessions (default is dry-run mode)",
    )
    clean_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (use with --no-dry-run)",
    )

    # Goal agent generator command
    new_parser = subparsers.add_parser("new", help="Generate a new goal-seeking agent")
    new_parser.add_argument("--file", "-f", required=True, type=Path, help="Path to prompt.md file")
    new_parser.add_argument(
        "--output", "-o", type=Path, help="Output directory (default: ./goal_agents)"
    )
    new_parser.add_argument("--name", "-n", help="Custom agent name (auto-generated if omitted)")
    new_parser.add_argument(
        "--skills-dir",
        type=Path,
        help="Custom skills directory (default: .claude/agents/amplihack)",
    )
    new_parser.add_argument("--enable-memory", action="store_true", help="Enable memory/learning")
    new_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    new_parser.add_argument(
        "--sdk",
        choices=["copilot", "claude", "microsoft", "mini"],
        default="copilot",
        help="SDK to use for agent execution (default: copilot)",
    )
    new_parser.add_argument(
        "--multi-agent",
        action="store_true",
        help="Enable multi-agent architecture with coordinator, memory agent, and sub-agents",
    )
    new_parser.add_argument(
        "--enable-spawning",
        action="store_true",
        help="Enable dynamic sub-agent spawning (requires --multi-agent)",
    )

    # Recipe commands
    recipe_parser = subparsers.add_parser("recipe", help="Recipe management and execution commands")
    recipe_subparsers = recipe_parser.add_subparsers(
        dest="recipe_command", help="Recipe subcommands"
    )

    # Recipe run command
    run_parser = recipe_subparsers.add_parser("run", help="Execute a recipe from YAML file")
    run_parser.add_argument("recipe_path", help="Path to recipe YAML file")
    run_parser.add_argument(
        "-c",
        "--context",
        action="append",
        nargs="+",
        metavar="KEY=VALUE",
        help="Set context variable (key=value). Values may contain special characters: -c 'task=Fix bug (#123)'",
    )
    run_parser.add_argument("--dry-run", action="store_true", help="Show what would be executed")
    run_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    run_parser.add_argument(
        "-f", "--format", choices=["table", "json", "yaml"], default="table", help="Output format"
    )
    run_parser.add_argument("-w", "--working-dir", help="Working directory for execution")

    # Recipe list command
    list_parser = recipe_subparsers.add_parser("list", help="List available recipes")
    list_parser.add_argument(
        "recipe_dir",
        nargs="?",
        default=None,
        help="Directory to search for recipes (default: search all known recipe directories)",
    )
    list_parser.add_argument(
        "-f", "--format", choices=["table", "json", "yaml"], default="table", help="Output format"
    )
    list_parser.add_argument("-t", "--tags", action="append", help="Filter by tags")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show full details")

    # Recipe validate command
    validate_parser = recipe_subparsers.add_parser("validate", help="Validate a recipe YAML file")
    validate_parser.add_argument("recipe_path", help="Path to recipe YAML file")
    validate_parser.add_argument("-v", "--verbose", action="store_true", help="Show details")
    validate_parser.add_argument(
        "-f", "--format", choices=["table", "json", "yaml"], default="table", help="Output format"
    )

    # Recipe show command
    show_parser = recipe_subparsers.add_parser("show", help="Show detailed recipe information")
    show_parser.add_argument("recipe_path", help="Path to recipe YAML file")
    show_parser.add_argument(
        "-f", "--format", choices=["table", "json", "yaml"], default="table", help="Output format"
    )
    show_parser.add_argument("--no-steps", action="store_true", help="Hide step details")
    show_parser.add_argument("--no-context", action="store_true", help="Hide context variables")
    # Mode detection commands
    mode_parser = subparsers.add_parser("mode", help="Claude installation mode commands")
    mode_subparsers = mode_parser.add_subparsers(dest="mode_command", help="Mode subcommands")

    # Detect mode command
    _ = mode_subparsers.add_parser("detect", help="Detect current Claude installation mode")

    # Migrate to plugin command
    _ = mode_subparsers.add_parser("to-plugin", help="Migrate from local to plugin mode")

    # Migrate to local command
    _ = mode_subparsers.add_parser("to-local", help="Create local .claude/ from plugin")

    return parser


def parse_args_with_passthrough(
    argv: list[str] | None = None,
) -> "tuple[argparse.Namespace, list[str]]":
    """Parse arguments with support for -- separator for Claude argument forwarding.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Tuple of (parsed_args, claude_args) where claude_args are arguments after --
    """
    if argv is None:
        argv = sys.argv[1:]

    # Split arguments on -- separator
    try:
        separator_index = argv.index("--")
        amplihack_args = argv[:separator_index]
        claude_args = argv[separator_index + 1 :]
    except ValueError:
        # No -- separator found
        amplihack_args = argv
        claude_args = []

    parser = create_parser()

    # If no amplihack command specified and we have claude_args, default to launch
    if not amplihack_args and claude_args:
        amplihack_args = ["launch"]
    elif not amplihack_args:
        # No command and no claude args - show help
        pass

    args = parser.parse_args(amplihack_args)
    return args, claude_args


__all__ = [
    "IS_WINDOWS",
    "EMOJI",
    "_CLAUDE_COMMANDS",
    "add_auto_mode_args",
    "add_common_sdk_args",
    "add_claude_specific_args",
    "create_parser",
    "parse_args_with_passthrough",
]
