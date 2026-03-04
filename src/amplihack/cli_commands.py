"""Command dispatch handlers for amplihack CLI utility subcommands.

This module contains the handler functions for utility subcommands:
memory, recipe, mode, plugin, new, and uvx-help.

SDK launch commands (copilot, codex, amplifier) are in cli_sdk_commands.py.

Public API:
    handle_memory_command: Dispatch memory subcommands (tree, export, import, clean)
    handle_recipe_command: Dispatch recipe subcommands (run, list, validate, show)
    handle_mode_command: Dispatch mode subcommands (detect, to-plugin, to-local)
    handle_plugin_command: Dispatch plugin subcommands (install, uninstall, link, verify)
    handle_new_command: Handle goal agent generator command
    handle_uvx_help_command: Handle UVX helper command
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from .cli_parser import EMOJI, create_parser
from .cli_sdk_commands import (  # noqa: F401 - re-export for backward compat
    handle_amplifier_command,
    handle_codex_command,
    handle_copilot_command,
)
from .plugin_cli import (
    plugin_install_command,
    plugin_uninstall_command,
    plugin_verify_command,
)
from .plugin_manager import PluginManager
from .utils import is_uvx_deployment

logger = logging.getLogger(__name__)


def handle_memory_command(args: argparse.Namespace) -> int:
    """Dispatch memory subcommands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    if args.memory_command == "tree":
        from .memory.cli_visualize import visualize_memory_tree
        from .memory.models import MemoryType

        # Select backend
        if args.backend == "kuzu":
            try:
                import asyncio

                from .memory.backends.kuzu_backend import KuzuBackend

                backend = KuzuBackend()
                asyncio.run(backend.initialize())
            except ImportError:
                print(
                    "Error: K\u00f9zu backend not available. Kuzu should be installed automatically with amplihack."
                )
                print("Fallin' back to SQLite backend...")
                from .memory.database import MemoryDatabase

                backend = MemoryDatabase()
                backend.initialize()
        else:
            from .memory.database import MemoryDatabase

            backend = MemoryDatabase()
            backend.initialize()

        # Convert type string to enum if provided
        memory_type = None
        if args.type:
            memory_type = MemoryType(args.type)

        # Visualize
        visualize_memory_tree(
            backend=backend,
            session_id=args.session,
            memory_type=memory_type,
            depth=args.depth,
        )

        # Cleanup
        if hasattr(backend, "close"):
            backend.close()

        return 0

    if args.memory_command == "export":
        from pathlib import Path as _Path

        from .agents.goal_seeking.memory_export import export_memory

        storage = _Path(args.storage_path) if args.storage_path else None
        try:
            result = export_memory(
                agent_name=args.agent,
                storage_path=storage,
                output_path=args.output,
                fmt=getattr(args, "format", "json"),
            )
            print(f"Exported memory for agent '{result['agent_name']}'")
            print(f"  Format: {result['format']}")
            print(f"  Output: {result['output_path']}")
            if "file_size_bytes" in result:
                size_kb = result["file_size_bytes"] / 1024
                print(f"  Size: {size_kb:.1f} KB")
            stats = result.get("statistics", {})
            if stats:
                for key, val in stats.items():
                    print(f"  {key}: {val}")
            return 0
        except Exception as e:
            print(f"Error exporting memory: {e}")
            return 1

    if args.memory_command == "import":
        from pathlib import Path as _Path

        from .agents.goal_seeking.memory_export import import_memory

        storage = _Path(args.storage_path) if args.storage_path else None
        try:
            result = import_memory(
                agent_name=args.agent,
                storage_path=storage,
                input_path=args.input,
                fmt=getattr(args, "format", "json"),
                merge=args.merge,
            )
            print(f"Imported memory into agent '{result['agent_name']}'")
            print(f"  Format: {result['format']}")
            print(f"  Source agent: {result.get('source_agent', 'N/A')}")
            print(f"  Merge mode: {result['merge']}")
            stats = result.get("statistics", {})
            if stats:
                for key, val in stats.items():
                    print(f"  {key}: {val}")
            return 0
        except Exception as e:
            print(f"Error importing memory: {e}")
            return 1

    if args.memory_command == "clean":
        from .memory.cli_cleanup import cleanup_memory_sessions

        # Select backend
        if args.backend == "kuzu":
            try:
                import asyncio

                from .memory.backends.kuzu_backend import KuzuBackend

                backend = KuzuBackend()
                asyncio.run(backend.initialize())
            except ImportError:
                print("Error: K\u00f9zu backend not available. Install with: pip install amplihack")
                return 1
        else:
            from .memory.database import MemoryDatabase

            backend = MemoryDatabase()
            backend.initialize()

        # Run cleanup
        result = cleanup_memory_sessions(
            backend=backend,
            pattern=args.pattern,
            dry_run=not args.no_dry_run,
            confirm=args.confirm,
        )

        # Cleanup backend
        if hasattr(backend, "close"):
            backend.close()

        # Return non-zero if there were errors
        return 1 if result["errors"] > 0 else 0

    create_parser().print_help()
    return 1


def handle_recipe_command(args: argparse.Namespace) -> int:
    """Dispatch recipe subcommands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    from .recipe_cli.recipe_command import (
        handle_list,
        handle_run,
        handle_show,
        handle_validate,
        parse_context_args,
    )

    if args.recipe_command == "run":
        # Parse context arguments (key=value pairs)
        context, errors = parse_context_args(args.context or [])
        if errors:
            for error in errors:
                print(f"Error: {error}", file=sys.stderr)
            return 1

        return handle_run(
            recipe_path=args.recipe_path,
            context=context,
            dry_run=args.dry_run,
            verbose=args.verbose,
            format=args.format,
            working_dir=args.working_dir,
        )

    if args.recipe_command == "list":
        return handle_list(
            recipe_dir=args.recipe_dir,
            format=args.format,
            tags=args.tags,
            verbose=args.verbose,
        )

    if args.recipe_command == "validate":
        return handle_validate(
            recipe_path=args.recipe_path,
            verbose=args.verbose,
            format=args.format,
        )

    if args.recipe_command == "show":
        return handle_show(
            recipe_path=args.recipe_path,
            format=args.format,
            show_steps=not args.no_steps,
            show_context=not args.no_context,
        )

    create_parser().print_help()
    return 1


def handle_mode_command(args: argparse.Namespace) -> int:
    """Dispatch mode subcommands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    from .mode_detector import MigrationHelper, ModeDetector

    detector = ModeDetector()

    if args.mode_command == "detect":
        mode = detector.detect()
        claude_dir = detector.get_claude_dir(mode)

        print(f"Claude installation mode: {mode.value}")
        if claude_dir:
            print(f"Using .claude directory: {claude_dir}")
        else:
            print("No .claude installation found")
            print("Install amplihack with: amplihack install")
        return 0

    if args.mode_command == "to-plugin":
        migrator = MigrationHelper()
        project_dir = Path.cwd()

        if not migrator.can_migrate_to_plugin(project_dir):
            print("Cannot migrate to plugin mode:")
            if not detector.has_local_installation():
                print("  - No local .claude/ directory found")
            if not detector.has_plugin_installation():
                print("  - Plugin not installed (run: amplihack install)")
            return 1

        print(f"This will remove local .claude/ directory: {project_dir / '.claude'}")
        print("Plugin installation will be used instead.")
        response = input("Continue? (y/N): ")

        if response.lower() != "y":
            print("Migration cancelled")
            return 0

        if migrator.migrate_to_plugin(project_dir):
            print(f"{EMOJI['check']} Migrated to plugin mode successfully")
            print("Local .claude/ removed, using plugin installation")
            return 0
        print("Migration failed")
        return 1

    if args.mode_command == "to-local":
        migrator = MigrationHelper()
        project_dir = Path.cwd()
        info = migrator.get_migration_info(project_dir)

        if not info["can_migrate_to_local"]:
            print("Cannot create local .claude/ directory:")
            if info["has_local"]:
                print("  - Local .claude/ already exists")
            if not info["has_plugin"]:
                print("  - Plugin not installed (run: amplihack install)")
            return 1

        print(f"This will create local .claude/ directory in: {project_dir}")
        print(f"Copying from plugin: {info['plugin_path']}")
        response = input("Continue? (y/N): ")

        if response.lower() != "y":
            print("Migration cancelled")
            return 0

        if migrator.migrate_to_local(project_dir):
            print(f"{EMOJI['check']} Local .claude/ created successfully")
            print("Now using project-local installation")
            return 0
        print("Migration failed")
        return 1

    create_parser().print_help()
    return 1


def handle_plugin_command(args: argparse.Namespace) -> int:
    """Dispatch plugin subcommands.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    if args.plugin_command == "install":
        return plugin_install_command(args)
    if args.plugin_command == "uninstall":
        return plugin_uninstall_command(args)
    if args.plugin_command == "verify":
        return plugin_verify_command(args)
    if args.plugin_command == "link":
        plugin_name = args.plugin_name
        plugin_root = Path.home() / ".amplihack" / "plugins"
        plugin_path = plugin_root / plugin_name

        if not plugin_path.exists():
            print(f"Error: Plugin not found at {plugin_path}")
            print("Install the plugin first with: amplihack install")
            return 1

        # Create plugin manager and link plugin
        manager = PluginManager(plugin_root=plugin_root)
        if manager._register_plugin(plugin_name):
            print(f"{EMOJI['check']} Plugin linked successfully: {plugin_name}")
            print("  Settings updated in: ~/.claude/settings.json")
            print("  Plugin should now appear in /plugin command")
            return 0
        print(f"Error: Failed to link plugin: {plugin_name}")
        return 1

    create_parser().print_help()
    return 1


def handle_new_command(args: argparse.Namespace) -> int:
    """Handle goal agent generator command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    from .goal_agent_generator.cli import new_goal_agent

    # Call the function directly (new_goal_agent is a Click command decorated function)
    return new_goal_agent(
        file=args.file,
        output=args.output,
        name=args.name,
        skills_dir=args.skills_dir,
        verbose=args.verbose,
        enable_memory=args.enable_memory,
        sdk=args.sdk,
        multi_agent=args.multi_agent,
        enable_spawning=args.enable_spawning,
    )


def handle_uvx_help_command(args: argparse.Namespace) -> int:
    """Handle UVX helper command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    from .commands.uvx_helper import find_uvx_installation_path, print_uvx_usage_instructions

    if args.find_path:
        path = find_uvx_installation_path()
        if path:
            print(str(path))
            return 0
        print("UVX installation path not found", file=sys.stderr)
        return 1
    if args.info:
        # Show UVX staging information
        print("\nUVX Information:")
        print(f"  Is UVX: {is_uvx_deployment()}")
        print("\nEnvironment Variables:")
        print(f"  AMPLIHACK_ROOT={os.environ.get('AMPLIHACK_ROOT', '(not set)')}")
        return 0
    print_uvx_usage_instructions()
    return 0


__all__ = [
    "handle_amplifier_command",
    "handle_codex_command",
    "handle_copilot_command",
    "handle_memory_command",
    "handle_mode_command",
    "handle_new_command",
    "handle_plugin_command",
    "handle_recipe_command",
    "handle_uvx_help_command",
]
